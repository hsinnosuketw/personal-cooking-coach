"""Candidate generation (plan E02): 2-3 feasible next moves for this moment.

"Keep watching" is always among them, so every intervention is compared
against doing nothing. Infeasible moves are filtered out with a reason
(e.g. no re-cutting once the onion is in the pan -- that is next time's
lesson, not a rescue).
"""
from __future__ import annotations

from . import recipes
from .schema import Candidate, KitchenState
from .state import known

MENU = {  # id: (kind, skill, label)
    "continue_observe": ("observe", None, "繼續，我在旁邊看著"),
    "lower_heat": ("adjust", "heat_control", "把火轉小一點"),
    "raise_heat": ("adjust", "heat_control", "把火轉大一點"),
    "add_salt_now": ("adjust", "salt_timing", "現在加一小撮鹽"),
    "add_water_splash": ("adjust", "moisture", "加一小匙水，鏟起鍋底"),
    "ask_heat_level": ("ask", "heat_control", "現在火開幾分？"),
    "advance_step": ("advance", "step_judgment", "可以進下一步了"),
    "recut_onion": ("adjust", "knife_cut", "把大塊的再切小，大小一致"),
}


def _feasibility(cid: str, state: KitchenState, step: dict) -> str | None:
    """None when the move is possible now, else why it is not."""
    in_pan = bool(step.get("onion_in_pan"))
    target = step.get("target")
    color = known(state, "onion_color")
    if cid == "recut_onion" and in_pan:
        return "洋蔥已下鍋，切法留到下次備料"
    if cid in ("lower_heat", "raise_heat", "add_water_splash") and not in_pan:
        return "還沒開始炒洋蔥"
    if cid == "add_salt_now":
        if known(state, "salted") is True:
            return "已經加過鹽"
        if not in_pan:
            return "洋蔥還沒下鍋"
        if step.get("salt") == "late" and target and (color is None or color < target["color"] - 0.15):
            return "這道要上色後再加鹽，太早加會延後焦糖化"
    if cid == "ask_heat_level" and known(state, "heat_level") is not None:
        return "火力已知"
    if cid == "advance_step" and recipes.next_step_id(state.recipe_id, state.step_id) is None:
        return "已是最後一步"
    return None


def _priority(state: KitchenState, step: dict) -> list[str]:
    target = step.get("target")
    color = known(state, "onion_color")
    pri = []
    if known(state, "cut_uniformity") == "uneven" and not step.get("onion_in_pan"):
        pri.append("recut_onion")
    if known(state, "heat_level") is None and step.get("onion_in_pan"):
        pri.append("ask_heat_level")
    if known(state, "smoke") is True or (target and color is not None and color >= target["max_color"] - 0.05):
        pri += ["lower_heat", "add_water_splash"]
    if target and color is not None and target["color"] - 0.05 <= color <= target["max_color"]:
        pri.append("advance_step")
    if known(state, "salted") is not True:
        pri.append("add_salt_now")
    if target and color is not None and color < target["color"] - 0.2:
        pri.append("raise_heat")
    pri += list(MENU)
    return list(dict.fromkeys(pri))


def all_candidates(state: KitchenState) -> list[Candidate]:
    step = recipes.step(state.recipe_id, state.step_id)
    out = []
    for cid, (kind, skill, label) in MENU.items():
        why = _feasibility(cid, state, step)
        out.append(Candidate(candidate_id=cid, kind=kind, skill_id=skill, label=label,
                             feasible=why is None, reason_infeasible=why))
    return out


def generate(state: KitchenState, n: int = 3) -> list[Candidate]:
    step = recipes.step(state.recipe_id, state.step_id)
    feasible = {c.candidate_id: c for c in all_candidates(state) if c.feasible}
    picked = [feasible[c] for c in _priority(state, step) if c in feasible][:n]
    if all(c.candidate_id != "continue_observe" for c in picked):
        picked[-1] = feasible["continue_observe"]
    return picked
