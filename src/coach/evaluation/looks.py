"""How right the frame checks were, against the annotated step spans."""
from __future__ import annotations

import numpy as np

from .goals import STARTED_SLACK_S, first_last
from .tracking import truth_active


def look_accuracy(looks: list[dict], truth) -> dict:
    first, _ = first_last({"truth": truth})
    judged = [c for c in looks if c["step"] is not None and c["status"] != "can't tell"]
    right = [(c["status"] != "not started") == (first.get(c["step"], 1e9) <= c["t"] + STARTED_SLACK_S) for c in judged]
    found = [c for c in looks if c["kind"] == "silent" and c["found"] is not None]
    secs = [c["sec"] for c in looks if not c.get("failed")]
    return {"checks": len(looks), **{f"{k} checks": sum(c["kind"] == k for c in looks) for k in ("start", "early_end", "restart", "silent")},
            "can't tell": sum(c["status"] == "can't tell" for c in looks if c["step"] is not None),
            "started / not started judged right": round(float(np.mean(right)), 2) if right else None,
            "silent checks that found a step": f"{len(found)}/{sum(c['kind'] == 'silent' for c in looks)}",
            "... and it was the annotated step (±10 s)": round(float(np.mean([c["found"] in truth_active(truth, c["t"], 10) for c in found])), 2) if found else None,
            "failed calls": sum(bool(c.get("failed")) for c in looks),
            "seconds per check p50 / p90": f"{np.percentile(secs, 50):.1f} / {np.percentile(secs, 90):.1f}" if secs else None,
            "first token p50": round(float(np.median([c["first_s"] for c in looks if not c.get("failed")])), 2) if secs else None}
