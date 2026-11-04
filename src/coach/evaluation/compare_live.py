"""Can a live LLM coach from the recipe and the video alone? (stage 41)

    python3 -m coach.evaluation.compare_live --list-models
    python3 -m coach.evaluation.compare_live --label smoke --seconds 180 --probe 60 "What do you see right now?"
    python3 -m coach.evaluation.compare_live --label A_1
    python3 -m coach.evaluation.compare_live --label nudge_1 --nudge-every 30   # only if A never speaks

The model gets the recipe, in our coach's own opening words, and the head-camera frames at the API's limit of one a
second, in real time. It gets nothing else: no questions, no world model, no memory, no d1. So what it says, or doesn't
say, is what a general live service does with the same footage; a nudge or a probe is an extra input, off by default
and recorded in the results.

Writes results/gemini_live_<video>_<label>.json after every reply, and each reply's audio next to it. Replies are timed
on the film clock (the last frame sent), so a reconnection doesn't shift them. The key comes from GEMINI_API_KEY or
.env and is never printed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

from ..config import DATA_PROCESSED, DATA_RAW, ROOT, RESULTS

VIDEO, RECIPE = "P08-20240614-085000", "P08_R03"
MODEL = "gemini-3.8-live"
FRAME_SIZE = 768              # the docs' best resolution at 1 frame a second
# Audio with video stops at 2 minutes unless compression is on. Set high: compression may drop old frames, and then
# "it forgot" would be our setting, not the service. COMPRESSION_DROP spots it happening in the token counts.
TRIGGER_TOKENS, TARGET_TOKENS = 120_000, 60_000
COMPRESSION_DROP = 0.9
MAX_RECONNECTS = 8


def system_prompt(name: str, texts: list[str], quiet_line: bool = False) -> str:
    """Our coach's opening and recipe block (coaching.prompts.coach_prompt), and the order line stage 40 tells it.

    quiet_line: "Stay quiet otherwise", as runs A_1 and A_2 had it. It may be why they said nothing, so it is off."""
    recipe = "\n".join(f"{k + 1}. {s}" for k, s in enumerate(texts))
    return f"""You are a cooking coach watching a home cook through a head-mounted camera. The video is live.

Recipe: {name}
{recipe}

The cook may do the steps in any order; the recipe order is only a guide. The cook can't ask you anything, so speak up on your own whenever the cook needs guidance, in English, in one or two short sentences.{" Stay quiet otherwise." if quiet_line else ""}"""


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        m = re.search(r"^GEMINI_API_KEY=[\"']?([^\"'\s]+)", env.read_text(), re.M)
        key = m.group(1) if m else None
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set: add it to .env")
    return key


def extract_frames(video: Path, out: Path, seconds: float | None = None, size: int = FRAME_SIZE) -> list[Path]:
    """One JPEG per second of the video: frame k shows second k. Kept in data/processed so every run sends the same."""
    out.mkdir(parents=True, exist_ok=True)
    frames = sorted(out.glob("*.jpg"))
    if not frames:
        subprocess.run(["ffmpeg", "-v", "error", "-threads", "4", "-i", str(video), "-vf", f"fps=1,scale={size}:{size}", "-q:v", "4",
                        str(out / "%05d.jpg")], check=True)
        frames = sorted(out.glob("*.jpg"))
    return frames[: int(seconds)] if seconds else frames


class Recorder:
    """Turns the server's messages into replies on the film clock, and saves after each one."""

    def __init__(self, path: Path, settings: dict):
        self.path, self.dir = path, path.with_suffix("")
        self.data = {"settings": settings, "replies": [], "inputs": [], "connections": [], "usage": [], "frames_sent": 0}
        self.current: dict | None = None
        self.audio, self.rate = bytearray(), 24000
        self.dir.mkdir(parents=True, exist_ok=True)

    def on_message(self, msg, t: float) -> str | None:
        """Returns a new resumption handle if the message carries one."""
        sc = getattr(msg, "server_content", None)
        if sc is not None:
            text = getattr(getattr(sc, "output_transcription", None), "text", None)
            turn = getattr(sc, "model_turn", None)
            for part in getattr(turn, "parts", None) or []:
                blob = getattr(part, "inline_data", None)
                if blob is not None and blob.data:
                    self._reply(t)
                    self.audio.extend(blob.data)
                    m = re.search(r"rate=(\d+)", blob.mime_type or "")
                    self.rate = int(m.group(1)) if m else self.rate
            if text:
                self._reply(t)["text"] += text
            if getattr(sc, "turn_complete", None) or getattr(sc, "interrupted", None):
                self.close_reply(t, "interrupted" if getattr(sc, "interrupted", None) else "complete")
        usage = getattr(msg, "usage_metadata", None)
        if usage is not None and getattr(usage, "total_token_count", None):
            self.data["usage"].append([t, usage.total_token_count, getattr(usage, "prompt_token_count", None),
                                       getattr(usage, "response_token_count", None)])
        update = getattr(msg, "session_resumption_update", None)
        if update is not None and getattr(update, "resumable", None) and update.new_handle:
            return update.new_handle
        return None

    def _reply(self, t: float) -> dict:
        if self.current is None:
            self.current = {"t": t, "end": t, "text": "", "ended": None, "audio": None}
        return self.current

    def close_reply(self, t: float, how: str) -> None:
        if self.current is None:
            return
        r, self.current = self.current, None
        r.update(end=t, ended=how, text=r["text"].strip())
        if self.audio:
            name = f"reply_{len(self.data['replies']):03d}.wav"
            with wave.open(str(self.dir / name), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(self.rate)
                w.writeframes(bytes(self.audio))
            r["audio"], self.audio = name, bytearray()
        self.data["replies"].append(r)
        print(f"{int(r['t']) // 60:02d}:{int(r['t']) % 60:02d} {r['text']}", flush=True)
        self.save()

    def save(self) -> None:
        self.data["compressions"] = compressions(self.data["usage"])
        self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding="utf-8")


def compressions(usage: list[list]) -> list[float]:
    """Film times where the prompt shrank: older context was dropped, so a later lapse can't count against the model."""
    rows = [(u[0], u[2]) for u in usage if u[2]]
    return [t for (_, a), (t, b) in zip(rows, rows[1:]) if b < COMPRESSION_DROP * a]


@dataclass
class Clock:
    """Film time is the last frame sent, so it stands still while reconnecting."""
    start: float = 0.0
    step: float = 1.0                               # film seconds between frames
    sent: int = 0
    handle: str | None = None
    scheduled: list = field(default_factory=list)   # [(film t, text)], extra inputs, sorted

    @property
    def t(self) -> float:
        return self.start + max(self.sent - 1, 0) * self.step


async def _send(session, frames: list[bytes], clock: Clock, rec: Recorder, pace: float) -> None:
    base = time.monotonic() - clock.sent * pace
    while clock.sent < len(frames):
        await asyncio.sleep(max(0.0, base + clock.sent * pace - time.monotonic()))
        await session.send_realtime_input(video={"data": frames[clock.sent], "mime_type": "image/jpeg"})
        clock.sent += 1
        rec.data["frames_sent"] = clock.sent
        while clock.scheduled and clock.scheduled[0][0] <= clock.t:
            _, text = clock.scheduled.pop(0)
            await session.send_realtime_input(text=text)
            rec.data["inputs"].append({"t": clock.t, "text": text})


async def _receive(session, clock: Clock, rec: Recorder) -> str:
    """Ends with the reason the connection is over. The SDK's receive() stops at each turn's end, hence the outer loop."""
    while True:
        got = False
        async for msg in session.receive():
            got = True
            handle = rec.on_message(msg, clock.t)
            clock.handle = handle or clock.handle
            if getattr(msg, "go_away", None) is not None:
                return "go_away"
        if not got:
            return "closed"


async def stream(connect, frames: list[bytes], rec: Recorder, start: float = 0.0, pace: float = 1.0, step: float = 1.0,
                 drain: float = 20.0, extra: list | None = None, backoff: float = 3.0, redact=str) -> None:
    """Send every frame in real time, reconnecting with the resumption handle when the server ends a connection.

    connect(handle) is an async context manager giving a session. After the last frame, wait `drain` s for a last reply.
    """
    clock = Clock(start=start, step=step, scheduled=sorted(extra or [], key=lambda x: x[0]))
    tries = 0
    while tries <= MAX_RECONNECTS:
        rec.data["connections"].append({"t": clock.t, "resumed": clock.handle is not None})
        why = None
        try:
            async with connect(clock.handle) as session:
                send = asyncio.create_task(_send(session, frames, clock, rec, pace))
                recv = asyncio.create_task(_receive(session, clock, rec))
                await asyncio.wait({send, recv}, return_when=asyncio.FIRST_COMPLETED)
                if send.done() and not send.exception():
                    await asyncio.wait({recv}, timeout=drain)
                    why = "finished"
                else:
                    why = recv.result() if recv.done() and not recv.exception() else repr(send.exception() if send.done() else recv.exception())
                for task in (send, recv):
                    task.cancel()
                await asyncio.gather(send, recv, return_exceptions=True)
        except Exception as e:      # a dropped socket can surface here too; the reason is recorded, the key removed
            why = repr(e)
        rec.close_reply(clock.t, why or "closed")
        rec.data["connections"][-1]["ended"] = redact(why or "closed")
        rec.save()
        if why == "finished":
            return
        tries += 1
        await asyncio.sleep(backoff * (why != "go_away"))
    rec.data["gave_up_at"] = clock.t
    rec.save()


def live_config(system: str, handle: str | None, proactive: bool = True, resolution: str | None = None):
    from google.genai import types
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system,
        output_audio_transcription=types.AudioTranscriptionConfig(),
        context_window_compression=types.ContextWindowCompressionConfig(
            trigger_tokens=TRIGGER_TOKENS, sliding_window=types.SlidingWindow(target_tokens=TARGET_TOKENS)),
        session_resumption=types.SessionResumptionConfig(handle=handle),
        proactivity=types.ProactivityConfig(proactive_audio=True) if proactive else None,
        media_resolution=f"MEDIA_RESOLUTION_{resolution.upper()}" if resolution else None,
    )


def client(key: str, api_version: str):
    from google import genai
    return genai.Client(api_key=key, http_options={"api_version": api_version})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="smoke")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--api-version", default="v1beta")
    ap.add_argument("--seconds", type=float, help="only the first N seconds of the video")
    ap.add_argument("--nudge-every", type=float, help="extra input: 'continue coaching' every N s of film")
    ap.add_argument("--probe", nargs=2, action="append", metavar=("T", "TEXT"), help="extra input, smoke test only: ask TEXT at film time T")
    ap.add_argument("--no-proactive", action="store_true", help="models that have it always on may refuse the setting")
    ap.add_argument("--tier", default="free", help="recorded in the results: on the free tier Google may use the content")
    ap.add_argument("--every", type=int, default=1, help="send one frame every N s: at 192 tokens a frame, the whole "
                                                         "film only stays in the 128k context at N=2 or more")
    ap.add_argument("--resolution", choices=["low", "medium", "high"], help="the API's media_resolution; default: unset")
    ap.add_argument("--final", help="asked right after the last frame, so it can't change what was said during the film; "
                                    "also the only way to read the token count from a silent run")
    ap.add_argument("--quiet-line", action="store_true", help="add 'Stay quiet otherwise', as runs A_1 and A_2 did")
    ap.add_argument("--list-models", action="store_true")
    args = ap.parse_args()

    key = load_key()
    redact = lambda s: str(s).replace(key, "***")
    if args.list_models:
        api = client(key, args.api_version)      # held: the SDK closes its connection when the client is collected
        names = [m.name for m in api.models.list()]
        print("\n".join(n for n in names if "live" in n or "native-audio" in n))
        return

    run = json.loads((RESULTS / f"coach_timeline_{VIDEO}.json").read_text())       # the steps our coach was given
    name = json.loads((DATA_RAW / "hd-epic" / "complete_recipes.json").read_text())[RECIPE]["name"]
    system = system_prompt(name, run["steps"], args.quiet_line)
    paths = extract_frames(DATA_RAW / "hd-epic" / f"{VIDEO}.mp4", DATA_PROCESSED / "live_frames" / VIDEO, args.seconds)
    frames = [p.read_bytes() for p in paths[:: args.every]]
    film = len(frames) * args.every
    extra = [(float(t), text) for t, text in args.probe or []]
    if args.nudge_every:
        extra += [(t, "continue coaching") for t in range(int(args.nudge_every), film, int(args.nudge_every))]

    if args.final:
        extra.append(((len(frames) - 1) * args.every, args.final))

    settings = {"model": args.model, "resolution": args.resolution, "final": args.final, "api_version": args.api_version, "video": VIDEO, "recipe": RECIPE, "system": system,
                "frames": len(frames), "frame_size": FRAME_SIZE, "every_s": args.every, "trigger_tokens": TRIGGER_TOKENS,
                "target_tokens": TARGET_TOKENS, "proactive_audio": not args.no_proactive, "tier": args.tier,
                "nudge_every": args.nudge_every, "probe": args.probe, "started": time.strftime("%Y-%m-%d %H:%M:%S %z")}
    rec = Recorder(RESULTS / f"gemini_live_{VIDEO}_{args.label}.json", settings)
    print(f"{args.model}: {len(frames)} frames, {name}", flush=True)
    api = client(key, args.api_version)          # held: the SDK closes its connection when the client is collected
    connect = lambda handle: api.aio.live.connect(model=args.model, config=live_config(system, handle, not args.no_proactive, args.resolution))
    asyncio.run(stream(connect, frames, rec, pace=args.every, step=args.every, extra=extra, redact=redact))
    d = rec.data
    print(f"frames sent {d['frames_sent']}/{len(frames)}, replies {len(d['replies'])}, connections {len(d['connections'])}, "
          f"compressions {d['compressions']}, last usage {d['usage'][-1] if d['usage'] else None}", flush=True)
    for c in d["connections"]:
        print(" connection", c, flush=True)


if __name__ == "__main__":
    main()
