"""Offline pass: run the world model over a whole cooking video, once per tick.

  python3 -m coach.perception.precompute VIDEO.mp4 --out results/P08-20240614-085000.npz [--stride 1] [--device cuda]

At each tick t the model sees the last 32 sampled frames (one every
int(fps / 8) frames, as in the EK100 eval) and predicts the verb, noun and
action about 1 s after t. The video is decoded once, front to back, with a
rolling buffer, instead of seeking per clip. Output (.npz): t, verb, noun,
action probabilities (float16), ready for the guide to replay in real time.
"""
from __future__ import annotations

import argparse
import collections
import time
from pathlib import Path

import cv2
import numpy as np
import torch

from . import clips
from .anticipate import load_model


def run(video: Path, out: Path, stride: float, device: torch.device, batch: int, end: float | None) -> None:
    model, probe, _ = load_model(device)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = int(fps / clips.FPS)
    last = min(n_frames, int((end or n_frames / fps) * fps))
    buf: collections.deque = collections.deque(maxlen=clips.FRAMES)
    ticks, pending, results = [], [], {"verb": [], "noun": [], "action": []}
    next_tick = clips.FRAMES * step / fps  # first tick once a full clip is buffered
    t0 = time.time()

    def flush():
        if not pending:
            return
        x = torch.stack(pending).to(device)
        with torch.no_grad():
            o = probe(model(x, torch.full((len(pending),), clips.ANTICIPATION_SEC, device=device)))
        for k in results:
            results[k].append(torch.sigmoid(o[k].float()).cpu().numpy().astype(np.float16))
        pending.clear()

    for i in range(last):
        if not cap.grab():
            break
        if i % step:
            continue
        ok, bgr = cap.retrieve()
        if not ok:
            break
        buf.append(clips.to_tensor(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)[None]))
        t = (i + 1) / fps
        if len(buf) == clips.FRAMES and t >= next_tick:
            ticks.append(t)
            pending.append(torch.cat(list(buf), dim=1))
            next_tick += stride
            if len(pending) == batch:
                flush()
                done = ticks[-1] / (last / fps)
                print(f"t={ticks[-1]:7.1f}s  {100 * done:5.1f}%  {time.time() - t0:6.0f}s elapsed", flush=True)
    flush()
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, t=np.array(ticks), fps=fps, **{k: np.concatenate(v) for k, v in results.items()})
    print(f"wrote {out}: {len(ticks)} ticks in {time.time() - t0:.0f}s")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--stride", type=float, default=1.0, help="seconds between ticks")
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--end", type=float, default=None, help="stop at this many seconds")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()
    run(args.video, args.out, args.stride, torch.device(args.device), args.batch, args.end)


if __name__ == "__main__":
    main()
