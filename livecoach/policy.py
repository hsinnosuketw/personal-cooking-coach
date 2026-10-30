"""Decision policy (plan F01-F07): rules first, then a checkable ranking.

Concerns in the plan's order: feasibility (candidates arrive feasible),
risk, the current step's goal, teaching value, interruption cost. When
keeping watch already stays safely on track, only a right-moment lesson
may interrupt. Otherwise an intervention must clearly beat "keep watching"
on the goal to count as better there; ties go to teaching a weak skill,
then to staying quiet. Every decision records whether it came from a
rule, the cache or the model, and speaks in one action line plus one
reason line.
"""
from __future__ import annotations

import uuid

from . import belief
from .candidates import MENU
from .schema import Candidate, Decision, KitchenState, SkillBelief, WMPrediction
from .state import known, onion_color

RISK_LIMIT = 0.6
GAP_MARGIN = 0.10   # how much closer to the target an intervention must get
COOLDOWN_S = 30.0   # don't repeat the same advice sooner than this
# Right-moment lessons (salt when the recipe wants it, move on at the target)
# earn teaching credit; heat changes must earn their place by outcome alone.
TEACHABLE = {"add_salt_now", "advance_step"}


def rule_decision(state: KitchenState) -> str | None:
    """High-priority, observable conditions that skip the model entirely."""
    color = onion_color(state)
    if known(state, "smoke") is True or (color is not None and color >= 0.9):
        return "lower_heat"
    return None


def choose(cands: list[Candidate], preds: list[WMPrediction],
           beliefs: dict[str, SkillBelief]) -> Candidate:
    by_id = {p.candidate_id: p for p in preds}
    ask = next((c for c in cands if c.kind == "ask"), None)
    if ask and any("敏感" in a for p in preds for a in p.assumptions):
        return ask  # the missing fact would change the advice: ask instead of guessing
    observe = by_id.get("continue_observe")

    def teach(c: Candidate) -> float:
        return belief.teaching_value(beliefs, c.skill_id) if c.candidate_id in TEACHABLE else 0.0

    def quiet(c: Candidate) -> int:
        return 0 if c.kind == "observe" else 1

    def safe_on_track(c: Candidate) -> bool:
        p = by_id[c.candidate_id]
        return p.on_track and p.burn_risk < RISK_LIMIT

    if observe is not None and safe_on_track(next(c for c in cands if c.kind == "observe")):
        # keeping watch already works: only a right-moment lesson that stays on track may interrupt
        return min((c for c in cands if safe_on_track(c)), key=lambda c: (-teach(c), quiet(c)))
    base_gap = observe.target_gap if observe else 1.0

    def key(c: Candidate):
        p = by_id[c.candidate_id]
        gap = p.target_gap
        if c.kind != "observe" and abs(gap - base_gap) < GAP_MARGIN:
            gap = base_gap  # not clearly better or worse than leaving it alone
        return (p.burn_risk >= RISK_LIMIT, round(gap / 0.05), -teach(c), quiet(c))

    return min(cands, key=key)


def _reason(c: Candidate, p: WMPrediction | None, step: dict, source: str) -> str:
    target = step.get("target", {}).get("describe")
    if source == "rule":
        return "已經冒煙或快焦了，先降溫保住洋蔥。"
    if c.kind == "observe":
        return "目前方向正確，需要時我會提醒你。"
    if c.kind == "ask":
        return "火力會決定接下來是變軟還是變焦，知道了才給得準。"
    if c.candidate_id == "add_salt_now":
        return "鹽會把洋蔥的水分逼出來，讓它慢慢變軟、不容易焦。"
    if p is None:
        return ""
    return p.primary_outcome + (f"；目標是{target}。" if target else "。")


def make_decision(c: Candidate, p: WMPrediction | None, step: dict, beliefs: dict[str, SkillBelief],
                  source: str, state_version: int, ts: float, last_spoken: Decision | None) -> Decision:
    speak = c.kind != "observe"
    if speak and last_spoken and last_spoken.candidate_id == c.candidate_id and ts - last_spoken.ts < COOLDOWN_S:
        speak = False  # said it moments ago; don't nag
    reason = _reason(c, p, step, source)
    if c.kind == "adjust" and source != "rule" and belief.teaching_value(beliefs, c.skill_id) == 0.0:
        reason = ""  # they have done this alone before: the action line is enough
    return Decision(decision_id=uuid.uuid4().hex[:12], candidate_id=c.candidate_id, kind=c.kind,
                    source=source, action_line=MENU[c.candidate_id][2], reason_line=reason,
                    speak=speak, state_version=state_version, ts=ts)
