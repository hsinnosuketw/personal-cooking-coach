"""Reminders that allow parallel work: a step the cook hasn't started is only worth a reminder once a step that
needs it is under way. Until then the cook may simply be doing things in another order.

The checklist can't tell "not done" from "not seen" (the camera misses actions), so steps without evidence are
shown to the coach as "not seen yet", with the times each step was first and last seen, which steps need it,
and how often it was already reminded.
"""
from __future__ import annotations

from .taskgraph import all_prerequisites, needed_by

REMIND_PARALLEL_ANSWER = """The cook may do steps in any order or in parallel; that is fine. A step only has to be finished before the steps that need it.
"Not seen yet" means the camera has no sign of it: the cook may not have started it, or the camera missed it.
Answer in {lang}, briefly, with two headings:
Where: what has been done (with times), what is in progress, and which steps have not been seen yet.
Next: the most useful thing to do now (2-3 sentences). Support what the cook is doing unless a step it needs has not been seen yet.
Never ask the cook to redo a step that is done, and don't keep repeating a reminder the cook has chosen to postpone.
Then end with exactly these five lines:
DONE: <step numbers, or none>
IN PROGRESS: <step numbers, or none>
LEFT: <step numbers, or none>
STEP: <the step the cook should work on now>
REMIND: <one step from "needed now", or none>"""


def mmss(t: float) -> str:
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def step_signs(seen: dict, steps_of: dict) -> dict[int, tuple[float, float, str]]:
    """Step -> (first seen, last seen, the action seen first), from the checklist's per-action "seen" record."""
    out = {}
    for action, (first, last, _) in seen.items():
        for k in steps_of.get(action, []):
            f0, l0, a0 = out.get(k, (first, last, action))
            out[k] = (min(f0, first), max(l0, last), a0 if f0 <= first else action)
    return out


def needed_now(statuses: list[str], needs: dict[int, list[int]]) -> list[int]:
    """Steps not seen yet that a started step (in progress or done) depends on, directly or indirectly."""
    started = [k for k, s in enumerate(statuses) if s != "not started"]
    want = set().union(*[all_prerequisites(needs, k) for k in started]) if started else set()
    return sorted(j for j in want if statuses[j] == "not started")


def memory_lines_parallel(texts: list[str], statuses: list[str], signs: dict, needs: dict[int, list[int]],
                          reminded: dict[int, list[float]], t: float) -> str:
    users = needed_by(needs)
    rows = []
    for k, text in enumerate(texts):
        state = "not seen yet" if statuses[k] == "not started" else statuses[k]
        when = f"; first sign {mmss(signs[k][0])} ({signs[k][2]}), last {mmss(signs[k][1])}" if k in signs else ""
        deps = f"; needed before step {', '.join(str(j + 1) for j in users.get(k, []))}" if users.get(k) else "; nothing waits on it"
        told = f"; reminded {len(reminded[k])}x (last {mmss(reminded[k][-1])})" if reminded.get(k) else ""
        rows.append(f"{k + 1}. [{state}{when}{deps}{told}] {text[:70]}")
    due = needed_now(statuses, needs)
    return ("\n".join(rows) + f"\nNow {mmss(t)}. Needed now (a started step depends on them, but they have not been seen): "
            + (", ".join(f"step {j + 1}" for j in due) or "none"))
