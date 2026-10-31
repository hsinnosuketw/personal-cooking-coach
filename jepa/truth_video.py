"""Render the video with HD-EPIC's ground truth next to what the model predicted.

  python3 -m jepa.truth_video VIDEO.mp4 PRED.npz --recipe P08_R03 --out truth.mp4 [--steps-json S.json]

Right panel, top to bottom: the action HD-EPIC's narrators recorded at this
moment (text, main action, hands); what V-JEPA 2 + probe predicted one
second earlier for this moment, green where it matches the true verb or
noun, with the running top-5 hit rate; the annotated recipe step against
the step tracker's choice. Bottom: the whole video as two colour strips
(annotated steps above, tracker below) with a cursor. No torch needed.
"""
from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .action_bank import ActionBankRepository
from .extractors import HDEpicExtractor, ManualRecipeExtractor
from .guide_video import ACCENT, GOOD, H, INK, MUTED, PANEL, SIDE, W, action_names, active, font, replay, truth_steps
from .vocab import Vocab

STEP_COLOURS = [(230, 159, 0), (86, 180, 233), (0, 158, 115), (240, 228, 66), (0, 114, 178), (213, 94, 0),
                (204, 121, 167), (150, 150, 150)]
BAD = (220, 90, 80)
STRIP_H = 64


def step_colour(k: int) -> tuple:
    return STEP_COLOURS[k % len(STEP_COLOURS)] if k >= 0 else (60, 60, 70)


def render(video: Path, pred_path: Path, recipe: str, out: Path, steps_json: Path | None, out_fps: int = 15,
           stop: float | None = None) -> dict:
    vocab = Vocab.load()
    hd = HDEpicExtractor(vocab)
    steps = ManualRecipeExtractor(vocab).extract_steps(str(steps_json)) if steps_json else hd.extract_steps(recipe)
    tracker_from = "VLM hand-level tags" if steps_json else "HD-EPIC tags"
    pred = dict(np.load(pred_path))
    ticks = pred["t"]
    results = replay(ActionBankRepository(vocab).from_steps(steps), pred)
    current = np.array([r.extras["current"] for r in results])
    truth = truth_steps(hd, recipe, video.stem)
    narr = hd.narr[hd.narr.video_id == video.stem].sort_values("start_timestamp")
    names = action_names()
    verbs = sorted(vocab.verb_row, key=vocab.verb_row.get)
    nouns = sorted(vocab.noun_row, key=vocab.noun_row.get)

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    end = min(total, float(ticks[-1]) + 1)
    stop = stop or end

    # the bottom strips, drawn once
    strip = Image.new("RGB", (W, STRIP_H), (18, 18, 24))
    sd = ImageDraw.Draw(strip)
    sd.text((8, 4), "annotated step", font=font(11), fill=MUTED)
    sd.text((8, 36), "tracker", font=font(11), fill=MUTED)
    x0, x1 = 110, W - 10
    to_x = lambda t: x0 + (x1 - x0) * t / end
    for k, s0, s1 in truth:
        sd.rectangle([to_x(s0), 18, max(to_x(s0) + 1, to_x(s1)), 30], fill=step_colour(k))
    for i, t in enumerate(ticks):
        if current[i] >= 0:
            sd.rectangle([to_x(t), 50, to_x(t) + max(1, (x1 - x0) / end), 62], fill=step_colour(int(current[i])))

    hits = {"verb": [0, 0], "noun": [0, 0]}
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"avc1"), out_fps, (W, H + STRIP_H))
    skip = max(0, int(fps / out_fps) - 1)
    last_scored = -1
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        t = cap.get(cv2.CAP_PROP_POS_FRAMES) / fps
        if t > stop:
            break
        for _ in range(skip):
            cap.grab()
        img = Image.new("RGB", (W, H + STRIP_H), PANEL)
        img.paste(Image.fromarray(cv2.cvtColor(cv2.resize(bgr, (SIDE, SIDE)), cv2.COLOR_BGR2RGB)), (0, 0))
        img.paste(strip, (0, H))
        d = ImageDraw.Draw(img)
        d.line([to_x(t), H + 2, to_x(t), H + STRIP_H - 2], fill=INK, width=2)
        x = SIDE + 24
        d.text((x, 14), f"Ground truth check   t = {int(t // 60)}:{int(t % 60):02d}", font=font(22, True), fill=INK)

        # 1. what really happened now
        now = narr[(narr.start_timestamp <= t) & (narr.end_timestamp >= t)]
        d.text((x, 50), "HD-EPIC narrators: happening now", font=font(16, True), fill=GOOD)
        y = 74
        true_v, true_n = set(), set()
        if len(now):
            r = now.iloc[-1]
            for line in textwrap.wrap(r.narration.strip(), 58)[:2]:
                d.text((x, y), line, font=font(15), fill=INK)
                y += 20
            pairs = [(hd.verb_key.get(a), hd.noun_key.get(b)) for a, b in r.main_action_classes]
            true_v = {a for a, _ in pairs if a}
            true_n = {b for _, b in pairs if b}
            d.text((x, y), "main action: " + ", ".join(f"{a} {b}" for a, b in pairs) +
                   f"   ({', '.join(r.hands)})", font=font(14), fill=MUTED)
            y += 22
        else:
            d.text((x, y), "no action annotated at this moment", font=font(15), fill=MUTED)
            y += 42

        # 2. what the model predicted 1 s ago for this moment
        i = int(np.searchsorted(ticks, t - 1.0, side="right")) - 1
        y += 8
        d.text((x, y), "V-JEPA 2 predicted 1 s earlier (top 5)", font=font(16, True), fill=ACCENT)
        y += 24
        if i >= 0:
            for key, labels, truth_set in (("verb", verbs, true_v), ("noun", nouns, true_n)):
                top = np.argsort(-pred[key][i].astype(float))[:5]
                xx = x
                d.text((xx, y), f"{key}s:", font=font(14), fill=MUTED)
                xx += 56
                for j in top:
                    word = labels[j]
                    col = GOOD if word in truth_set else (INK if truth_set else MUTED)
                    d.text((xx, y), word, font=font(14, word in truth_set), fill=col)
                    xx += d.textlength(word, font=font(14, word in truth_set)) + 14
                if truth_set and i != last_scored:
                    hits[key][0] += any(labels[j] in truth_set for j in top)
                    hits[key][1] += 1
                y += 22
            last_scored = i
            act = np.argsort(-pred["action"][i].astype(float))[:3]
            d.text((x, y), "actions: " + ", ".join(names[a] for a in act), font=font(14), fill=MUTED)
            y += 22
        rate = lambda k: f"{100 * hits[k][0] / hits[k][1]:.0f}%" if hits[k][1] else "-"
        d.text((x, y), f"so far, true verb in top 5: {rate('verb')}   true noun in top 5: {rate('noun')}",
               font=font(13), fill=MUTED)
        y += 34

        # 3. recipe step: annotated vs tracker
        ann = sorted(active(truth, t))
        cur = int(current[i]) if i >= 0 else -1
        d.text((x, y), "Recipe step", font=font(16, True), fill=ACCENT)
        y += 26
        right = cur in ann if ann else None
        d.text((x, y), "annotated:", font=font(14), fill=MUTED)
        d.text((x + 92, y), ", ".join(str(k + 1) for k in ann) if ann else "none (between steps)", font=font(14, True),
               fill=INK)
        y += 22
        d.text((x, y), f"tracker ({tracker_from}):", font=font(14), fill=MUTED)
        y += 20
        label = f"{cur + 1}. {steps[cur].text}" if cur >= 0 else "not started"
        for line in textwrap.wrap(label, 58)[:2]:
            d.text((x, y), line, font=font(14, True), fill=GOOD if right else (BAD if right is False else INK))
            y += 20
        if right is not None:
            d.text((x, y), "matches the annotation" if right else "differs from the annotation", font=font(13),
                   fill=GOOD if right else BAD)
        # step legend
        y = H - 24 - 18 * len(steps)
        for k, s in enumerate(steps):
            d.rectangle([x, y + 4, x + 12, y + 14], fill=step_colour(k))
            d.text((x + 20, y), textwrap.shorten(f"{k + 1}. {s.text}", 60, placeholder="…"), font=font(12), fill=MUTED)
            y += 18
        writer.write(cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR))
    writer.release()
    summary = {"verb_top5_hit": round(hits["verb"][0] / max(1, hits["verb"][1]), 3),
               "noun_top5_hit": round(hits["noun"][0] / max(1, hits["noun"][1]), 3),
               "seconds_with_narration": hits["verb"][1], "tracker_from": tracker_from, "kind": "ground_truth"}
    out.with_suffix(".json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("pred", type=Path)
    ap.add_argument("--recipe", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--steps-json", type=Path, default=None, help="tracker steps (default: HD-EPIC's)")
    ap.add_argument("--end", type=float, default=None, help="stop rendering at this second (for a quick look)")
    args = ap.parse_args()
    print(json.dumps(render(args.video, args.pred, args.recipe, args.out, args.steps_json, stop=args.end), indent=1))


if __name__ == "__main__":
    main()
