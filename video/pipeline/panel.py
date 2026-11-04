"""The demo page's model panel (src/coach/render/coach_video.py) as data: where each row sits at a given second, a crisp
redraw of the coach's box for the zoom, and the moments the models are right.

    PYTHONPATH=src python3 video/pipeline/panel.py check     # redraws each zoom box at 1x and compares it with the page video

The page video is 1280x776; the panel shots crop its top 1280x720 and scale it 1.5x, so a panel point (x, y) is at
(1.5x, 1.5y) in the film. The layout numbers below repeat draw_panel() for the memory runs (SHOW_ABOUT off).
"""
import functools
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from coach.coaching.answers import advice_text
from coach.render.guide_video import font as _font

font = functools.lru_cache(maxsize=None)(_font)
ROOT = Path(__file__).resolve().parents[2]
RUN = "coach_adaptive_remind_parallel_hdtags_{}"
SCALE = 1.5                       # page video -> film
BOX_X0, BOX_X1 = 734, 1266        # out_box(): x - 8 .. W - 14, with x = SIDE + 22
TEXT_X = 746                      # x + 4
OUT_BG, OUT_INK, OUT_MUTED = (255, 255, 255), (25, 25, 32), (100, 100, 112)
MARK = (47, 158, 110, 92)         # the film's memory green, see-through, behind the highlighted words
ADVICE_LINES = 8                  # memory runs: 5 + 3 lines when the About bullets are off


@functools.lru_cache(maxsize=None)
def load(video):
    run = json.loads((ROOT / "results" / f"{RUN.format(video)}.json").read_text())
    run["calls"] = [dict(c, next=advice_text(c["next"], c.get("text"))) for c in run["calls"]]
    run["_t"] = np.array([k["t"] for k in run["ticks"]])
    return run


def state(video, t):
    """What the page draws at second t: the tick, the answered calls, the pending one."""
    run = load(video)
    i = max(0, int(np.searchsorted(run["_t"], t, side="right")) - 1)
    ready = [c for c in run["calls"] if c["ready"] <= t]
    asked = [c for c in run["calls"] if c["t"] <= t < c["ready"]]
    return run["ticks"][i], ready, asked


def layout(video, t):
    """Panel rows at second t, in page-video pixels: text tops of the 3 world-model and 3 d1 rows, and the coach box."""
    tick, ready, asked = state(video, t)
    wm_top = 70
    wm_h = 92 + (20 if tick.get("recent") else 0)
    coach_top = wm_top + wm_h + 12 + 30
    advice = textwrap.wrap(ready[-1]["next"], 60)[:ADVICE_LINES] if ready else []
    coach_h = 14 + 18 * (bool(ready) + bool(asked)) + 20 * max(1, len(advice))
    d1_top = coach_top + coach_h + 12 + 30
    return {"tick": tick, "ready": ready, "asked": asked, "advice": advice,
            "wm_rows": [wm_top + 7 + 21 * k for k in range(len(tick["wm"]))],
            "coach": (BOX_X0, coach_top, BOX_X1, coach_top + coach_h),
            "d1_rows": [d1_top + 7 + 21 * k for k in range(len(tick["d1"]))]}


def coach_box(video, t, scale=3, phrase=None):
    """The coach's box as the page draws it at second t, redrawn at `scale` (RGBA, transparent corners). With
    `phrase`, the words of that verbatim phrase sit on a green marker; it must lie within the lines the page shows."""
    lay = layout(video, t)
    x0, y0, x1, y1 = lay["coach"]
    s = scale
    img = Image.new("RGBA", ((x1 - x0 + 1) * s, (y1 - y0 + 1) * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([0, 0, (x1 - x0) * s, (y1 - y0) * s], radius=8 * s, fill=OUT_BG)
    tx = (TEXT_X - x0) * s
    yy = 7
    if lay["asked"]:
        a = lay["asked"][-1]
        d.text((tx, yy * s), f"thinking… asked at {a['t']:.0f} s, {t - a['t']:.0f} s so far", font=font(13 * s), fill=OUT_MUTED)
        yy += 18
    c = lay["ready"][-1]
    why = f" · {c['trigger']}" if c.get("trigger") else ""
    d.text((tx, yy * s), f"advice from {c['t']:.0f} s (answered in {c['sec']:.0f} s{why})", font=font(13 * s), fill=OUT_MUTED)
    yy += 18
    lines = lay["advice"]
    if phrase:
        joined = " ".join(lines)
        a = joined.find(phrase)
        assert a >= 0, f"{phrase!r} is not in the {len(lines)} lines the panel shows at {t:.1f} s"
        b, pos = a + len(phrase), 0
        for k, line in enumerate(lines):   # the marker, line by line, behind the text
            la, lb = max(a, pos) - pos, min(b, pos + len(line)) - pos
            if la < lb:
                f = font(15 * s)
                mx0 = tx + d.textlength(line[:la], font=f) - 2 * s
                mx1 = tx + d.textlength(line[:lb], font=f) + 2 * s
                d.rounded_rectangle([mx0, (yy + 20 * k) * s, mx1, (yy + 20 * k + 19) * s], radius=3 * s, fill=MARK)
            pos += len(line) + 1
    for k, line in enumerate(lines):
        d.text((tx, (yy + 20 * k) * s), line, font=font(15 * s), fill=OUT_INK)
    return img, lay["coach"]


def calls_change(video, a, b):
    """Times in (a, b] where an answer arrives or a new call goes out: the coach box changes there."""
    return sorted({x for c in load(video)["calls"] for x in (c["t"], c["ready"]) if a < x <= b})


@functools.lru_cache(maxsize=None)
def hits(video):
    """(world-model hits per tick index, d1 moves done as [(action, time it happens)]), scored by find_moments."""
    sys.path.insert(0, str(Path(__file__).parent))
    import find_moments
    from coach.data.extractors import HDEpicExtractor
    from coach.data.vocab import Vocab
    _, rows = find_moments.score(video[:3], HDEpicExtractor(Vocab.load()))
    wm = {i: r["wm_hit"] for i, r in enumerate(rows)}
    done = sorted({(a, round(r["t"] + dt, 2)) for r in rows for a, _, dt in r["d1_done"]}, key=lambda x: x[1])
    return wm, done


def frame_crop(video, t, box):
    """The page video's pixels inside `box` at second t (for the redraw check)."""
    x0, y0, x1, y1 = box
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(ROOT / "results" / f"{RUN.format(video)}.mp4"),
                          "-frames:v", "1", "-vf", f"format=rgb24,crop={x1 - x0 + 1}:{y1 - y0 + 1}:{x0}:{y0}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(y1 - y0 + 1, x1 - x0 + 1, 3)


def check(moments):
    """Mean absolute difference between the 1x redraw and the page video, per zoom moment (0-255; compression ~3)."""
    for video, t in moments:
        img, box = coach_box(video, t, scale=1)
        flat = Image.new("RGB", img.size, (24, 24, 32))
        flat.paste(img, (0, 0), img)
        real = frame_crop(video, t, box)
        diff = np.abs(np.asarray(flat, np.int16) - real.astype(np.int16)).mean()
        print(f"{video} {t:7.2f}s  box {box}  mean |diff| {diff:5.2f}")


if __name__ == "__main__" and sys.argv[1:] == ["check"]:
    check([("P08-20240614-085000", 40.0), ("P08-20240614-085000", 295.0), ("P02-20240210-113925", 409.0)])
