"""Cut the footage each beat needs, as listed in video/media/hd/manifest.json (written by build.py).

    python3 video/pipeline/cut_clips.py          # cuts what is missing or changed
    python3 video/pipeline/cut_clips.py --force  # cuts everything again

Full-bleed: crop x 0-1408, y 520-1312 (exactly 16:9), scale to 1920x1080.
Picture-in-picture: a 1000x1000 crop from x 204, y 408, at 680x680 (twice its 340 px size on screen).
H.264, short GOP for fast seeking, no audio, ffmpeg -threads 3.
"""
import json
import subprocess
import sys
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
ROOT = VIDEO.parent
HD = VIDEO / "media" / "hd"
RAW = ROOT / "data" / "raw" / "hd-epic"
CROP = {"full": "crop=1408:792:0:520,scale=1920:1080:flags=lanczos",
        "pip": "crop=1000:1000:204:408,scale=680:680:flags=lanczos"}


def cut(m, force=False):
    out = HD / m["file"]
    stamp = out.with_suffix(".json")
    if not force and out.exists() and stamp.exists() and json.loads(stamp.read_text()) == m:
        return False
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{m['start']:.3f}", "-i", str(RAW / f"{m['video']}.mp4"),
           "-t", f"{m['duration']:.3f}", "-vf", CROP[m["kind"]] + ",fps=30,format=yuv420p", "-an",
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
