"""Storyboard of the rendered beats: stills at each beat's key moments plus a self-contained index.html.

    python3 video/pipeline/storyboard.py

Stills (960x540) are grabbed from video/out/beats/beat_XX.mp4 at the moments build.py lists in
video/hyperframes/keyframes.json, so they match the film frame for frame. Writes video/out/storyboard/.
"""
import html
import json
import shutil
import subprocess
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
OUT = VIDEO / "out" / "storyboard"
BEATS = {b["id"]: b for b in json.loads((VIDEO / "beats.json").read_text())["beats"]}
TIMES = json.loads((VIDEO / "audio" / "timings.json").read_text())
KEYS = json.loads((VIDEO / "hyperframes" / "keyframes.json").read_text())
FONTS = VIDEO / "hyperframes" / "assets" / "fonts"
e = html.escape
# The renders are BT.709 limited range; a JPEG is BT.601 full range. Without this the greens come out light.
JPEG_VF = "scale={w}:{h}:in_color_matrix=bt709:in_range=tv:out_color_matrix=bt601:out_range=pc,format=yuvj420p"


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def stills():
    (OUT / "img").mkdir(parents=True, exist_ok=True)
    shots = {}
    for bid in sorted(KEYS, key=int):
        src = VIDEO / "out" / "beats" / f"beat_{int(bid):02d}.mp4"
        dur = TIMES["beats"][bid]["duration"]
        for k, (t, note) in enumerate(KEYS[bid]):
            t = min(max(t, 0), dur - 1 / 30)
            fn = f"b{int(bid):02d}_{k}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-vf", JPEG_VF.format(w=960, h=540),
                            "-color_range", "pc", "-q:v", "3", "-threads", "3", str(OUT / "img" / fn)], check=True)
            shots.setdefault(bid, []).append((fn, t, note))
    return shots


def page(shots):
    cards = []
    for bid in sorted(shots, key=int):
        b, tm = BEATS[int(bid)], TIMES["beats"][bid]
        say = e(b["say"]).replace("Coach:", '<span class="cv">Coach</span>')
        figs = "".join(f'<figure><img src="img/{fn}" alt="{e(note)}" loading="lazy" width="960" height="540">'
                       f'<figcaption><span>{mmss(tm["start"] + t)}</span> {e(note)}</figcaption></figure>' for fn, t, note in shots[bid])
        n = len(shots[bid])
        cards.append(f"""<article class="beat {b['tone']}">
  <div class="stills n{min(n, 4)}">{figs}</div>
  <div class="text">
    <p class="when"><b>{mmss(tm['start'])}</b> · {tm['duration']:.1f} s · planned {e(b['time'])}</p>
    <h2>{e(b['label'])}</h2>
    <p class="k">Say</p><p class="say">{say}</p>
    <p class="k">Screen</p><p class="screen">{e(b['screen'])}</p>
  </div>
</article>""")
    total = TIMES["total"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Demo Storyboard v4</title>
<link rel="stylesheet" href="fonts/fonts.css">
<style>
:root {{ --paper: #f2f5f1; --surface: #fff; --ink: #1c1c1e; --muted: #6b6e6a; --line: #dde2db; --nomem: #e5484d; --mem: #2f9e6e;
  --sans: "Figtree", system-ui, sans-serif; --mono: "JetBrains Mono", ui-monospace, Menlo, monospace; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font-family: var(--sans); font-size: 16px; line-height: 1.5; padding: 40px 16px 80px; }}
.wrap {{ max-width: 1400px; margin: 0 auto; display: grid; gap: 28px; }}
header {{ display: grid; gap: 8px; max-width: 820px; }}
h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 3rem); font-weight: 700; letter-spacing: -0.02em; line-height: 1.05; }}
h1 i {{ font-family: "Instrument Serif", serif; font-weight: 400; color: var(--mem); }}
.eyebrow, .k, .when, figcaption span {{ font-family: var(--mono); font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }}
.lede {{ color: var(--muted); margin: 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 640px), 1fr)); gap: 20px; }}
.beat {{ background: var(--surface); border-radius: 14px; overflow: hidden; border-top: 4px solid var(--muted); box-shadow: 0 1px 2px rgba(0,0,0,.05), 0 8px 24px rgba(0,0,0,.06); display: grid; align-content: start; min-width: 0; }}
.beat.nomem {{ border-top-color: var(--nomem); }}
.beat.mem {{ border-top-color: var(--mem); }}
.stills {{ display: grid; gap: 2px; background: #111214; }}
.stills.n2 {{ grid-template-columns: 1fr 1fr; }}
.stills.n3, .stills.n4 {{ grid-template-columns: 1fr 1fr; }}
.stills.n3 figure:first-child {{ grid-column: span 2; }}
figure {{ margin: 0; position: relative; min-width: 0; }}
figure img {{ display: block; width: 100%; height: auto; }}
figcaption {{ position: absolute; left: 8px; bottom: 8px; right: 8px; font-size: .8rem; color: #fff; text-shadow: 0 1px 4px rgba(0,0,0,.8); }}
figcaption span {{ color: #fff; background: rgba(17,18,20,.6); padding: 1px 6px; border-radius: 5px; margin-right: 4px; }}
.text {{ padding: 16px 20px 20px; display: grid; gap: 4px; }}
.text h2 {{ margin: 0 0 6px; font-size: 1.35rem; font-weight: 700; letter-spacing: -0.01em; }}
.when b {{ color: var(--ink); font-weight: 500; }}
.k {{ margin: 8px 0 0; }}
.say {{ margin: 0; font-weight: 600; }}
.screen {{ margin: 0; color: #3c3e42; }}
.cv {{ font-family: var(--mono); font-size: .7rem; letter-spacing: .1em; text-transform: uppercase; color: #fff; background: var(--nomem); padding: 1px 6px; border-radius: 4px; }}
footer {{ color: var(--muted); font-size: .85rem; }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <p class="eyebrow">Personal Cooking Coach · demo video v4 · storyboard</p>
  <h1>Every beat, at its <i>key moments</i></h1>
  <p class="lede">{len(shots)} beats, {mmss(total)} in all. Stills come from the rendered beat videos (out/beats), at the moments the page generator marks. Under each beat: where it starts in the film, its length, what the narrator says and what beats.json asks to see.</p>
</header>
<div class="grid">
{chr(10).join(cards)}
</div>
<footer>Footage: HD-EPIC, University of Bristol · CC BY-NC 4.0. Built with Meta V-JEPA 2 · Muse Glimmer · Liquid AI d1.</footer>
</div>
</body>
</html>
"""


def main():
    shots = stills()
    (OUT / "fonts").mkdir(parents=True, exist_ok=True)
    for f in FONTS.iterdir():
        shutil.copy2(f, OUT / "fonts" / f.name)
    (OUT / "index.html").write_text(page(shots), encoding="utf-8")
    print(f"wrote {OUT / 'index.html'} with {sum(len(v) for v in shots.values())} stills")


if __name__ == "__main__":
    main()
