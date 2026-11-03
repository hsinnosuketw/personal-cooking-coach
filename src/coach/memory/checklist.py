"""The checklist memory: for each recipe step, not started / in progress / done, with when and why it changed.

Three kinds of evidence move a step forward:
- the camera rule: a recipe action the probe is confident about for a few seconds in a row marks its step started;
- the order rule: once a later step has enough action segments, earlier steps in progress count as done;
- the coach's answers (DONE / IN PROGRESS lines), which can only move a step forward.

The loop-aware versions add rounds for steps the recipe repeats (stage 29). Every function here is causal: it
reads evidence up to time t only. The rows the coach sees are written in coaching, not here.
"""
from __future__ import annotations

import numpy as np

RANK = {"not started": 0, "in progress": 1, "done": 2}


def recipe_actions(steps, action_names: list[str]) -> tuple[list[str], np.ndarray, dict[str, list[int]]]:
    """The probe actions that are evidence for some step: (names, their rows in the probe's action head, steps of each).

    `steps` are StepSpecs (order, pairs of verb, noun, …); an action tagged on several steps counts for each.
    """
    row = {name: j for j, name in enumerate(action_names)}
    bank = []  # (key, step index, "verb noun"), one per tag
    for s in steps:
        for v, n, _ in s.pairs:
            key = f"s{s.order + 1}_{v}_{n}".replace(" ", "_").replace(":", "_")
            if f"{v} {n}" in row and key not in {b[0] for b in bank}:
                bank.append((key, s.order, f"{v} {n}"))
    names = sorted({b[2] for b in bank})
    return names, np.array([row[a] for a in names]), {a: sorted({b[1] for b in bank if b[2] == a}) for a in names}


def new_ledger(n_steps: int) -> dict:
    """steps: status, when it last changed and by what; seen: action -> [first s, last s, seconds]; streak: run lengths."""
    return {"steps": [{"status": "not started", "t": None, "by": None} for _ in range(n_steps)], "seen": {}, "streak": {}}


def rule_update(ledger: dict, t: float, probs, names: list[str], steps_of: dict, seen_p: float, seen_k: int) -> list[str]:
    """One second of evidence (`probs`: the probe's probability for each of `names` at time t).

    An action counts as seen once it has p >= seen_p for seen_k seconds in a row; it then marks the first of its
    steps that is not done as in progress. Returns the actions seen for the first time this second.
    """
    first = []
    for a, pa in zip(names, probs):
        run = ledger["streak"].get(a, 0) + 1 if pa >= seen_p else 0
        ledger["streak"][a] = run
        if run < seen_k:
            continue
        if a not in ledger["seen"]:
            first.append(a)
        rec = ledger["seen"].setdefault(a, [t, t, 0])
        rec[1], rec[2] = t, rec[2] + 1
        open_steps = [k for k in steps_of[a] if ledger["steps"][k]["status"] != "done"]
        if open_steps and ledger["steps"][open_steps[0]]["status"] == "not started":
            ledger["steps"][open_steps[0]].update(status="in progress", t=t, by="rule")
    return first


def apply_coach(ledger: dict, parsed: dict, t: float, monotonic: bool = False) -> None:
    """Take the coach's DONE / IN PROGRESS lines. monotonic=True (stage 25 on): a step only moves forward, so the
    coach can't erase camera evidence."""
    for k in range(len(ledger["steps"])):
        status = "done" if k in parsed["DONE"] else "in progress" if k in parsed["IN PROGRESS"] else "not started"
        if monotonic and RANK[status] <= RANK[ledger["steps"][k]["status"]]:
            continue
        if ledger["steps"][k]["status"] != status:
            ledger["steps"][k].update(status=status, t=t, by="coach")


def infer_order(ledger: dict, step_segments: dict, t: float, min_segments: int, coach_step: int | None = None) -> None:
    """Earlier steps in progress count as done once a later step has min_segments segments,
    except the step the coach is advising right now (coach_step)."""
    for k, n in step_segments.items():
        if n >= min_segments:
            for j in range(k):
                if j != coach_step and ledger["steps"][j]["status"] == "in progress":
                    ledger["steps"][j].update(status="done", t=t, by="order")


# --- steps the recipe repeats (stage 29) ---------------------------------------------------------------------------

def new_loop_ledger(n_steps: int) -> dict:
    ledger = new_ledger(n_steps)
    for s in ledger["steps"]:
        s["rounds"] = 0          # how many times this step has been finished
    ledger["fresh"] = {}         # step -> its segments since it was last finished
    return ledger


def set_status(ledger: dict, k: int, status: str, t: float, by: str) -> None:
    st = ledger["steps"][k]
    if status == "done" and st["status"] != "done":
        st["rounds"] = st.get("rounds", 0) + 1
        ledger.setdefault("fresh", {})[k] = 0
    st.update(status=status, t=t, by=by)


def reopen_loops(ledger: dict, seg: dict, t: float, loop_of: dict, reopen_segments: int) -> list[int]:
    """New evidence for a finished step inside a repeated run starts its next round."""
    opened = []
    for k in seg["steps"]:
        if k not in loop_of or ledger["steps"][k]["status"] != "done":
            continue
        ledger["fresh"][k] = ledger["fresh"].get(k, 0) + 1
        if ledger["fresh"][k] >= reopen_segments:
            ledger["steps"][k].update(status="in progress", t=t, by="new round")
            opened.append(k)
    return opened


def apply_coach_loops(ledger: dict, parsed: dict, t: float, loop_of: dict) -> None:
    """Monotonic, except that the coach may reopen a finished step of a repeated run (a new round)."""
    for k in range(len(ledger["steps"])):
        status = "done" if k in parsed["DONE"] else "in progress" if k in parsed["IN PROGRESS"] else "not started"
        cur = ledger["steps"][k]["status"]
        if RANK[status] > RANK[cur]:
            set_status(ledger, k, status, t, "coach")
        elif cur == "done" and status == "in progress" and k in loop_of:
            ledger["steps"][k].update(status="in progress", t=t, by="coach: new round")


def infer_order_loops(ledger: dict, seg_starts: dict, t: float, min_segments: int, coach_step: int | None = None) -> None:
    """The order rule, counting only a later step's segments that began after this step (re)opened:
    otherwise a reopened round would be closed again at once by the evidence of the previous round."""
    n = len(ledger["steps"])
    for j, st in enumerate(ledger["steps"]):
        if j == coach_step or st["status"] != "in progress":
            continue
        if any(sum(t0 >= st["t"] for t0 in seg_starts.get(k, [])) >= min_segments for k in range(j + 1, n)):
            set_status(ledger, j, "done", t, "order")


def loop_status(s: dict) -> str:
    r = s.get("rounds", 0)
    if s["status"] == "done":
        return "done" + (f" x{r}" if r > 1 else "")
    if s["status"] == "in progress" and r:
        return f"in progress, round {r + 1}"
    return s["status"]
