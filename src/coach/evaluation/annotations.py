"""Upper bounds built from HD-EPIC's narrations: annotated events (stage 32) and a perfect probe (stage 37).

These read the annotations, so they are for evaluation only: the live system never sees them.
"""
from __future__ import annotations

import numpy as np


def annotation_segments(narr, ts, verb_key: dict, noun_key: dict, steps_of: dict, merge_gap_s: float) -> list[dict]:
    """HD-EPIC's narrated actions as stage-24 segments, in the probe's words. Each one is known once it ends
    (`done_at` = the first tick at or after its end), and consecutive actions on one object merge as in stage 24.
    narr: this video's narrations (start_timestamp, end_timestamp, main_action_classes)."""
    ts = np.asarray(ts, dtype=float)
    merged = []
    for r in narr.sort_values("start_timestamp").itertuples():
        names = [f"{verb_key.get(v)} {noun_key.get(n)}" for v, n in r.main_action_classes]
        if not names or "None" in names[0]:
            continue
        a, (t0, t1) = names[0], (float(r.start_timestamp), float(r.end_timestamp))
        i = int(np.searchsorted(ts, t1))
        if i >= len(ts):
            continue
        verb, noun = a.split(" ", 1)
        prev = merged[-1] if merged else None
        if prev and prev["noun"] == noun and t0 - prev["t1"] <= merge_gap_s:
            prev["verbs"] += [verb] if verb not in prev["verbs"] else []
            prev.update(t1=max(prev["t1"], t1), done_at=max(prev["done_at"], i), action="/".join(prev["verbs"]) + " " + noun,
                        steps=sorted(set(prev["steps"]) | set(steps_of.get(a, []))))
        else:
            merged.append({"t0": t0, "t1": t1, "action": a, "steps": steps_of.get(a, []), "done_at": i, "noun": noun, "verbs": [verb]})
    return merged


def annotation_pred(pred: dict, narr, verb_key: dict, noun_key: dict, verb_row: dict, noun_row: dict, action_row: dict,
                    p: float = 0.9, floor: float = 0.001) -> dict:
    """A perfect probe: every second, the verbs, nouns and actions the annotators marked at that moment (in
    EPIC-KITCHENS classes) get p, split between overlapping ones; everything else gets floor. `pred` gives the
    ticks and the array shapes."""
    ts = pred["t"].astype(float)
    out = {"t": pred["t"], "fps": pred["fps"], "verb": np.full(pred["verb"].shape, floor, np.float32),
           "noun": np.full(pred["noun"].shape, floor, np.float32), "action": np.full(pred["action"].shape, floor, np.float32)}
    rows = []
    for r in narr.itertuples():
        if r.main_action_classes:
            vk, nk = verb_key.get(r.main_action_classes[0][0]), noun_key.get(r.main_action_classes[0][1])
            rows.append((r.start_timestamp, r.end_timestamp, verb_row.get(vk), noun_row.get(nk), action_row.get(f"{vk} {nk}")))
    for i, tt in enumerate(ts):
        now = [r for r in rows if r[0] <= tt <= r[1]]
        for _, _, v, n, a in now:
            for key, j in (("verb", v), ("noun", n), ("action", a)):
                if j is not None:
                    out[key][i, j] += p / len(now)
    return out


def mask_step(p: dict, rows: list[int], floor: float = 0.001) -> dict:
    """A probe output with the given action rows (those only a skipped step has) set to floor."""
    out = {key: v.copy() if hasattr(v, "copy") else v for key, v in p.items()}
    out["action"][:, rows] = floor
    return out
