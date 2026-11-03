"""Is the checklist right second by second (stage 29)? Especially when the cook returns to an earlier step."""
from __future__ import annotations

import numpy as np

from .advice import finished_by
from .tracking import truth_active, truth_entries


def revisit_seconds(truth, ts, n_steps: int) -> list[tuple[int, int]]:
    """(tick, step) inside a return visit: the step was left for a later step and the cook came back to it."""
    entries, out = truth_entries(truth), []
    first = {}
    for t0, k in entries:
        first.setdefault(k, t0)
    for i, tt in enumerate(np.asarray(ts, dtype=float)):
        for k in truth_active(truth, tt):
            later_before = any(first.get(j, 1e9) < tt and j > k for j in range(n_steps))
            if tt > first[k] + 10 and later_before:
                out.append((i, k))
    return out


def checklist_scores(states: list[list[str]], truth, ts, n_steps: int) -> dict:
    """states[i]: the checklist's statuses at tick i."""
    ts = np.asarray(ts, dtype=float)
    on = [(i, k) for i, tt in enumerate(ts) for k in truth_active(truth, tt)]
    rev = revisit_seconds(truth, ts, n_steps)
    return {"step being cooked is open (all annotated seconds)": round(float(np.mean([states[i][k] != "done" for i, k in on])), 2),
            "... during return visits": round(float(np.mean([states[i][k] != "done" for i, k in rev])), 2) if rev else None,
            "return-visit seconds": len(rev),
            "finished steps marked done": round(float(np.mean([states[i][k] == "done" for i, tt in enumerate(ts)
                                                               for k in finished_by(truth, tt)])), 2),
            "'done' steps the cook is not on (±10 s)": round(float(np.mean(
                [k not in truth_active(truth, ts[i], 10) for i, st in enumerate(states) for k, x in enumerate(st) if x == "done"])), 2)}
