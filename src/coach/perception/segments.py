"""Action segments: the probe's per-second top action, smoothed and cut into runs of one action (stage 24).

The coach reasons over segments ("12-19 s take egg (step 1)") instead of per-second labels. A segment is only known
once it has ended, so each one carries `done_at`, the tick at which a live system would have it.
"""
from __future__ import annotations

from collections.abc import Sequence


def smoothed(labels: Sequence[str], i: int, window_s: int) -> str:
    """The most common label in the last `window_s` ticks up to i (ties: the most recent)."""
    window = list(labels[max(0, i - window_s + 1): i + 1])
    return max(set(window), key=lambda a: (window.count(a), window[::-1].index(a) * -1))


def build_segments(top_label: Sequence[str], t: Sequence[float], steps_of: dict, smooth_s: int, min_seg_s: float,
                   merge_gap_s: float) -> list[dict]:
    """Segments of at least min_seg_s seconds; touching segments about the same object are merged
    ("put phone, check phone, put phone" is one phone episode)."""
    labels = [smoothed(top_label, i, smooth_s) for i in range(len(top_label))]
    segs, start = [], 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            t0, t1 = float(t[start]), float(t[i - 1]) + 1
            if t1 - t0 >= min_seg_s:
                a = labels[start]
                segs.append({"t0": t0, "t1": t1, "action": a, "steps": steps_of.get(a, []), "done_at": i})
            start = i
    merged = []
    for sg in segs:
        prev = merged[-1] if merged else None
        if prev and prev["noun"] == sg["action"].split(" ", 1)[-1] and sg["t0"] - prev["t1"] <= merge_gap_s:
            verbs = prev["verbs"] + [v for v in [sg["action"].split(" ", 1)[0]] if v not in prev["verbs"]]
            prev.update(t1=sg["t1"], done_at=sg["done_at"], verbs=verbs, action="/".join(verbs) + " " + prev["noun"],
                        steps=sorted(set(prev["steps"]) | set(sg["steps"])))
        else:
            merged.append(dict(sg, noun=sg["action"].split(" ", 1)[-1], verbs=[sg["action"].split(" ", 1)[0]]))
    return merged


def seg_line(s: dict) -> str:
    where = "/".join(f"step {k + 1}" for k in s["steps"]) or "other"
    return f"{s['t0']:.0f}-{s['t1']:.0f} s {s['action']} ({where})"


def doing_step(recent: list[dict]) -> int | None:
    """The step most of the last three segments belong to, if any."""
    votes = [k for s in recent[-3:] for k in s["steps"]]
    return max(set(votes), key=votes.count) if votes else None
