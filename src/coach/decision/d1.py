"""The decision model (Liquid AI d1-2B): every second, the next action from the recipe's Actions Bank.

d1 answers typed questions about a JSON state. The state holds what a live system knows at time t: the tracker's
step, the probe's expected actions, the coach's latest advice (and reasoning), and from stage 21 on the checklist.
The model itself is loaded in the notebook (transformers, GPU); everything here is plain data.
"""
from __future__ import annotations

import copy

SKIP_DONE = " Skip steps the checklist marks done, unless the coach explicitly says to go back to that step."
NEW_ROUND = " A finished step of a repeated run can start a new round."


def d1_choices(steps, texts: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """The Actions Bank as d1 choices ("s3_cut_onion" -> "Step 3 (Add chopped red onions…): cut onion"), and the steps."""
    actions = {}
    for s in steps:
        for v, n, _ in s.pairs:
            actions.setdefault(f"s{s.order + 1}_{v}_{n}".replace(" ", "_").replace(":", "_"),
                               f"Step {s.order + 1} ({s.text[:45]}…): {v} {n}")
    return actions, {f"step{k + 1}": t for k, t in enumerate(texts)}


def d1_questions(actions: dict[str, str], step_choices: dict[str, str], skip_done: bool = False,
                 new_rounds: bool = False) -> dict:
    """next_action / next_step / should_speak. skip_done (stage 26c) and new_rounds (stage 31) add to the instructions."""
    qs = {
        "next_action": {"type": "choice", "instructions": "Which action should the cook do next, following the coach?",
                        "criteria": actions},
        "next_step": {"type": "choice", "instructions": "Which recipe step should the cook do next?",
                      "criteria": step_choices},
        "should_speak": {"type": "noul",
                         "instructions": "Does the coach say the cook should change or start something now, rather than keep going?"},
    }
    return extend_questions(qs, skip_done, new_rounds)


def extend_questions(qs: dict, skip_done: bool = False, new_rounds: bool = False) -> dict:
    qs = copy.deepcopy(qs)
    for q in ("next_action", "next_step"):
        qs[q]["instructions"] += (SKIP_DONE if skip_done else "") + (NEW_ROUND if new_rounds else "")
    return qs


def d1_state(t: float, tracker_step: int, expected: list[str], advice: str, thinking: str | None) -> dict:
    """thinking: the coach's reasoning (its last 6000 characters), or None to leave it out."""
    state = {"time_s": round(t), "tracker_step": tracker_step + 1, "predicted_next_actions": expected,
             "coach_advice": advice}
    if thinking is not None:
        state["coach_reasoning"] = thinking[-6000:]
    return state


def with_checklist(state: dict, ledger: dict) -> dict:
    """Stage 21 on: the checklist's step numbers per status."""
    state["checklist"] = {status: [k + 1 for k, s in enumerate(ledger["steps"]) if s["status"] == status]
                          for status in ("done", "in progress", "not started")}
    return state


def best_action(answers: dict, actions: dict[str, str]) -> tuple[str, int]:
    """The most likely next action, as ("cut onion", 0-based step)."""
    best = max(answers["next_action"]["probabilities"].items(), key=lambda kv: kv[1])[0]
    return actions[best].split(": ")[-1], int(best.split("_")[0][1:]) - 1
