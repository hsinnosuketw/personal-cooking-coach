"""Render beat pages to MP4 with HyperFrames, one at a time, and check each against its frame count in timings.json.

    python3 video/pipeline/render_beats.py              # every beat
    python3 video/pipeline/render_beats.py 3 7          # beats 3 and 7
    python3 video/pipeline/render_beats.py --workers 3  # fewer Chrome workers (default 4)

Writes video/out/beats/beat_XX.mp4 (1920x1080, 30 fps, no audio). Waits while the 1-minute load average is above
MAX_LOAD and less than MIN_IDLE percent of the CPU is idle, before starting each beat.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
HF = VIDEO / "hyperframes"
OUT = VIDEO / "out" / "beats"
HF_CLI = "hyperframes@0.9.8"
MAX_LOAD = float(os.environ.get("MAX_LOAD", "7"))
MIN_IDLE = float(os.environ.get("MIN_IDLE", "45"))   # macOS load counts I/O-blocked threads, so idle CPU also lets a render start


def cpu_idle():
    """Percent of CPU idle over a 2 s sample (macOS top)."""
    r = subprocess.run(["top", "-l", "2", "-n", "0", "-s", "2"], capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.startswith("CPU usage")]
    return float(lines[-1].split(",")[-1].strip().split("%")[0]) if lines else 0.0


def frames(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_packets,width,height,r_frame_rate", "-of", "json", str(path)], capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    return int(s["nb_read_packets"]), s["width"], s["height"], s["r_frame_rate"]


def render(bid, workers):
    out = OUT / f"beat_{bid:02d}.mp4"
    tmp = OUT / f".beat_{bid:02d}.tmp.mp4"
    cmd = ["npx", "-y", HF_CLI, "render", "-c", f"compositions/beat_{bid:02d}.html", "-o", str(tmp),
           "-w", str(workers), "-f", "30", "-q", "looks", "--quiet"]
    env = dict(os.environ, DO_NOT_TRACK="1", HYPERFRAMES_SKIP_SKILLS="1")
    t0 = time.time()
    r = subprocess.run(cmd, cwd=HF, env=env, capture_output=True, text=True)
    if r.returncode or not tmp.exists():
        print(f"beat {bid:2d}  FAILED ({r.returncode})\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}", flush=True)
        return False
    return tmp, out, time.time() - t0


def main():
    args = sys.argv[1:]
    workers = 4
    if "--workers" in args:
        i = args.index("--workers")
        workers = int(args[i + 1])
        del args[i:i + 2]
    timings = json.loads((VIDEO / "audio" / "timings.json").read_text())["beats"]
    ids = [int(a) for a in args] or sorted(int(k) for k in timings)
    OUT.mkdir(parents=True, exist_ok=True)
    ok = True
    for bid in ids:
        while os.getloadavg()[0] > MAX_LOAD and cpu_idle() < MIN_IDLE:
            print(f"load {os.getloadavg()[0]:.1f} > {MAX_LOAD} and CPU idle < {MIN_IDLE:.0f}%, waiting", flush=True)
            time.sleep(20)
        res = render(bid, workers)
        if not res:
            ok = False
            continue
        tmp, out, secs = res
        n, w, h, fps = frames(tmp)
        want = timings[str(bid)]["frames"]
        good = n == want and (w, h) == (1920, 1080) and fps == "30/1"
        if good:
            tmp.replace(out)
        else:
            ok = False
        print(f"beat {bid:2d}  {'ok ' if good else 'BAD'}  {n}/{want} frames  {w}x{h} {fps}  {secs:5.1f}s  load {os.getloadavg()[0]:.1f}", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
