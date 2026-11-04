"""The effects track and the music bed, on the film clock: video/audio/sfx.wav and video/audio/music_bed.wav.

    python3 video/pipeline/sound.py        # after build.py (hyperframes/cues.json) and tts.py (audio/timings.json)

Effects are synthesised here (no sample files): a pop when a card lands, a tick when a step icon fills or the counter
steps, a two-note chime when one of d1's moves is actually done, a whoosh for chapter cards and the coach reply's lift.
The music is "Bushwick Tarantella" by Kevin MacLeod (incompetech.com), CC BY 4.0, credited on the end card; the mp3
lives in video/media/music/ (gitignored), from https://incompetech.com/music/royalty-free/mp3-royaltyfree/Bushwick%20Tarantella.mp3.
Its level follows the story (MUSIC_DB per beat); assemble.py ducks it under the narration.
"""
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

VIDEO = Path(__file__).resolve().parents[1]
AUDIO = VIDEO / "audio"
MUSIC = VIDEO / "media" / "music" / "Bushwick Tarantella.mp3"
SR = 48000
# Music level per beat, in dB, before ducking. None = silent. It starts with the cooking, dips under the three
# problems, stops for the turn, comes back with memory, sits lower under the explanation and swells at the close.
# Measured before ducking: -27 LUFS at the hook, -23 with memory, -34 under the problems; the narration is -16.
MUSIC_DB = {0: -9, 1: -19, 2: -19, 3: -19, 4: -19, 5: None, 6: -10, 7: -10, 8: -11, 9: -10, 10: -16, 11: -16, 12: -16, 13: -9}
RAMP = 0.6            # crossfade between beat levels, seconds
FADE_OUT = 2.5        # at the end of the film
SFX_DB = {"pop": -15, "tick": -21, "check": -19, "whoosh": -22}


def env(n, attack, decay):
    t = np.arange(n) / SR
    return (1 - np.exp(-t / attack)) * np.exp(-t / decay)


def pop():
    t = np.arange(int(0.12 * SR)) / SR
    f = 520 + 650 * np.exp(-t / 0.012)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * env(len(t), 0.002, 0.035)


def tick():
    t = np.arange(int(0.06 * SR)) / SR
    return (np.sin(2 * np.pi * 2400 * t) + 0.5 * np.sin(2 * np.pi * 3600 * t)) * env(len(t), 0.0005, 0.008)


def check():
    n = int(0.45 * SR)
    out = np.zeros(n)
    for f, at in ((1046.5, 0.0), (1568.0, 0.075)):
        k = int(at * SR)
        t = np.arange(n - k) / SR
        out[k:] += np.sin(2 * np.pi * f * t) * env(n - k, 0.003, 0.09)
    return out


def whoosh(length=0.42, seed=7):
    n = int(length * SR)
    noise = np.random.default_rng(seed).standard_normal(n)
    shape = np.sin(np.pi * np.arange(n) / n) ** 2
    cut = 400 + 3600 * shape                       # a one-pole low-pass that opens and closes with the swell
    a = np.exp(-2 * np.pi * cut / SR)
    y, prev = np.zeros(n), 0.0
    for i in range(n):
        prev = (1 - a[i]) * noise[i] + a[i] * prev
        y[i] = prev
    return y * shape


SOUNDS = {"pop": pop(), "tick": tick(), "check": check(), "whoosh": whoosh()}


def norm(x, db):
    return x / np.max(np.abs(x)) * 10 ** (db / 20)


def write(path, stereo):
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def effects(timings, cues, n):
    out = np.zeros(n)
    count = 0
    for bid, items in cues.items():
        start = timings["beats"][bid]["start"]
        for t, kind in items:
            snd = norm(SOUNDS[kind], SFX_DB[kind])
            i = int(round((start + t) * SR))
            j = min(n, i + len(snd))
            if i < n:
                out[i:j] += snd[: j - i]
                count += 1
    return np.stack([out, out], axis=1), count


def music(timings, n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(MUSIC), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    track = np.frombuffer(raw, "<f4").reshape(-1, 2)[:n]
    assert len(track) >= n, "the music is shorter than the film"
    gain = np.zeros(n)
    for bid, b in timings["beats"].items():
        db = MUSIC_DB[int(bid)]
        i, j = int(b["start"] * SR), min(n, int((b["start"] + b["duration"]) * SR))
        gain[i:j] = 0.0 if db is None else 10 ** (db / 20)
    k = int(RAMP * SR)                              # smooth every step with a moving average one ramp long
    c = np.cumsum(np.pad(gain, (k // 2, k - k // 2), mode="edge"))
    gain = (c[k:] - c[:-k]) / k
    f = int(FADE_OUT * SR)
    gain[-f:] *= np.linspace(1, 0, f)
    return track * gain[:, None]


def main():
    timings = json.loads((AUDIO / "timings.json").read_text())
    cues = json.loads((VIDEO / "hyperframes" / "cues.json").read_text())
    n = int(round(timings["total"] * SR))
    sfx, count = effects(timings, cues, n)
    write(AUDIO / "sfx.wav", sfx)
    write(AUDIO / "music_bed.wav", music(timings, n))
    print(f"wrote sfx.wav ({count} effects) and music_bed.wav, {timings['total']:.2f} s")


if __name__ == "__main__":
    main()
