"""coach.evaluation.compare_live with a fake live session: no network, no key. Run: python3 tests/test_compare_live.py"""
import asyncio
import contextlib
import json
import sys
import tempfile
import wave
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coach.evaluation import compare_live as cl

FRAMES = [bytes([k]) for k in range(6)]


def say(text, done=True, audio=b"\x01\x00" * 10):
    part = NS(inline_data=NS(data=audio, mime_type="audio/pcm;rate=24000"))
    return NS(server_content=NS(output_transcription=NS(text=text), model_turn=NS(parts=[part]), turn_complete=done, interrupted=None))


class Session:
    """Sends `script[n]` (a list of messages) to the client once n frames have arrived."""

    def __init__(self, script, log):
        self.script, self.log = script, log
        self.q = asyncio.Queue()
        self.frames = 0

    async def send_realtime_input(self, video=None, text=None):
        if text is not None:
            self.log["text"].append(text)
            return
        self.log["frames"].append(video["data"])
        assert video["mime_type"] == "image/jpeg"
        self.frames += 1
        for m in self.script.get(self.frames, []):
            self.q.put_nowait(m)

    async def receive(self):
        yield await self.q.get()


def connector(scripts, log):
    @contextlib.asynccontextmanager
    async def connect(handle):
        log["handles"].append(handle)
        yield Session(scripts[len(log["handles"]) - 1], log)
    return connect


def run(scripts, **kw):
    log = {"frames": [], "text": [], "handles": []}
    tmp = Path(tempfile.mkdtemp())
    rec = cl.Recorder(tmp / "run.json", {"model": "fake"})
    asyncio.run(cl.stream(connector(scripts, log), FRAMES, rec, pace=0.0, drain=0.01, backoff=0.0, **kw))
    return log, rec, json.loads((tmp / "run.json").read_text())


def test_only_the_recipe_goes_in_the_system_prompt():
    p = cl.system_prompt("Eggs", ["Crack the eggs.", "Heat the pan."])
    assert "1. Crack the eggs.\n2. Heat the pan." in p and "Recipe: Eggs" in p
    assert not any(w in p.lower() for w in ("checklist", "expects", "tracker", "done so far"))


def test_the_quiet_line_is_off_unless_asked_for():
    assert "quiet" not in cl.system_prompt("Eggs", ["Crack."]).lower()
    assert cl.system_prompt("Eggs", ["Crack."], quiet_line=True).endswith("Stay quiet otherwise.")


def test_frames_only_by_default_and_replies_on_the_film_clock():
    log, rec, d = run([{3: [say("Crack the eggs.")]}])
    assert log["frames"] == FRAMES and log["text"] == []             # the recipe and the video, nothing else
    r = d["replies"][0]
    assert r["t"] == 2 and r["text"] == "Crack the eggs." and r["ended"] == "complete"     # third frame shows second 2
    with wave.open(str(rec.dir / r["audio"])) as w:
        assert w.getframerate() == 24000 and w.getnframes() == 10


def test_every_other_frame_keeps_film_time():
    _, _, d = run([{3: [say("Crack the eggs.")]}], step=2.0)
    assert d["replies"][0]["t"] == 4                                 # third frame sent, every 2 s: second 4


def test_transcript_pieces_join_into_one_reply():
    _, _, d = run([{2: [say("Crack ", done=False), say("the eggs.")]}])
    assert [r["text"] for r in d["replies"]] == ["Crack the eggs."]


def test_go_away_resumes_with_the_handle_and_loses_no_frame():
    bye = [NS(session_resumption_update=NS(resumable=True, new_handle="h1")), NS(go_away=NS(time_left="5s"))]
    log, _, d = run([{2: bye}, {}])
    assert log["handles"] == [None, "h1"]
    assert sorted(set(log["frames"])) == FRAMES                      # a frame in flight may repeat; none is skipped
    assert [c["resumed"] for c in d["connections"]] == [False, True]


def test_extra_inputs_are_sent_on_time_and_recorded():
    log, _, d = run([{}], extra=[(2.0, "continue coaching")])
    assert log["text"] == ["continue coaching"]
    assert d["inputs"] == [{"t": 2, "text": "continue coaching"}]


def test_compression_is_spotted_in_the_token_counts():
    assert cl.compressions([[1, 0, 100, 0], [2, 0, 120, 0], [3, 0, 60, 0], [4, 0, 80, 0]]) == [3]


def test_a_failed_connection_keeps_trying_and_redacts_the_reason():
    log = {"handles": []}
    @contextlib.asynccontextmanager
    async def connect(handle):
        log["handles"].append(handle)
        raise RuntimeError("bad key SECRET")
        yield
    rec = cl.Recorder(Path(tempfile.mkdtemp()) / "run.json", {})
    asyncio.run(cl.stream(connect, FRAMES, rec, pace=0.0, backoff=0.0, redact=lambda s: str(s).replace("SECRET", "***")))
    assert len(log["handles"]) == cl.MAX_RECONNECTS + 1 and rec.data["gave_up_at"] == 0
    assert "SECRET" not in json.dumps(rec.data)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
