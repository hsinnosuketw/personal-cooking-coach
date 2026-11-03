"""Pick moments from a precomputed video and save what the world model predicted at each.

  python3 -m coach.render.demo_frames VIDEO.mp4 PRED.npz --recipe P08_R03 --out DIR [--extra 12]

For every annotated step start (taken 1 s early, as the model sees it) plus
`extra` evenly spaced moments that have a narration 1 s later: the last
frame the model saw (JPEG), its top-5 verbs, nouns and actions for ~1 s
ahead, the guide's belief over the recipe steps, and what HD-EPIC's
narrators say actually happened next. Writes DIR/frames.json + DIR/*.jpg.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from ..perception.action_bank import ActionBankRepository
from ..data.extractors import HDEpicExtractor
from .guide_video import action_names, replay, truth_steps
from ..data.vocab import Vocab


def top(probs: np.ndarray, names, k: int = 5) -> list[dict]:
    p = probs.astype(float)
    return [{"name": names[i], "p": round(float(p[i]), 3)} for i in np.argsort(-p)[:k]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("pred", type=Path)
    ap.add_argument("--recipe", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--extra", type=int, default=12)
    args = ap.parse_args()

    vocab = Vocab.load()
    hd = HDEpicExtractor(vocab)
    steps = hd.extract_steps(args.recipe)
    bank = ActionBankRepository(vocab).from_steps(steps)
    pred = dict(np.load(args.pred))
    ticks = pred["t"]
    results = replay(bank, pred)
    truth = truth_steps(hd, args.recipe, args.video.stem)
    narr = hd.narr[hd.narr.video_id == args.video.stem]
    actions = action_names()
    verbs = sorted(vocab.verb_row, key=vocab.verb_row.get)
    nouns = sorted(vocab.noun_row, key=vocab.noun_row.get)

    def next_narration(t: float) -> str | None:
        """What the narrators say happens in the ~2 s after t + 1."""
        rows = narr[(narr.start_timestamp <= t + 3.0) & (narr.end_timestamp >= t + 1.0)]
        return rows.sort_values("start_timestamp").narration.str.strip().iloc[0] if len(rows) else None

    first_start = {}
    for k, s0, _ in truth:
        first_start[k] = min(first_start.get(k, s0), s0)
    moments = {int(np.searchsorted(ticks, s0 - 1.0) - 1): f"step {k + 1} is about to start"
               for k, s0 in sorted(first_start.items(), key=lambda x: x[1])}
    candidates = [i for i, t in enumerate(ticks) if next_narration(t)]
    for i in np.linspace(0, len(candidates) - 1, args.extra).astype(int):
        moments.setdefault(candidates[i], "sample moment")
    moments = {i: why for i, why in sorted(moments.items()) if i >= 0}

    args.out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(args.video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = []
    for i, why in moments.items():
        t = float(ticks[i])
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(t * fps) - 1))
        ok, bgr = cap.read()
        if not ok:
            continue
        name = f"t{int(t):04d}.jpg"
        cv2.imwrite(str(args.out / name), cv2.resize(bgr, (640, 640)), [cv2.IMWRITE_JPEG_QUALITY, 85])
        r = results[i]
        post = r.extras["posterior"]
        out.append({
            "t": round(t, 1), "why": why, "image": name,
            "next_narration": next_narration(t),
            "annotated_steps": sorted(k + 1 for k, s0, s1 in truth if s0 <= t + 1.0 <= s1),
            "top5": {"action": top(pred["action"][i], actions), "verb": top(pred["verb"][i], verbs),
                     "noun": top(pred["noun"][i], nouns)},
            "guide": {"current_step": r.extras["current"] + 1,
                      "belief": [{"step": k + 1, "p": round(float(p), 3)} for k, p in enumerate(post)]},
        })
    (args.out / "frames.json").write_text(json.dumps({
        "recipe": args.recipe, "name": hd.recipes[args.recipe]["name"], "video": args.video.stem,
        "steps": [{"step": s.order + 1, "text": s.text} for s in steps], "frames": out}, indent=1), encoding="utf-8")
    print(f"wrote {len(out)} frames to {args.out}")


if __name__ == "__main__":
    main()
