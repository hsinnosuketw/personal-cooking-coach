"""One learner's coaching session: events in, decisions out (plan D03, D09, D12, F05, F08).

Pipeline per event: reduce state -> rules -> candidates -> world model
(cache or model) -> policy -> decision, with per-stage timings. Skill
evidence comes from three places only: a spoken prompt (recorded, no level
change), the learner's response, and a closed step's observed outcome --
guided if the coach prompted that skill during the step, else independent.
"""
from __future__ import annotations

import json
import pathlib
import time
import uuid

from . import belief, candidates, policy, recipes, state
from .candidates import MENU
from .schema import Decision, Evidence, EvidenceKind, LearnerResponse, ObservationEvent
from .world_model import WorldModel

RESPONSE_EVIDENCE = {
    "acknowledged": EvidenceKind.prompt_acknowledged,
    "self_reported_done": EvidenceKind.self_reported_done,
    "observed_success": EvidenceKind.observed_guided_success,
    "not_followed": EvidenceKind.not_followed,
}


class Session:
    def __init__(self, learner_id: str, recipe_id: str, provider, memory: bool = True,
                 log_dir: str | None = None):
        self.session_id = uuid.uuid4().hex[:12]
        self.learner_id, self.provider, self.memory = learner_id, provider, memory
        self.beliefs = belief.new_beliefs()
        self.wm = WorldModel(provider)
        self.state = state.initial_state(recipe_id)
        self.decisions: list[Decision] = []
        self.prompted: set[str] = set()  # skills the coach spoke about during the current step
        self.last_candidates, self.last_predictions, self.trace = [], [], []
        self.log_path = (pathlib.Path(log_dir) / f"{self.session_id}.jsonl") if log_dir else None

    # -- inputs -----------------------------------------------------------
    def switch_recipe(self, recipe_id: str, ts: float = 0.0) -> None:
        self.state = state.initial_state(recipe_id, ts)
        self.prompted = set()
        if not self.memory:  # ablation A1: same pipeline, no history across recipes
            self.beliefs = belief.new_beliefs()
        self._log("switch_recipe", {"recipe_id": recipe_id, "ts": ts})

    def observe(self, ev: ObservationEvent) -> Decision:
        if ev.facts.get("step_done"):
            self._close_step(ev)
        before = self.state.step_id
        self.state = state.apply_event(self.state, ev)
        if self.state.step_id != before:
            self.prompted = set()
        self._log("event", ev.model_dump())
        return self._decide(ev)

    def respond(self, r: LearnerResponse) -> None:
        d = next((d for d in self.decisions if d.decision_id == r.decision_id), None)
        skill = MENU[d.candidate_id][1] if d else None
        if skill and r.kind in RESPONSE_EVIDENCE:
            self._evidence(RESPONSE_EVIDENCE[r.kind], skill, r.ts, r.decision_id)
        self._log("response", r.model_dump())

    # -- pipeline ---------------------------------------------------------
    def _decide(self, ev: ObservationEvent) -> Decision:
        t, stages = time.perf_counter(), {}

        def lap(name):
            nonlocal t
            now = time.perf_counter()
            stages[name] = round((now - t) * 1000, 2)
            t = now

        step = recipes.step(self.state.recipe_id, self.state.step_id)
        version = self.state.version
        rule = policy.rule_decision(self.state)
        lap("rules")
        cands = candidates.generate(self.state)
        lap("candidates")
        preds, source = [], "rule"
        if rule:
            chosen = next(c for c in candidates.all_candidates(self.state) if c.candidate_id == rule)
        else:
            preds, source = self.wm.compare(self.state, self.beliefs, cands)
            lap("world_model")
            chosen = policy.choose(cands, preds, self.beliefs)
        if state.is_stale(version, self.state):  # never act on a superseded state
            raise RuntimeError("state changed during decision")
        pred = next((p for p in preds if p.candidate_id == chosen.candidate_id), None)
        last = next((d for d in reversed(self.decisions) if d.speak), None)
        d = policy.make_decision(chosen, pred, step, self.beliefs, source, version, ev.ts, last)
        lap("policy")
        if d.speak and chosen.skill_id:
            self.prompted.add(chosen.skill_id)
            self._evidence(EvidenceKind.prompt_given, chosen.skill_id, ev.ts, d.decision_id)
        self.decisions.append(d)
        self.last_candidates, self.last_predictions = cands, preds
        self.trace.append({"event_id": ev.event_id, "source": source, "stages_ms": stages})
        self._log("decision", d.model_dump())
        return d

    def _close_step(self, ev: ObservationEvent) -> None:
        good = ev.facts.get("outcome", "good") == "good"
        for skill in recipes.step(self.state.recipe_id, self.state.step_id)["skills"]:
            kind = (EvidenceKind.observed_failure if not good
                    else EvidenceKind.observed_guided_success if skill in self.prompted
                    else EvidenceKind.observed_independent_success)
            self._evidence(kind, skill, ev.ts, ev.event_id)

    def _evidence(self, kind, skill, ts, ref) -> None:
        belief.add_evidence(self.beliefs, Evidence(kind=kind, skill_id=skill, recipe_id=self.state.recipe_id,
                                                   step_id=self.state.step_id, ts=ts, ref=ref))

    # -- outputs ----------------------------------------------------------
    def snapshot(self) -> dict:
        return {
            "session_id": self.session_id, "learner_id": self.learner_id, "memory": self.memory,
            "provider": self.provider.name, "state": self.state.model_dump(mode="json"),
            "recipe": recipes.load(self.state.recipe_id),
            "beliefs": {k: b.model_dump(mode="json") for k, b in self.beliefs.items()},
            "candidates": [c.model_dump() for c in candidates.all_candidates(self.state)],
            "considered": [c.candidate_id for c in self.last_candidates],
            "predictions": [p.model_dump() for p in self.last_predictions],
            "decision": self.decisions[-1].model_dump() if self.decisions else None,
            "trace": self.trace[-1] if self.trace else None,
            "counters": {"provider_calls": self.provider.calls, "cache_hits": self.wm.hits},
        }

    def _log(self, kind: str, payload: dict) -> None:
        if self.log_path is None:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": kind, **payload}, ensure_ascii=False, default=str) + "\n")
