"""Step tracking against the annotated step spans (`truth`: [step, start s, end s] rows)."""
from __future__ import annotations

import numpy as np

from ..perception.hsmm import stable_changes


def truth_active(truth, t: float, slack: float = 0.0) -> set[int]:
    return {k for k, s0, s1 in truth if s0 - slack <= t <= s1 + slack}


def truth_entries(truth, gap: float = 10.0) -> list[tuple[float, int]]:
    """(time, step) whenever the cook (re)enters a step: no span of it ended in the previous `gap` seconds."""
    out, last_end = [], {}
    for k, s0, s1 in sorted(truth, key=lambda r: r[1]):
        if s0 - last_end.get(k, -1e9) > gap:
            out.append((s0, k))
        last_end[k] = max(last_end.get(k, -1e9), s1)
    return out


def tracker_scores(seq, ts, truth, hold: int) -> dict:
    """How well a per-tick step sequence follows the annotations; changes count once they hold `hold` ticks."""
    ts = np.asarray(ts, dtype=float)
    on = [i for i, t in enumerate(ts) if truth_active(truth, t)]
    changes = stable_changes(seq, hold)
    entries = truth_entries(truth)
    caught = [any(k == kk and -5 <= ts[i] - t0 <= 20 for i, kk in changes) for t0, k in entries]
    return {"current step right (annotated seconds)": round(float(np.mean([int(seq[i]) in truth_active(truth, ts[i]) for i in on])), 2),
            "step changes per minute": round(len(changes) / ((ts[-1] - ts[0]) / 60), 1),
            "step entries caught within 20 s": f"{sum(caught)}/{len(entries)}",
            "entry recall": round(float(np.mean(caught)), 2),
            "change precision (a real entry within 20 s)": round(float(np.mean(
                [any(k == kk and -5 <= ts[i] - t0 <= 20 for t0, kk in entries) for i, k in changes])), 2) if changes else None}
