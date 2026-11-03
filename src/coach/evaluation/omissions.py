"""The skipped-step test (stage 36): a step's evidence is removed; is it still reminded, and how soon?"""
from __future__ import annotations

from ..coaching.reminders import mmss


def omission_scores(run: dict) -> dict:
    """Was the skipped step (run["omitted"]) ever reminded, and how long after the cook would have done it?"""
    k = run["omitted"]
    due = min(s0 for j, s0, _ in run["truth"] if j == k)
    named = [c for c in run["calls"] if c.get("remind") == k or c.get("coach_step") == k]
    after = [c["ready"] for c in named if c["ready"] >= due]
    other = [c for c in run["calls"] if c.get("remind") is not None and c["remind"] != k]
    return {"skipped step": k + 1, "it would have started at": mmss(due), "coach calls": len(run["calls"]),
            "reminded (STEP or REMIND)": f"{len(named)}x", "first reminder after that": mmss(after[0]) if after else "never",
            "delay (s)": round(after[0] - due) if after else None,
            "REMIND naming other steps": len(other),
            "checklist marked it started": any(x["ledger"][k] != "not started" for x in run["ticks"])}
