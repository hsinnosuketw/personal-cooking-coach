"""Model providers (plan D02): one interface, an offline mock and the Meta Model API.

MockProvider is deterministic. It rebuilds the onion from known facts,
simulates every candidate with onion.py, and flags when the outcome hinges
on a fact that is still unknown (so the policy can ask instead of guess).

MetaProvider sends the same comparison to the Meta Model API with
JSON-schema structured output. Status: written against the dev.meta.ai
docs read on 2026-10-30 (POST https://api.meta.ai/v1/chat/completions,
response_format {"type": "json_schema", "json_schema": {name, schema,
strict}}, usage.prompt_tokens / completion_tokens) but never run against
the live API -- there is no key yet. Treat it as untested.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from . import onion, recipes
from .candidates import MENU
from .schema import Candidate, KitchenState, SkillBelief, WMPrediction
from .state import known, onion_color

HORIZON_S = 120
API_URL = "https://api.meta.ai/v1/chat/completions"
CUT_CV = {"even": 0.08, "uneven": 0.35}
SKILL_EFFECT = {
    "continue_observe": "留給學習者自己判斷，是獨立成功的機會",
    "lower_heat": "練習火力控制：快上色時先降火",
    "raise_heat": "練習火力控制：上色太慢時加火",
    "add_salt_now": "練習加鹽時機",
    "add_water_splash": "練習用水救鍋、刮起鍋底",
    "ask_heat_level": "建立對火力的自我覺察",
    "advance_step": "練習判斷何時進下一步",
    "recut_onion": "練習切出一致的大小",
}


def target_gap(o: onion.Onion, step: dict) -> float:
    t = step.get("target")
    if not t:
        return 0.0
    return min(1.0, abs(o.color - t["color"]) + (0.5 if o.color > t["max_color"] else 0.0))


def onion_from_state(state: KitchenState, heat: float | None = None) -> tuple[onion.Onion, list[str]]:
    """The onion as far as the facts say, plus the assumptions filling the gaps."""
    notes = []
    color = onion_color(state)
    if color is None:
        color = 0.3
        notes.append("色度未知，假設 0.30")
    moisture = known(state, "moisture")
    if moisture is None:
        moisture = max(0.2, 1.0 - float(color))
        notes.append(f"水分未知，依顏色估 {moisture:.2f}")
    if heat is None:
        heat = known(state, "heat_level")
        if heat is None:
            heat = 5.0
            notes.append("火力未知，假設 5")
    return onion.Onion(color=float(color), moisture=float(moisture), heat=float(heat),
                       salted=known(state, "salted") is True,
                       cut_cv=CUT_CV.get(known(state, "cut_uniformity"), 0.10)), notes


class MockProvider:
    name = "mock"

    def __init__(self):
        self.calls = 0

    def compare(self, state: KitchenState, beliefs: dict[str, SkillBelief],
                cands: list[Candidate], horizon_s: int = HORIZON_S) -> list[WMPrediction]:
        self.calls += 1
        step = recipes.step(state.recipe_id, state.step_id)
        if not step.get("onion_in_pan"):
            return [self._prep_prediction(state, c, horizon_s) for c in cands]
        base, notes = onion_from_state(state)
        sensitive = False
        if known(state, "heat_level") is None:  # would a different heat change the advice?
            lo = onion.simulate(onion_from_state(state, heat=3)[0], horizon_s)
            hi = onion.simulate(onion_from_state(state, heat=8)[0], horizon_s)
            sensitive = (abs(onion.burn_risk(hi) - onion.burn_risk(lo)) >= 0.3
                         or abs(target_gap(hi, step) - target_gap(lo, step)) >= 0.15)
        out = []
        for c in cands:
            after = base if c.candidate_id == "advance_step" else onion.simulate(
                onion.apply_action(base, c.candidate_id), horizon_s)
            conf = "low" if sensitive else ("medium" if notes else "high")
            out.append(WMPrediction(
                candidate_id=c.candidate_id, horizon_s=horizon_s,
                primary_outcome=f"{horizon_s} 秒後{onion.describe(after)}",
                alternative_outcome="火力若比假設大，會更快上色甚至焦掉" if sensitive else "大致如預測",
                burn_risk=round(onion.burn_risk(after), 3), target_gap=round(target_gap(after, step), 3),
                confidence="high" if (c.kind == "ask" and sensitive) else conf,
                predicted_skill_effect=SKILL_EFFECT.get(c.candidate_id, ""),
                assumptions=notes + (["結果對火力很敏感"] if sensitive else [])))
        return out

    def _prep_prediction(self, state, c, horizon_s) -> WMPrediction:
        uneven = known(state, "cut_uniformity") == "uneven"
        gap = 0.0 if c.candidate_id == "recut_onion" or not uneven else 0.2
        return WMPrediction(
            candidate_id=c.candidate_id, horizon_s=horizon_s,
            primary_outcome="大小一致，下鍋後熟度平均" if gap == 0 else "大小不一，下鍋後小塊會先焦",
            alternative_outcome="", burn_risk=0.0, target_gap=gap, confidence="high",
            predicted_skill_effect=SKILL_EFFECT.get(c.candidate_id, ""))

    def direct_decide(self, state: KitchenState) -> str:
        """B0 stand-in: one shot, no candidates, no world model, no memory.

        Mirrors the plan's failure modes on purpose (always add salt, never
        ask); real B0 numbers need MetaProvider.
        """
        self.calls += 1
        color = onion_color(state)
        if known(state, "smoke") is True or (color is not None and color >= 0.85):
            return "lower_heat"
        if known(state, "salted") is not True and recipes.step(state.recipe_id, state.step_id).get("onion_in_pan"):
            return "add_salt_now"
        return "continue_observe"


class MetaProvider:
    """Meta Model API adapter (untested against the live API; see module docstring)."""

    def __init__(self, model: str = "muse-spark-1.3", timeout: float = 20.0, retries: int = 1):
        self.model, self.timeout, self.retries = model, timeout, retries
        self.name = f"meta:{model}"
        self.calls = self.prompt_tokens = self.completion_tokens = 0

    def _chat(self, system: str, user: str, schema_name: str, schema: dict) -> dict:
        key = os.environ.get("MODEL_API_KEY")
        if not key:
            raise RuntimeError("MODEL_API_KEY is not set")
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema",
                                 "json_schema": {"name": schema_name, "schema": schema, "strict": True}},
        }).encode()
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(API_URL, data=body, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read())
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and attempt < self.retries:
                    time.sleep(1.0 + attempt)
                    continue
                raise
        self.calls += 1
        usage = data.get("usage", {})
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        return json.loads(data["choices"][0]["message"]["content"])

    @staticmethod
    def _facts(state: KitchenState) -> str:
        return json.dumps({k: {"value": f.value, "status": f.status.value, "source": f.source}
                           for k, f in state.facts.items()}, ensure_ascii=False)

    def compare(self, state, beliefs, cands, horizon_s: int = HORIZON_S) -> list[WMPrediction]:
        step = recipes.step(state.recipe_id, state.step_id)
        ids = [c.candidate_id for c in cands]
        item = {"type": "object", "additionalProperties": False,
                "required": ["candidate_id", "primary_outcome", "alternative_outcome", "burn_risk",
                             "target_gap", "confidence", "predicted_skill_effect", "assumptions"],
                "properties": {"candidate_id": {"type": "string", "enum": ids},
                               "primary_outcome": {"type": "string"},
                               "alternative_outcome": {"type": "string"},
                               "burn_risk": {"type": "number"}, "target_gap": {"type": "number"},
                               "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                               "predicted_skill_effect": {"type": "string"},
                               "assumptions": {"type": "array", "items": {"type": "string"}}}}
        schema = {"type": "object", "additionalProperties": False, "required": ["predictions"],
                  "properties": {"predictions": {"type": "array", "items": item}}}
        system = ("You are the world model of a real-time cooking coach. For EACH candidate next move, "
                  f"predict the pan {horizon_s} seconds later if the cook does it. Facts marked unknown or "
                  "conflict are not known: state the assumption you make. burn_risk and target_gap are 0-1. "
                  "Answer in Traditional Chinese.")
        user = json.dumps({"recipe": state.recipe_id, "step": step, "facts": json.loads(self._facts(state)),
                           "skill_levels": {k: beliefs[k].level.value for k in step["skills"]},
                           "candidates": [c.model_dump() for c in cands]}, ensure_ascii=False)
        got = self._chat(system, user, "candidate_predictions", schema)["predictions"]
        preds = [WMPrediction(horizon_s=horizon_s, **p) for p in got]
        if sorted(p.candidate_id for p in preds) != sorted(ids):
            raise ValueError("model did not predict every candidate exactly once")
        return preds

    def direct_decide(self, state: KitchenState) -> str:
        """B0: the same model, one prompt, choosing the next move directly."""
        step = recipes.step(state.recipe_id, state.step_id)
        schema = {"type": "object", "additionalProperties": False, "required": ["candidate_id"],
                  "properties": {"candidate_id": {"type": "string", "enum": list(MENU)}}}
        user = json.dumps({"recipe": state.recipe_id, "step": step,
                           "facts": json.loads(self._facts(state)),
                           "moves": {k: v[2] for k, v in MENU.items()}}, ensure_ascii=False)
        return self._chat("You coach a home cook in real time. Pick the single best next move.",
                          user, "next_move", schema)["candidate_id"]
