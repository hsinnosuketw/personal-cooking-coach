"""Cut the footage each beat needs, as listed in video/media/hd/manifest.json (written by build.py).

    python3 video/pipeline/cut_clips.py          # cuts what is missing or changed
    python3 video/pipeline/cut_clips.py --force  # cuts everything again

Full-bleed: crop x 0-1408, y 520-1312 (exactly 16:9), scale to 1920x1080.
Picture-in-picture: a 1000x1000 crop from x 204, y 408, at 680x680 (twice its 340 px size on screen).
Panel: the demo page's 1280x776 video of a run (results/coach_*.mp4, 15 fps), its bottom strip cut off, scaled 1.5x.
A cut with "holds" freezes its picture at those points (seconds into the cut) for that long.
H.264, short GOP for fast seeking, no audio, ffmpeg -threads 3.
"""
import json
import subprocess
import sys
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
ROOT = VIDEO.parent
import version as V  # noqa: E402  (video/pipeline/version.py)
HD = V.HD
RAW = ROOT / "data" / "raw" / "hd-epic"
RUNS = ROOT / "results"
CROP = {"full": "crop=1408:792:0:520,scale=1920:1080:flags=lanczos",
        "pip": "crop=1000:1000:204:408,scale=680:680:flags=lanczos",
        "panel": "crop=1280:720:0:0,scale=1920:1080:flags=lanczos"}


def freeze_graph(vf, holds):
    """Filter graph that plays the cut and freezes it at each hold: [[seconds into the cut, seconds frozen], ...]."""
    n = len(holds) + 1
    edges = [0.0] + [a for a, _ in holds] + [None]
    g = f"[0:v]{vf},split={n}" + "".join(f"[s{k}]" for k in range(n)) + ";"
    for k in range(n):
        a, b = edges[k], edges[k + 1]
        trim = f"trim=start={a:.3f}" + (f":end={b:.3f}" if b is not None else "")
        pad = f",tpad=stop_mode=clone:stop_duration={holds[k][1]:.3f}" if k < len(holds) else ""
        g += f"[s{k}]{trim},setpts=PTS-STARTPTS{pad}[p{k}];"
    return g + "".join(f"[p{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0,format=yuv420p[out]"


def cut(m, force=False):
    out = HD / m["file"]
    stamp = out.with_suffix(".json")
    if not force and out.exists() and stamp.exists() and json.loads(stamp.read_text()) == m:
        return False
    src = str((RUNS if m["kind"] == "panel" else RAW) / f"{m['video']}.mp4")
    vf = CROP[m["kind"]] + ",fps=30"
    holds = m.get("holds") or []
    read = m["duration"] - sum(h for _, h in holds)          # source seconds; the freezes make up the rest
    if holds:
        filt = ["-t", f"{read:.3f}", "-i", src, "-filter_complex", freeze_graph(vf, holds), "-map", "[out]"]
    else:
        filt = ["-i", src, "-t", f"{read:.3f}", "-vf", vf + ",format=yuv420p"]
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{m['start']:.3f}", *filt, "-an",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-g", "15", "-movflags", "+faststart", "-threads", "3", str(out)]
    subprocess.run(cmd, check=True)
    stamp.write_text(json.dumps(m))
    return True


def main():
    force = "--force" in sys.argv
    manifest = json.loads((HD / "manifest.json").read_text())
    for m in manifest:
        done = cut(m, force)
        print(f"{'cut ' if done else 'have'} {m['file']:<16} {m['video']} {m['start']:8.2f}s +{m['duration']:.2f}s {m['kind']}")


if __name__ == "__main__":
    main()
