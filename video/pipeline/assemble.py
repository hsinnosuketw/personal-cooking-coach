"""Join the rendered beats into the film: demo_v1.mp4 (+ narration at -16 LUFS), demo_v1.srt and a contact sheet.

    python3 video/pipeline/assemble.py           # system python3 (needs Pillow, which the .venv lacks)
    python3 video/pipeline/assemble.py --sheet   # only the contact sheet, from the existing demo_v1.mp4

Needs video/out/beats/beat_XX.mp4 (render_beats.py) and video/audio/narration.wav + timings.json (tts.py).
The video is re-encoded once (libx264, CRF 18); the narration is normalised with two-pass loudnorm
(-16 LUFS integrated, -1.5 dBTP) and muxed as AAC 192k at 48 kHz.
"""
import json
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

VIDEO = Path(__file__).resolve().parents[1]
OUT = VIDEO / "out"
BEATS = OUT / "beats"
AUDIO = VIDEO / "audio"
FILM = OUT / "demo_v1.mp4"
THREADS = "3"
# The renders are BT.709 limited range; a JPEG is BT.601 full range. Without this the greens come out light.
JPEG_VF = "scale={w}:{h}:in_color_matrix=bt709:in_range=tv:out_color_matrix=bt601:out_range=pc,format=yuvj420p"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def ts(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(timings):
    """One subtitle per sentence, on the film clock. Coach lines are marked 'Coach:' as in beats.json."""
    cues = []
    for bid in sorted(timings["beats"], key=int):
        b = timings["beats"][bid]
        for s in b["sentences"]:
            text = ("Coach: " if s["voice"] == "coach" else "") + s["text"]
            cues.append([b["start"] + s["start"], b["start"] + s["end"], text])
    for i, c in enumerate(cues):   # hold each a little after the voice stops, never into the next one
        nxt = cues[i + 1][0] if i + 1 < len(cues) else timings["total"]
        c[1] = min(c[1] + 0.3, nxt - 0.05)
    lines = []
    for i, (a, b, text) in enumerate(cues, 1):
        lines += [str(i), f"{ts(a)} --> {ts(b)}", "\n".join(textwrap.wrap(text, 42)), ""]
    (OUT / "demo_v1.srt").write_text("\n".join(lines), encoding="utf-8")
    return len(cues)


def loudnorm_args():
    """First loudnorm pass: measure the narration, so the second pass can be linear."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(AUDIO / "narration.wav"), "-af",
                        "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    return (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")


def concat_and_mux(ids):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, dir=OUT) as f:
        for bid in ids:
            f.write(f"file '{(BEATS / f'beat_{bid:02d}.mp4').as_posix()}'\n")
        lst = f.name
    try:
        af = loudnorm_args() + ",aresample=48000"
        run(["ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", str(AUDIO / "narration.wav"),
             "-map", "0:v:0", "-map", "1:a:0", "-af", af,
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-threads", THREADS, str(FILM)])
    finally:
        Path(lst).unlink(missing_ok=True)


def contact_sheet(total, every=4.0, cols=6, w=320):
    """One frame every 4 s, labelled with its film time."""
    h = w * 9 // 16
    with tempfile.TemporaryDirectory(dir=OUT) as tmp:
        step = round(every * 30)   # exact frames 0, 120, 240...: tile i is film time i * every
        run(["ffmpeg", "-hide_banner", "-y", "-i", str(FILM), "-vf", f"select='not(mod(n,{step}))'," + JPEG_VF.format(w=w, h=h),
             "-fps_mode", "vfr", "-color_range", "pc", "-q:v", "3", "-threads", THREADS, f"{tmp}/f_%03d.jpg"])
        frames = sorted(Path(tmp).glob("f_*.jpg"))
        rows = -(-len(frames) // cols)
        pad, lab = 8, 26
        sheet = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + lab + pad) + pad), (17, 18, 20))
        draw = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 15)
        except OSError:
            font = ImageFont.load_default()
        for i, fp in enumerate(frames):
            x, y = pad + (i % cols) * (w + pad), pad + (i // cols) * (h + lab + pad)
            sheet.paste(Image.open(fp), (x, y + lab))
            t = i * every
            draw.text((x + 2, y + 4), f"{int(t // 60)}:{t % 60:04.1f}", fill=(220, 224, 220), font=font)
        sheet.save(OUT / "demo_v1_sheet.jpg", quality=88)
        return len(frames)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,duration,nb_frames,sample_rate",
             "-of", "json", str(path)])
    return json.loads(r.stdout)["streams"]


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1]
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)[-1]
    return float(i), float(tp)


def main():
    timings = json.loads((AUDIO / "timings.json").read_text())
    if "--sheet" in sys.argv:   # only the contact sheet, from the existing demo_v1.mp4
        print(f"sheet of {contact_sheet(timings['total'])} frames")
        return
    ids = sorted(int(k) for k in timings["beats"])
    missing = [i for i in ids if not (BEATS / f"beat_{i:02d}.mp4").exists()]
    assert not missing, f"render these beats first: {missing}"
    concat_and_mux(ids)
    n = write_srt(timings)
    k = contact_sheet(timings["total"])
    for s in probe(FILM):
        print(" ", {k_: s.get(k_) for k_ in ("codec_type", "codec_name", "width", "height", "r_frame_rate", "sample_rate", "duration", "nb_frames")})
    i, tp = loudness(FILM)
    print(f"wrote {FILM.name} (timeline {timings['total']:.3f}s), {n} subtitles, sheet of {k} frames; loudness {i} LUFS, true peak {tp} dBFS")


if __name__ == "__main__":
    main()
