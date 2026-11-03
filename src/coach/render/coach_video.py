"""The combined coach video (stage 19): the cooking video with the coach's advice, beside a panel of model outputs.

Left: the video, with the advice as a banner for a few seconds when d1 says to speak. Right: the world model's
expected actions, the coach's latest advice (or "thinking…" while a question is out), d1's next move and, from
stage 23 on, the checklist. Bottom: a strip with the annotated steps and the coach's thinking time.
"""
from __future__ import annotations

import functools
import textwrap
import time
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

from ..coaching.answers import advice_text
from .guide_video import ACCENT, GOOD, H, INK, MUTED, PANEL, SIDE, W, font

font = functools.lru_cache(maxsize=None)(font)  # loading the TrueType file on every call was the slowest part

STRIP_H, BLUE = 56, (86, 160, 233)
OUT_BG, OUT_INK, OUT_MUTED = (255, 255, 255), (25, 25, 32), (100, 100, 112)
BAR_WM, BAR_D1, LABEL = (214, 140, 40), (40, 150, 85), (175, 175, 190)
BAR_LEN, BAR_TRACK = 130, (218, 218, 224)
ABOUT = {  # one sentence each: what it does, which model, what it reads
    "wm": [("Description", "Predicts what the cook will do about a second from now."),
           ("Model", "Meta V-JEPA 2 with an EPIC-KITCHENS action probe."),
           ("Input", "The last 3.2 seconds of the cooking video.")],
    "coach": [("Description", "Says what to do next and why, using the recipe."),
              ("Model", "Meta Muse Glimmer 30B."),
              ("Input", "The recipe, the cook's recent actions and the world model's prediction.")],
    "d1": [("Description", "Picks the next recipe action, every second."),
           ("Model", "Liquid AI d1-2B."),
           ("Input", "The coach's advice, the world model's prediction and the current step.")],
}



def render_coach_video(tl: dict, video, out, icons_dir, end_s: float | None = None, out_fps: int = 15, banner_s: float = 6,
                       show_about: bool = False, fix_advice: bool = True) -> str:
    """Render run `tl` (a coach_*.json run) over `video` into `out` (mp4); returns a one-line summary.

    end_s: stop after this many seconds (None = whole video). show_about: the Description / Model / Input bullets
    (the demo page has them, so the video shows outputs only). fix_advice: show an answer's Next part when it was
    saved as just "Where:" (runs from before the parser fix)."""
    SHOW_ABOUT = show_about
    calls = [dict(c, next=advice_text(c["next"], c.get("text"))) if fix_advice else c for c in tl["calls"]]
    T_TICKS = np.array([k["t"] for k in tl["ticks"]])
    ICONS = {k: Image.open(Path(icons_dir) / f"{k}.png").convert("RGBA").resize((28, 28), Image.LANCZOS)
             for k in ("chef", "recipe")}
    steps_txt = tl["steps"]
    cap = cv2.VideoCapture(str(video))
    vfps = cap.get(cv2.CAP_PROP_FPS)
    end = min(cap.get(cv2.CAP_PROP_FRAME_COUNT) / vfps, float(T_TICKS[-1]) + 1, end_s or 1e9)
    strip = Image.new("RGB", (W, STRIP_H), (18, 18, 24))
    sd = ImageDraw.Draw(strip)
    x0s, x1s = 120, W - 10
    to_x = lambda t: x0s + (x1s - x0s) * t / end
    sd.text((8, 6), "annotated step", font=font(11), fill=MUTED)
    sd.text((8, 32), "coach thinking", font=font(11), fill=MUTED)
    colours = [tuple(int(255 * c) for c in plt.cm.tab10(k)[:3]) for k in range(len(steps_txt))]
    for k, s0, s1 in tl["truth"]:
        if s0 < end:
            sd.rectangle([to_x(s0), 8, max(to_x(s0) + 1, to_x(min(s1, end))), 22], fill=colours[int(k)])
    for c in calls:
        if c["t"] < end:
            sd.rectangle([to_x(c["t"]), 34, max(to_x(c["t"]) + 2, to_x(min(c["ready"], end))), 48], fill=BLUE)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"avc1"), out_fps, (W, H + STRIP_H))
    skip = max(0, int(vfps / out_fps) - 1)
    t_start = time.perf_counter()

    def section(img, d, x, y, title, colour, icon, about) -> int:
        """Title plus Description / Model / Input bullets; returns the y below them."""
        tx = x
        if icon:
            img.paste(ICONS[icon], (x, y - 5), ICONS[icon])
            tx = x + 34
        d.text((tx, y), title, font=font(16, True), fill=colour)
        y += 24
        for label, text in about if SHOW_ABOUT else []:
            d.text((x + 2, y), "•", font=font(12, True), fill=LABEL)
            d.text((x + 14, y), f"{label}:", font=font(12, True), fill=LABEL)
            lx = x + 14 + d.textlength(f"{label}: ", font=font(12, True))
            d.text((lx, y), text, font=font(12), fill=MUTED)
            y += 16
        return y + (4 if SHOW_ABOUT else 6)

    def out_box(d, x, y, h) -> None:
        d.rounded_rectangle([x - 8, y, W - 14, y + h], radius=8, fill=OUT_BG)

    def out_bars(d, x, y, rows, colour) -> int:
        """A grey track as long as confidence 1.0, filled in colour up to the confidence."""
        for label, p in rows:
            d.rounded_rectangle([x, y + 4, x + BAR_LEN, y + 15], radius=3, fill=BAR_TRACK)
            fill = int(round(BAR_LEN * min(1.0, max(0.0, p))))
            if fill >= 2:
                d.rounded_rectangle([x, y + 4, x + fill, y + 15], radius=3, fill=colour)
            d.text((x + 142, y), f"{label}  {p:.2f}", font=font(15), fill=OUT_INK)
            y += 21
        return y

    def draw_panel(t: float, i: int, ready: list, asked: list) -> np.ndarray:
        """Strip + right-hand panel as a BGR frame; the video is pasted over its left part per frame."""
        tick = tl["ticks"][i]
        memory = "ledger" in tick
        img = Image.new("RGB", (W, H + STRIP_H), PANEL)
        img.paste(strip, (0, H))
        d = ImageDraw.Draw(img, "RGBA")
        x = SIDE + 22
        d.text((x, 8), f"t = {int(t // 60)}:{int(t % 60):02d}", font=font(20, True), fill=INK)

        # 1. world model
        y = section(img, d, x, 40, "World Model's User Next Actions Predictions", ACCENT, None, ABOUT["wm"])
        recent = tick.get("recent")  # stage 26: the action segments the coach reasons over
        box_h = 92 + (20 if recent else 0)
        out_box(d, x, y, box_h)
        yy = out_bars(d, x + 4, y + 7, [(a, p) for a, p in tick["wm"]], BAR_WM)
        ann = sorted(int(k) + 1 for k, s0, s1 in tl["truth"] if s0 <= t <= s1)
        d.text((x + 4, yy + 2), f"step tracker: step {tick['tracker'] + 1}   ·   annotated: {', '.join(map(str, ann)) or 'none'}",
               font=font(13), fill=OUT_MUTED)
        if recent:
            acts = " → ".join(r.split(" s ", 1)[-1].split(" (")[0] for r in recent)
            d.text((x + 4, yy + 22), textwrap.shorten(f"recent actions: {acts}", 72, placeholder="…"), font=font(13, True), fill=OUT_INK)
        y += box_h + 12

        # 2. coach
        about = ABOUT["coach"] if not memory else ABOUT["coach"][:2] + [
            ("Input", "The recipe, its checklist, recent actions and what the cook should vs. is doing.")]
        y = section(img, d, x, y, "Coach's Suggestions", BLUE, "chef", about)
        advice = textwrap.wrap(ready[-1]["next"], 60)[:(5 if memory else 6) + (0 if SHOW_ABOUT else 3)] if ready else []
        h = 14 + 18 * (bool(ready) + bool(asked)) + 20 * max(1, len(advice))
        out_box(d, x, y, h)
        yy = y + 7
        if asked:
            d.text((x + 4, yy), f"thinking… asked at {asked[-1]['t']:.0f} s, {t - asked[-1]['t']:.0f} s so far",
                   font=font(13), fill=OUT_MUTED)
            yy += 18
        if ready:
            c = ready[-1]
            why = f" · {c['trigger']}" if c.get("trigger") else ""
            d.text((x + 4, yy), f"advice from {c['t']:.0f} s (answered in {c['sec']:.0f} s{why})", font=font(13), fill=OUT_MUTED)
            yy += 18
            for line in advice:
                d.text((x + 4, yy), line, font=font(15), fill=OUT_INK)
                yy += 20
        else:
            d.text((x + 4, yy), "no advice yet", font=font(15), fill=OUT_MUTED)
        y += h + 12

        # 3. decision model
        about = ABOUT["d1"] if not memory else ABOUT["d1"][:2] + [
            ("Input", "The coach's advice, the checklist, the prediction and the current step.")]
        y = section(img, d, x, y, "Decision Model: Next Recipe Move", GOOD, "recipe", about)
        h = 14 + 21 * 3 + 21 * 3 + (44 if memory else 0)
        out_box(d, x, y, h)
        yy = out_bars(d, x + 4, y + 7, [(f"{a}  (step {s})", p) for a, s, p in tick["d1"]], BAR_D1)
        def labelled(yl, label, text, fill=OUT_INK):
            d.text((x + 4, yl), label, font=font(14, True), fill=OUT_INK)
            d.text((x + 8 + d.textlength(label, font=font(14, True)), yl), text, font=font(14), fill=fill)
        cur_k = tick["tracker"] + 1
        labelled(yy + 1, "User Current Step:", f"{cur_k}. " + textwrap.shorten(steps_txt[cur_k - 1], 40, placeholder="…"))
        labelled(yy + 22, "Next Step:", f"{tick['d1_step']}. " + textwrap.shorten(steps_txt[tick['d1_step'] - 1], 46, placeholder="…"))
        labelled(yy + 43, "Remind the Cook Now?", f"P = {tick['speak']:.2f}", BAR_D1 if tick["speak"] > 0.5 else OUT_MUTED)
        yy += 21
        if memory:  # stage 23: the coach's checklist and should-vs-doing
            marks = {"done": "✓", "in progress": "▶", "not started": "○"}
            d.text((x + 4, yy + 43), "checklist:  " + "   ".join(f"{marks[s]}{k + 1}" for k, s in enumerate(tick["ledger"])),
                   font=font(15, True), fill=OUT_INK)
            state = "aligned" if tick["aligned"] else f"misaligned {tick['streak']} s"
            d.text((x + 4, yy + 64), textwrap.shorten(f"should: {tick['should']}  ·  doing: {tick['wm'][0][0]}  ·  {state}", 68,
                                                       placeholder="…"), font=font(13), fill=BAR_D1 if tick["aligned"] else (200, 70, 50))
        return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

    def draw_banner(text: str) -> np.ndarray:
        """The advice overlay for the video's bottom edge (black = see-through)."""
        lines_ = textwrap.wrap(text, 52)[:3]
        img = Image.new("RGB", (SIDE, 52 + 26 * len(lines_)), (0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((20, 12), "COACH", font=font(20, True), fill=BLUE)
        for k, line in enumerate(lines_):
            d.text((20, 44 + 26 * k), line, font=font(19), fill=INK)
        return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

    key, frame_base, banner = None, None, None
    cursor = (INK[2], INK[1], INK[0])
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        t = cap.get(cv2.CAP_PROP_POS_FRAMES) / vfps
        if t > end:
            break
        for _ in range(skip):
            cap.grab()
        i = max(0, int(np.searchsorted(T_TICKS, t, side="right")) - 1)
        ready = [c for c in calls if c["ready"] <= t]
        asked = [c for c in calls if c["t"] <= t < c["ready"]]
        show = bool(ready) and t - ready[-1]["ready"] <= banner_s and tl["ticks"][i]["speak"] > 0.5
        new_key = (i, int(t), len(ready), len(asked), show)
        if new_key != key:  # the panel changes about once a second, not every frame
            key, frame_base = new_key, draw_panel(t, i, ready, asked)
            banner = draw_banner(ready[-1]["next"]) if show else None
        frame = frame_base.copy()
        frame[:H, :SIDE] = cv2.resize(bgr, (SIDE, SIDE), interpolation=cv2.INTER_AREA)
        if banner is not None:
            rows = frame[H - banner.shape[0]:H, :SIDE]
            text = banner.any(axis=2)
            rows[:] = (rows * 0.25).astype(np.uint8)
            rows[text] = banner[text]
        xc = int(to_x(t))
        cv2.line(frame, (xc, H + 2), (xc, H + STRIP_H - 2), cursor, 2)
        writer.write(frame)
    writer.release()
    return f"wrote {out} ({Path(out).stat().st_size / 1e6:.0f} MB, {end:.0f} s of video) in {time.perf_counter() - t_start:.0f} s"
