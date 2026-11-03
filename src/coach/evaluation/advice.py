"""Scoring the advice and d1's choices against the annotated step spans (stages 23, 26 and 31).

truth: [step, start s, end s] rows. "Good next" accepts either answer key from stage 17: what this cook did next,
or the next step in recipe order.
"""
from __future__ import annotations

import difflib
import numpy as np
import pandas as pd

from .tracking import truth_active, truth_entries


def finished_by(truth, t: float) -> set[int]:
    """Steps whose last annotated span ended before t."""
    last_end = {}
    for k, s0, s1 in truth:
        last_end[k] = max(last_end.get(k, 0), s1)
    return {k for k, e in last_end.items() if e < t}


def good_next(truth, n_steps: int, t: float) -> set[int]:
    now = {k for k, s0, s1 in truth if s0 <= t + 1 <= s1}
    later = sorted((s0, k) for k, s0, s1 in truth if s0 > t)
    started = {k for k, s0, s1 in truth if s0 <= t}
    left = [k for k in range(n_steps) if k not in started]
    return now | ({later[0][1]} if not now and later else set()) | ({min(left)} if left else set())


def d1_scores(ticks: list[dict], truth, n_steps: int) -> dict:
    return {"d1 next step good (per second)": round(float(np.mean([k["d1_step"] - 1 in good_next(truth, n_steps, k["t"]) for k in ticks])), 2),
            "d1 proposes a finished step": round(float(np.mean([k["d1_step"] - 1 in finished_by(truth, k["t"]) for k in ticks])), 2)}


def d1_memory_scores(ticks: list[dict], truth, n_steps: int) -> dict:
    """Stage 26f: does d1 avoid steps the checklist marks done, and is the checklist's "done" right?"""
    with_done = [k for k in ticks if "done" in k["ledger"]]
    marked = [(k["t"], j) for k in ticks for j, s in enumerate(k["ledger"]) if s == "done"]
    return {"d1 Next Step is a checklist-done step": round(float(np.mean([k["ledger"][k["d1_step"] - 1] == "done" for k in with_done])), 2),
            "d1 top action in a checklist-done step": round(float(np.mean([k["ledger"][k["d1_action_step"] - 1] == "done" for k in with_done])), 2),
            **d1_scores(ticks, truth, n_steps),
            "checklist 'done' correct (per second)": round(float(np.mean([j in finished_by(truth, t) for t, j in marked])), 2) if marked else None}


def repeated(calls: list[dict]) -> float:
    """Share of answers whose advice text is >80% the same as the one before."""
    pairs = list(zip(calls, calls[1:]))
    return round(float(np.mean([difflib.SequenceMatcher(None, a["next"], b["next"]).ratio() > 0.8 for a, b in pairs])), 2) if pairs else 0.0


def repeated_step(calls: list[dict]) -> float | None:
    pairs = [(a, b) for a, b in zip(calls, calls[1:]) if a.get("coach_step") is not None]
    return round(float(np.mean([a["coach_step"] == b["coach_step"] for a, b in pairs])), 2) if pairs else None


def timing_scores(run: dict, truth, n_steps: int, window: float = 30.0) -> dict:
    """Stage 31: how often the coach spoke, whether step entries got advice within `window` s, and whether it fit."""
    calls, ticks = run["calls"], run["ticks"]
    minutes = (ticks[-1]["t"] - ticks[0]["t"]) / 60
    entries = [(t0, k) for t0, k in truth_entries(truth) if t0 <= ticks[-1]["t"] - window]
    fresh = lambda t0: [c for c in calls if t0 <= c["ready"] <= t0 + window]
    good = lambda t: good_next(truth, n_steps, t)
    on_target = lambda c, k: c.get("coach_step") is not None and (c["coach_step"] == k or c["coach_step"] in good(c["ready"]))
    row = {"advice messages": len(calls), "per minute": round(len(calls) / minutes, 2),
           "same STEP as the previous advice": repeated_step(calls), "repeated advice (text)": repeated(calls),
           "step entries with advice within 30 s": round(float(np.mean([bool(fresh(t0)) for t0, k in entries])), 2),
           "... and the advice fits the step": round(float(np.mean([any(on_target(c, k) for c in fresh(t0)) for t0, k in entries])), 2),
           "coach STEP fits (active or next)": round(float(np.mean([c["coach_step"] in good(c["t"]) for c in calls
                                                                    if c.get("coach_step") is not None])), 2),
           **d1_scores(ticks, truth, n_steps), "median coach s": round(float(np.median([c["sec"] for c in calls])), 1) if calls else None}
    said = [c for c in calls if c.get("intent") and c["intent"]["doing"] is not None]
    if said:
        row["coach DOING is the annotated step (±5 s)"] = round(float(np.mean([c["intent"]["doing"] in truth_active(truth, c["t"], 5) for c in said])), 2)
        row["HSMM step at the same calls"] = round(float(np.mean([c["hsmm"] in truth_active(truth, c["t"], 5) for c in said])), 2)
    if run.get("suppressed"):
        row["calls skipped (nothing new)"] = sum(run["suppressed"].values())
    row["triggers"] = ", ".join(f"{k} {v}" for k, v in pd.Series([c.get("trigger", "?") for c in calls]).value_counts().items())
    return row


def actual_next(truth, t: float) -> set[int]:
    """What this cook did: the step being worked on at t (+1 s), or else the next step to start."""
    now = {k for k, s0, s1 in truth if s0 <= t + 1 <= s1}
    if now:
        return now
    later = sorted((s0, k) for k, s0, s1 in truth if s0 > t)
    return {later[0][1]} if later else set()


def recipe_next(truth, n_steps: int, t: float) -> set[int]:
    """What the recipe says: a step in progress, or the lowest-numbered step not started yet."""
    now = {k for k, s0, s1 in truth if s0 <= t + 1 <= s1}
    started = {k for k, s0, s1 in truth if s0 <= t}
    left = [k for k in range(n_steps) if k not in started]
    return now | ({min(left)} if left else set())


def setting_scores(rows: list[dict], truth, n_steps: int) -> dict:
    """Stage 17: one coach setting's answers at fixed moments (rows: t, step, sec, tokens, text, truncated)."""
    ok = [r for r in rows if r["step"] is not None]
    secs = [r["sec"] for r in rows if r["sec"] is not None]
    hit = lambda f: round(float(np.mean([r["step"] in f(r["t"]) for r in rows])), 2)
    return {"answered": f"{len(ok)}/{len(rows)}", "cut off by max_tokens": sum(r["truncated"] for r in rows),
            "acc: what the cook did": hit(lambda t: actual_next(truth, t)), "acc: recipe order": hit(lambda t: recipe_next(truth, n_steps, t)),
            "acc: either": hit(lambda t: actual_next(truth, t) | recipe_next(truth, n_steps, t)),
            "median s (10 at once)": round(float(np.median(secs)), 1) if secs else None,
            "median output tokens": int(np.median([r["tokens"] for r in rows if r["tokens"]])) if secs else None,
            "median words": int(np.median([len(r["text"].split()) for r in ok])) if ok else None}


def run_summary(run: dict, truth, n_steps: int) -> dict:
    """Stage 26d: how often the coach spoke, repeats, d1's choices and, with checklist lines, DONE precision/recall."""
    calls, ticks = run["calls"], run["ticks"]
    minutes = (ticks[-1]["t"] - ticks[0]["t"]) / 60
    row = {"advice messages": len(calls), "per minute": round(len(calls) / minutes, 1), "repeated advice": repeated(calls),
           **d1_scores(ticks, truth, n_steps), "median coach s": round(float(np.median([c["sec"] for c in calls])), 1) if calls else None}
    parsed = [c for c in calls if c.get("parsed")]
    if parsed:
        fin = lambda t: finished_by(truth, t)
        tp = sum(len(set(c["parsed"]["DONE"]) & fin(c["t"])) for c in parsed)
        said, real = sum(len(c["parsed"]["DONE"]) for c in parsed), sum(len(fin(c["t"])) for c in parsed)
        row.update({"DONE precision": round(tp / said, 2) if said else None, "DONE recall": round(tp / real, 2) if real else None,
                    "STEP is a finished step": round(float(np.mean([c["coach_step"] in fin(c["t"]) for c in parsed
                                                                     if c["coach_step"] is not None])), 2)})
    if any(c.get("trigger") for c in calls):
        row["triggers"] = ", ".join(f"{k} {v}" for k, v in pd.Series([c["trigger"] for c in calls]).value_counts().items())
    return row
