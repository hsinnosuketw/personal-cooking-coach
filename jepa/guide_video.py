"""Render the cooking guide as a demo video, and score it against the annotations.

  python3 -m jepa.guide_video VIDEO.mp4 PRED.npz --recipe P08_R03 --out guide.mp4 [--speed 4]
  ... --steps-json nim_steps.json   use steps written by the NIM VLM instead of HD-EPIC's

Left: the cooking video, sped up. Right: what V-JEPA 2 expects about 1 s
ahead, every step's live score, the guide's current step and, for honesty,
the step HD-EPIC's annotators marked at that moment. When the scorer
decides a new step is starting, the frame freezes with a NEXT STEP banner.
Runs on the predictions precompute.py saved, so no torch is needed here.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .action_bank import ActionBankRepository
from .domain import Prediction
from .extractors import HDEpicExtractor, ManualRecipeExtractor
from .scorer import LatentStateScorer, match_scores
from .vocab import CACHE, Vocab, class_maps

W, H, SIDE = 1280, 720, 720
INK, MUTED, ACCENT, GOOD, PANEL = (235, 235, 240), (150, 150, 165), (255, 176, 59), (90, 200, 120), (24, 24, 32)
FREEZE_S = 2.5


def font(size: int, bold: bool = False):
    dejavu = f"DejaVuSans{'-Bold' if bold else ''}.ttf"
    for name in (f"/usr/share/fonts/truetype/dejavu/{dejavu}", dejavu, "/Library/Fonts/Arial.ttf",
                 "/System/Library/Fonts/Helvetica.ttc", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)  # scalable fallback, never the tiny bitmap font


def action_names() -> list[str]:
    import pandas as pd
    maps = class_maps(CACHE / "EPIC_100_train.csv")
    verbs = pd.read_csv(CACHE / "EPIC_100_verb_classes.csv").set_index("id").key
    nouns = pd.read_csv(CACHE / "EPIC_100_noun_classes.csv").set_index("id").key
    names = [""] * len(maps["actions"])
    for (v, n), row in maps["actions"].items():
        names[row] = f"{verbs[v]} {nouns[n]}"
    return names


def truth_steps(hd: HDEpicExtractor, recipe: str, video_id: str) -> list[tuple[int, float, float]]:
    order = {sid: i for i, sid in enumerate(hd.recipes[recipe]["steps"])}
    return [(order[sid], s0, s1) for sid, segs in hd.spans(recipe).items() for v, s0, s1 in segs if v == video_id]


def active(truth, t: float) -> set[int]:
    return {k for k, s0, s1 in truth if s0 <= t <= s1}


def replay(bank, pred: dict) -> list:
    """Run the scorer through every tick once; the video just looks results up."""
    scorer = LatentStateScorer(bank)
    match = match_scores(bank, pred["verb"].astype(float), pred["noun"].astype(float))
    return [scorer.evaluate(Prediction(float(t), pred["verb"][i], pred["noun"][i]), match[i])
            for i, t in enumerate(pred["t"])]


def evaluate(results, ticks, truth, n_steps: int) -> dict:
    """Guide's current step vs the step annotated ~1 s ahead, on ticks where one is."""
    rows = [(r.extras["current"], active(truth, t + 1.0)) for r, t in zip(results, ticks)]
    rows = [(c, a) for c, a in rows if a]
    hits = sum(c in a for c, a in rows)
    starts = sorted({min(s0 for k2, s0, _ in truth if k2 == k) for k, _, _ in truth})
    pauses = [r.timestamp for r in results if r.should_pause]
    near = sum(any(abs(p - s) <= 10 for p in pauses) for s in starts)
    return {"ticks_with_annotated_step": len(rows), "step_accuracy": round(hits / max(1, len(rows)), 3),
            "chance": round(float(np.mean([len(a) / n_steps for _, a in rows])) if rows else 0, 3),
            "pauses": len(pauses), "step_starts": len(starts), "starts_with_a_pause_within_10s": near}


def draw_panel(img: Image.Image, title: str, res, top_actions, truth_now: set[int], cands, t: float, note: str):
    d = ImageDraw.Draw(img)
    x0 = SIDE + 24
    d.rectangle([SIDE, 0, W, H], fill=PANEL)
    d.text((x0, 18), title, font=font(24, True), fill=INK)
    d.text((x0, 52), f"t = {int(t // 60)}:{int(t % 60):02d}   {note}", font=font(15), fill=MUTED)
    d.text((x0, 86), "V-JEPA 2 expects in ~1 s:", font=font(16, True), fill=ACCENT)
    for i, (name, p) in enumerate(top_actions):
        y = 112 + i * 24
        d.rectangle([x0, y + 4, x0 + int(150 * p), y + 18], fill=(110, 85, 40))
        d.text((x0 + 160, y), f"{name}  {p:.2f}", font=font(16), fill=INK)
    y = 112 + len(top_actions) * 24 + 18
    d.text((x0, y), "Recipe steps (bar = guide's belief)", font=font(16, True), fill=ACCENT)
    y += 30
    post = res.extras["posterior"] if res is not None else np.zeros(len(cands))
    cur = res.extras["current"] if res is not None else -1
    row_h = max(44, min(64, (H - y - 20) // max(1, len(cands))))
    for k, c in enumerate(cands):
        yy = y + k * row_h
        if k == cur:
            d.rectangle([x0 - 10, yy - 4, W - 12, yy + row_h - 8], outline=ACCENT, width=2)
        d.rectangle([x0, yy + row_h - 18, x0 + int((W - x0 - 40) * float(post[k])), yy + row_h - 12], fill=ACCENT)
        label = textwrap.shorten(f"{k + 1}. {c.raw_text}", 58, placeholder="…")
        d.text((x0, yy), label, font=font(15, k == cur), fill=INK if k == cur else MUTED)
        if k in truth_now:
            d.text((W - 96, yy), "annotated", font=font(12), fill=GOOD)


def banner(img: Image.Image, text: str):
    d = ImageDraw.Draw(img, "RGBA")
    lines = textwrap.wrap(text, 46)[:3]
    h = 70 + 32 * len(lines)
    d.rectangle([0, H - h, SIDE, H], fill=(0, 0, 0, 200))
    d.text((24, H - h + 16), "NEXT STEP", font=font(22, True), fill=ACCENT)
    for i, line in enumerate(lines):
        d.text((24, H - h + 52 + 32 * i), line, font=font(24), fill=INK)


def render(video: Path, pred_path: Path, recipe: str, out: Path, speed: float, steps_json: Path | None,
           start: float | None, end: float | None) -> dict:
    vocab = Vocab.load()
    hd = HDEpicExtractor(vocab)
    steps = ManualRecipeExtractor(vocab).extract_steps(str(steps_json)) if steps_json else hd.extract_steps(recipe)
    bank = ActionBankRepository(vocab).from_steps(steps)
    cands = bank.get_all_candidates()
    pred = dict(np.load(pred_path))
    results = replay(bank, pred)
    ticks = pred["t"]
    truth = truth_steps(hd, recipe, video.stem)
    summary = evaluate(results, ticks, truth, len(cands))
    if steps_json:  # its steps aren't HD-EPIC's, so step-number accuracy would compare different steps
        for k in ("step_accuracy", "chance", "ticks_with_annotated_step"):
            summary.pop(k)
    summary.update(recipe=recipe, steps_from="NIM VLM" if steps_json else "HD-EPIC annotations")
    names = action_names()

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    start = start if start is not None else max(0.0, min(s0 for _, s0, _ in truth) - 15)
    end = end if end is not None else min(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps, max(s1 for _, _, s1 in truth) + 10)
    out_fps = 30
    raw = out.with_suffix(".raw.mp4")
    writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), out_fps, (W, H))
    title = hd.recipes[recipe]["name"]
    note = f"{speed:g}x speed · steps: {summary['steps_from']}"
    shown_pauses = set()
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start * fps))
    t = start
    while t < end:
        ok, bgr = cap.read()
        if not ok:
            break
        src_t = cap.get(cv2.CAP_PROP_POS_FRAMES) / fps
        for _ in range(max(0, int(fps * speed / out_fps) - 1)):  # skip frames to reach the playback speed
            cap.grab()
        t = src_t
        i = int(np.searchsorted(ticks, t, side="right")) - 1
        res = results[i] if i >= 0 else None
        img = Image.new("RGB", (W, H))
        img.paste(Image.fromarray(cv2.cvtColor(cv2.resize(bgr, (SIDE, SIDE)), cv2.COLOR_BGR2RGB)), (0, 0))
        top = [] if i < 0 else [(names[a], float(pred["action"][i][a])) for a in np.argsort(-pred["action"][i].astype(float))[:3]]
        draw_panel(img, title, res, top, active(truth, t), cands, t, note)
        frame = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        writer.write(frame)
        if res is not None and res.should_pause and i not in shown_pauses:
            shown_pauses.add(i)
            banner(img, res.action.raw_text)
            frozen = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
            for _ in range(int(FREEZE_S * out_fps)):
                writer.write(frozen)
    writer.release()
    if shutil.which("ffmpeg"):  # H.264 so browsers and phones play it
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "23", "-movflags", "+faststart", str(out)], check=True)
        raw.unlink()
    else:
        raw.rename(out)
    out.with_suffix(".json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("pred", type=Path)
    ap.add_argument("--recipe", required=True, help="HD-EPIC recipe id, e.g. P08_R03 (also gives the ground truth)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--speed", type=float, default=4.0)
    ap.add_argument("--steps-json", type=Path, default=None)
    ap.add_argument("--start", type=float, default=None)
    ap.add_argument("--end", type=float, default=None)
    args = ap.parse_args()
    print(json.dumps(render(args.video, args.pred, args.recipe, args.out, args.speed, args.steps_json,
                            args.start, args.end), indent=1))


if __name__ == "__main__":
    main()
