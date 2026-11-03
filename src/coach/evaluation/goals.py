"""Score runs by the coach's goals: remember every step the cook has started, remind steps not started yet.

Recipe order is ignored: cooks skip ahead and come back, so "did it follow the recipe" is not the question.
A step counts as done once the cook starts it (HD-EPIC's first annotated span); memory is judged on when the
checklist first stopped calling it "not started". Inputs are saved run dicts (results/coach_*.json): they carry
"truth" [[step, start, end], ...], "steps", "ticks" (per second, with "ledger" and "d1_step") and "calls".
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REMIND_BEFORE_S = 120   # a reminder "leads" a step if it names it in the 2 minutes before the cook first starts it
STARTED_SLACK_S = 10    # memory may lag the cook a little; marking a step started >10 s before it was is a false memory


def first_last(run: dict) -> tuple[dict, dict]:
    """Per step: when the cook first started it (the start of 'done at least once') and when its last part ended."""
    first, last = {}, {}
    for k, s0, s1 in run["truth"]:
        first[k], last[k] = min(first.get(k, 1e9), s0), max(last.get(k, 0), s1)
    return first, last


def step_state(k: int, t: float, first: dict, last: dict) -> str:
    if first.get(k, 1e9) > t:
        return "not started yet"
    return "started, more to come" if last[k] >= t else "finished"


def memory_scores(run: dict) -> dict:
    """Does the checklist remember each step the cook has started, and when?"""
    ticks, n = run["ticks"], len(run["steps"])
    if "ledger" not in ticks[0]:
        return {}
    first, _ = first_last(run)
    marked = {k: next((x["t"] for x in ticks if x["ledger"][k] != "not started"), None) for k in range(n)}
    started = [k for k in first if first[k] <= ticks[-1]["t"]]
    lag = [marked[k] - first[k] for k in started if marked[k] is not None]
    tp = fp = fn = 0
    for x in ticks:
        for k in range(n):
            said, real = x["ledger"][k] != "not started", first.get(k, 1e9) <= x["t"] + STARTED_SLACK_S
            tp, fp, fn = tp + (said and real), fp + (said and not real), fn + (real and not said)
    return {"steps started (annotated)": len(started),
            "remembered by the end": f"{sum(marked[k] is not None for k in started)}/{len(started)}",
            "memory F1 over time": round(2 * tp / max(1, 2 * tp + fp + fn), 2),
            "median lag of the memory (s)": round(float(np.median(lag))) if lag else None,
            "remembered >10 s before it happened": sum(l < -STARTED_SLACK_S for l in lag),
            "steps never done but remembered": sum(marked[k] is not None for k in range(n) if k not in first)}


def reminder_scores(run: dict) -> dict:
    """What the coach's STEP and d1's Next Step point at: a step not started yet, one in progress, or one finished.
    Only up to the end of the annotations (Aloo Paratha's stop at ~1520 s of 1850 s): after that every step looks finished."""
    first, last = first_last(run)
    end = max(s1 for _, _, s1 in run["truth"])
    calls = [c for c in run["calls"] if c.get("coach_step") is not None and c["ready"] <= end]
    out = {}
    if calls:
        kinds = pd.Series([step_state(c["coach_step"], c["ready"], first, last) for c in calls])
        out.update({f"coach → {k}": round(float((kinds == k).mean()), 2)
                    for k in ("not started yet", "started, more to come", "finished")})
        reminds = [c for c in run["calls"] if c.get("remind") is not None and c["ready"] <= end]
        if any("remind" in c for c in run["calls"]):  # stage 35's REMIND line
            out["REMIND lines"] = f"{len(reminds)}/{len(calls)}"
            out["REMIND → not started yet"] = round(float(np.mean([step_state(c["remind"], c["ready"], first, last) == "not started yet"
                                                                    for c in reminds])), 2) if reminds else None
            calls = calls + [dict(c, coach_step=c["remind"]) for c in reminds]   # a reminder counts as naming that step
        later = [k for k in first if first[k] > run["ticks"][0]["t"] + 30]
        out["steps reminded before the cook started them"] = (
            f"{sum(any(c['coach_step'] == k and first[k] - REMIND_BEFORE_S <= c['ready'] <= first[k] for c in calls) for k in later)}"
            f"/{len(later)}")
        never = [k for k in range(len(run["steps"])) if k not in first]
        if never:
            out["never-done steps the coach named"] = ", ".join(
                f"{k + 1}: {sum(c['coach_step'] == k for c in calls)}x" for k in never)
    d1 = pd.Series([step_state(x["d1_step"] - 1, x["t"], first, last) for x in run["ticks"] if x["t"] <= end])
    out.update({f"d1 → {k}": round(float((d1 == k).mean()), 2) for k in ("not started yet", "started, more to come", "finished")})
    minutes = (run["ticks"][-1]["t"] - run["ticks"][0]["t"]) / 60
    out.update({"advice per minute": round(len(run["calls"]) / minutes, 2),
                "same STEP twice in a row": round(float(np.mean([a["coach_step"] == b["coach_step"]
                                                                 for a, b in zip(calls, calls[1:])])), 2) if len(calls) > 1 else None})
    return out


RUN_FILES = {  # label -> timeline file prefix (notebook stages 18, 26, 31, 32, 35)
    "no memory (stage 18)": "coach_timeline",
    "every 3 actions": "coach_events_N3", "every 5 actions": "coach_events_N5", "every 10 actions": "coach_events_N10",
    "every 10 · HD tags": "coach_events_N10_hdtags",
    "adaptive timing · HD tags": "coach_adaptive_timing_hdtags",
    "+ loops · HD tags": "coach_adaptive_timing_loops_hdtags",
    "+ loops + intent · HD tags": "coach_adaptive_timing_loops_intent_hdtags",
    "every 10 · annotated events": "coach_events_N10_oracle_hdtags",
    "+ loops + intent · annotated events": "coach_adaptive_timing_loops_intent_oracle_hdtags",
    "reminders + wrap-up check · HD tags": "coach_adaptive_remind_hdtags",
}


def goal_table(results: Path, video_id: str, runs: dict[str, str] = RUN_FILES) -> pd.DataFrame:
    """One row per saved run of this video that exists: memory and reminder scores side by side."""
    rows = {}
    for label, prefix in runs.items():
        f = Path(results) / f"{prefix}_{video_id}.json"
        if f.exists():
            run = json.loads(f.read_text())
            rows[label] = {**memory_scores(run), **reminder_scores(run)}
    return pd.DataFrame(rows).T


MEMORY_COLS = ["remembered by the end", "memory F1 over time", "median lag of the memory (s)",
               "remembered >10 s before it happened", "steps never done but remembered"]
