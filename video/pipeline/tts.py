"""Narration for the demo video: one WAV per beat, timings.json and narration.wav.

    video/.venv/bin/python video/pipeline/tts.py            # all beats
    video/.venv/bin/python video/pipeline/tts.py 3 7        # only beats 3 and 7 (timings are rebuilt from every beat's WAV)

Reads video/beats.json. Each beat's `say` is split into sentences; text after "Coach:" is spoken by the
coach voice. Each sentence is synthesised on its own with Kokoro-82M, trimmed, and joined with 0.3 s gaps.
Writes video/audio/beat_XX.wav (speech only), video/audio/beat_XX.json (sentences and word times),
video/audio/timings.json (the film timeline) and video/audio/narration.wav (the whole track).
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

VIDEO = Path(__file__).resolve().parents[1]
import version as V  # noqa: E402  (video/pipeline/version.py)
AUDIO = V.AUDIO
AUDIO.mkdir(exist_ok=True)
SR = 24000
FPS = 30
GAP = 0.30          # between sentences
LEAD = 0.20         # silence at the head of each beat, before the first word
TAIL = 0.50         # silence after the last word of each beat
MIN_BEAT = 2.5
# Extra hold after the speech, for pictures that need it (seconds, on top of TAIL).
EXTRA_TAIL = {
    6: 1.2,    # M2: the world model's "peel onion" tick held 2 s
    8: 1.0,    # E2: on to the moment the memory marks step 1 (5:16.2), after the freezes on the three ticks
    9: 5.1,    # B3: the salt (9:20) until d1's "take salt" and "sprinkle salt" are done (9:24.4, 9:24.7)
    13: 4.0,   # the end card with the project name and the credits
}
# Extra silence after a sentence: {beat: {sentence index: seconds}}, so a picture can hold before the next line.
PAUSE_AFTER = {
    6: {1: 0.9},           # the coach's "fine to do in parallel" stays lifted and marked for about 2 s
    8: {1: 0.9, 3: 0.2},   # the 4:53 reply held 2.5 s; "Open the carton. Take an egg. Crack it." spaced to the ticks
}
if V.VERSION == "v5":
    EXTRA_TAIL[9] = 3.9    # B3's salt until d1's ticks (9:24.4)
    EXTRA_TAIL[12] = 0.5   # the table holds
    PAUSE_AFTER[1] = {0: 3.0}   # the recipe list stays 3 s after its sentence, to be read
VOICES = {
    "narrator": dict(voice="af_heart", speed=0.85),
    "coach": dict(voice="am_michael", speed=0.8),
}
# What the TTS reads, where the written form would be mispronounced. The SRT keeps the written form.
SPOKEN = [
    ("V-JEPA 2", "Vee-Jeppa two"),
    ("Liquid AI's d1", "Liquid A.I.'s D one"),
]


def sentences(say):
    """[(voice, text)] in order; 'Coach:' switches to the coach voice for the rest of the line."""
    parts = say.split("Coach:")
    out = []
    for i, part in enumerate(parts):
        voice = "narrator" if i == 0 else "coach"
        for s in re.split(r"(?<=[.?!])\s+", part.strip()):
            if s:
                out.append((voice, s))
    return out


def spoken(text):
    for a, b in SPOKEN:
        text = text.replace(a, b)
    return text


def trim(audio, words):
    """Cut leading and trailing silence (kept: 40 ms), shifting the word times to match."""
    level = np.abs(audio)
    thr = max(level.max() * 0.02, 1e-4)
    loud = np.nonzero(level > thr)[0]
    a = max(int(loud[0]) - int(0.04 * SR), 0)
    b = min(int(loud[-1]) + int(0.04 * SR), len(audio))
    off = a / SR
    words = [dict(w, start=round(max(w["start"] - off, 0), 3), end=round(min(w["end"] - off, (b - a) / SR), 3)) for w in words]
    return audio[a:b], words


def synth(pipe, voice, text):
    v = VOICES[voice]
    chunks, words, t0 = [], [], 0.0
    for r in pipe(spoken(text), voice=v["voice"], speed=v["speed"]):
        a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
        for tk in r.tokens or []:
            if tk.start_ts is None or not re.search(r"\w", tk.text):
                continue
            words.append({"w": tk.text, "start": round(t0 + tk.start_ts, 3), "end": round(t0 + tk.end_ts, 3)})
        chunks.append(a)
        t0 += len(a) / SR
    return trim(np.concatenate(chunks).astype(np.float32), words)


def build_beat(pipe, bt):
    parts, sents, t = [], [], 0.0
    for i, (voice, text) in enumerate(sentences(bt["say"])):
        if i:
            gap = GAP + PAUSE_AFTER.get(bt["id"], {}).get(i - 1, 0.0)
            parts.append(np.zeros(int(gap * SR), np.float32))
            t += gap
        a, words = synth(pipe, voice, text)
        d = len(a) / SR
        sents.append({"voice": voice, "text": text, "start": round(t, 3), "end": round(t + d, 3),
                      "words": [dict(w, start=round(t + w["start"], 3), end=round(t + w["end"], 3)) for w in words]})
        parts.append(a)
        t += d
    audio = np.concatenate(parts)
    sf.write(AUDIO / f"beat_{bt['id']:02d}.wav", audio, SR, subtype="PCM_16")
    meta = {"id": bt["id"], "label": bt["label"], "audio_duration": round(len(audio) / SR, 3), "sentences": sents}
    (AUDIO / f"beat_{bt['id']:02d}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(f"beat {bt['id']:2d}  {meta['audio_duration']:6.2f}s  {bt['label']}")


def layout(beats):
    """timings.json and narration.wav, from the per-beat WAVs. Beat starts sit on whole frames."""
    timeline, track, start = {}, [], 0.0
    for bt in beats:
        meta = json.loads((AUDIO / f"beat_{bt['id']:02d}.json").read_text())
        audio, _ = sf.read(AUDIO / f"beat_{bt['id']:02d}.wav", dtype="float32")
        dur = max(LEAD + len(audio) / SR + TAIL + EXTRA_TAIL.get(bt["id"], 0.0), MIN_BEAT)
        dur = math.ceil(round(dur * FPS, 6)) / FPS
        sents = [dict(s, start=round(LEAD + s["start"], 3), end=round(LEAD + s["end"], 3),
                      words=[dict(w, start=round(LEAD + w["start"], 3), end=round(LEAD + w["end"], 3)) for w in s["words"]])
                 for s in meta["sentences"]]
        timeline[str(bt["id"])] = {"label": bt["label"], "start": round(start, 4), "duration": round(dur, 4),
                                   "frames": round(dur * FPS), "estimate": bt["time"], "audio": f"beat_{bt['id']:02d}.wav",
                                   "speech_offset": LEAD, "audio_duration": meta["audio_duration"], "sentences": sents}
        seg = np.zeros(round(dur * SR), np.float32)
        a0 = int(LEAD * SR)
        seg[a0:a0 + len(audio)] = audio[: len(seg) - a0]
        track.append(seg)
        start += dur
    total = round(start, 4)
    (AUDIO / "timings.json").write_text(json.dumps(
        {"fps": FPS, "sample_rate": SR, "total": total, "note": "times in seconds; sentence and word times are relative to the beat start",
         "beats": timeline}, indent=1, ensure_ascii=False))
    sf.write(AUDIO / "narration.wav", np.concatenate(track), SR, subtype="PCM_16")
    print(f"total {total:.2f}s  ({int(total // 60)}:{total % 60:05.2f})")


def main():
    beats = json.loads(V.BEATS_FILE.read_text())["beats"]
    only = {int(a) for a in sys.argv[1:]}
    todo = [b for b in beats if not only or b["id"] in only]
    if todo:
        from kokoro import KPipeline
        pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
        for bt in todo:
            build_beat(pipe, bt)
    layout(beats)


if __name__ == "__main__":
    main()
