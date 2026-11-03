"""Frame checks (stage 38): ask a small vision model whether a step has begun, when the camera rule is unsure.

A check is triggered by the evidence, not by a clock:
- start: the camera rule would mark a step started (it is held as "maybe" until the check answers);
- early_end: a step's evidence stopped within early_end_s of starting;
- restart: a finished step's evidence is back;
- silent: no new step for silent_s while some steps show no sign (which listed step, if any, do the frames show?).
At most one check every every_s; a step found "not started" waits again_s before it is checked again.
"""
from __future__ import annotations

import base64
import io
import json
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from ..coaching.reminders import mmss


@dataclass(frozen=True)
class LookSettings:
    frames: int = 4           # one 2x2 contact sheet ...
    span_s: float = 20        # ... of the last 20 s
    px: int = 336
    every_s: float = 15
    again_s: float = 60
    early_end_s: float = 20
    silent_s: float = 120


WHY = {"start": "An action model thinks this step may have just begun",
       "early_end": "An action model saw this step start and then stop soon after",
       "restart": "This step was finished, and an action model sees it again",
       "coach": "The cooking coach is unsure whether the cook has begun this step"}


def check_prompt(kind: str, k: int | None, t: float, evidence: str, open_steps: list[int], name: str, texts: list[str],
                 span_s: float, version: int = 2) -> str:
    """version 2: STATUS line (the default); 4: a yes/no question. (1: preparing didn't count; 3: one example answer,
    which anchored the 11B on "in progress".)"""
    head = (f"Four frames from a head-mounted camera in a home kitchen, from {mmss(t - span_s)} to {mmss(t)} "
            f"(left to right, top to bottom). The cook is making {name}.\n")
    if kind == "silent":
        listed = "\n".join(f"{j + 1}. {texts[j][:90]}" for j in open_steps)
        return head + f"""These recipe steps have not been seen yet:
{listed}
Is the cook doing one of them in these frames? Answer with one line: STEP: <number, or none>, then one short sentence on what the frames show."""
    return head + f"""Step {k + 1}: {texts[k]}
{WHY[kind]} ({evidence}). Preparing this step's own ingredients or tools (getting them out, chopping, cracking, measuring) counts as
in progress: the step has begun. Fetching or tidying things that belong to a different step does not.
""" + ("""Which is true now? Answer with one line: STATUS: not started | in progress | done | can't tell, then one short sentence on what the frames show."""
        if version == 2 else
        """Has the cook begun this step (including preparing its own ingredients), and is it still under way or already over?
Start your answer with exactly one word: yes (begun), no (not begun), or unsure. Then one short sentence on what the frames show.""")


def parse_status(text: str, version: int = 2) -> str:
    """not started / in progress / done / can't tell. An answer that copies the option list back counts as no answer."""
    if version >= 4:
        word = re.match(r"\W*(yes|no|unsure)\b", (text or "").replace("*", ""), re.I)
        return {"yes": "in progress", "no": "not started"}.get(word[1].lower() if word else "", "can't tell")
    line = next((l for l in (text or "").replace("*", "").splitlines() if re.search(r"STATUS\W*:", l, re.I)), "")
    if line.count("|") >= 2:
        return "can't tell"
    m = re.search(r"STATUS\W*:\s*(not started|in progress|done|can'?t tell)", (text or "").replace("*", ""), re.I)
    return m[1].lower().replace("cant", "can't") if m else "can't tell"


def parse_step(text: str, open_steps: list[int]) -> int | None:
    m = re.search(r"STEP\W*:\s*(\d+)", (text or "").replace("*", ""), re.I)
    return int(m[1]) - 1 if m and int(m[1]) - 1 in open_steps else None


# --- vision backends: (answer, seconds to the first token, seconds in all) ------------------------------------------

def ask_nim(img: bytes, prompt: str, model: str, api_key: str) -> tuple[str, float, float]:
    """Not streamed: Glimmer's streamed answers arrived empty (its reasoning comes first)."""
    import requests
    t0 = time.perf_counter()
    body = {"model": model, "max_tokens": 800, "temperature": 0.2, "stream": False, "reasoning_effort": "none",
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(img).decode()}},
                {"type": "text", "text": prompt}]}]}
    r = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", json=body, timeout=120,
                      headers={"Authorization": f"Bearer {api_key}"})
    r.raise_for_status()
    sec = time.perf_counter() - t0
    return r.json()["choices"][0]["message"].get("content") or "", sec, sec


def ask_local(vlm, proc, img: bytes, prompt: str, device) -> tuple[str, float, float]:
    """Llama 3.2 Vision loaded with transformers (MllamaForConditionalGeneration + its processor), greedy, 60 tokens."""
    from PIL import Image
    from transformers import TextIteratorStreamer
    t0 = time.perf_counter()
    msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
    inputs = proc(Image.open(io.BytesIO(img)), proc.apply_chat_template(msgs, add_generation_prompt=True),
                  add_special_tokens=False, return_tensors="pt").to(device)
    streamer = TextIteratorStreamer(proc.tokenizer, skip_prompt=True, skip_special_tokens=True)
    job = threading.Thread(target=lambda: vlm.generate(**inputs, max_new_tokens=60, do_sample=False, streamer=streamer))
    job.start()
    text, first = "", None
    for piece in streamer:
        if piece and first is None:
            first = time.perf_counter() - t0
        text += piece
    job.join()
    return text, first or 0.0, time.perf_counter() - t0


class Looker:
    """Runs frame checks with a cache (one JSON file per video), so a replay never asks the same question twice.

    sheet(t) -> JPEG bytes or None; ask(img, prompt, k, t) -> (answer, first token s, total s);
    prompt(kind, k, t, evidence, open_steps) -> str.
    """

    def __init__(self, backend: str, version: int, cache: Path, sheet, ask, prompt, rerun: bool = False):
        self.backend, self.version, self.path = backend, version, Path(cache)
        self.sheet, self.ask, self.prompt = sheet, ask, prompt
        self.answers = json.loads(self.path.read_text()) if self.path.exists() and not rerun else {}

    def __call__(self, kind: str, k: int | None, t: float, evidence: str, open_steps: list[int]) -> dict:
        key = f"{self.backend}|p{self.version}|{kind}|{k}|{int(t)}|{','.join(map(str, open_steps)) if kind == 'silent' else ''}"
        if key not in self.answers:
            img = self.sheet(t)
            if img is None:
                self.answers[key] = {"answer": "", "first_s": 0.0, "sec": 0.0, "failed": "no frames"}
            else:
                try:
                    answer, first_s, sec = self.ask(img, self.prompt(kind, k, t, evidence, open_steps), k, t)
                    self.answers[key] = {"answer": answer, "first_s": round(first_s, 2), "sec": round(sec, 2)}
                except Exception as e:  # a failed check counts as "can't tell"
                    self.answers[key] = {"answer": "", "first_s": 0.0, "sec": 0.0, "failed": f"{type(e).__name__}: {e}"[:200]}
            self.path.write_text(json.dumps(self.answers, indent=1))
        rec = self.answers[key]
        out = dict(rec, kind=kind, step=k, t=t, ready=t + max(rec["sec"], 1.0))
        out["status"] = parse_status(rec["answer"], self.version) if k is not None else None
        out["found"] = parse_step(rec["answer"], open_steps) if k is None else None
        return out


def frame_checked_starts(ts, probs, names: list[str], steps_of: dict, n_steps: int, seen_p: float, seen_k: int,
                         look, s: LookSettings, use_looks: bool) -> tuple[list[dict], list[dict]]:
    """The camera rule with or without frame checks: (per-tick statuses as {"t", "ledger"}, the checks made).

    probs[i]: the probe's probability for each of `names` at tick i. Unlike coach.memory.checklist.rule_update, a
    seen action whose steps are all done still counts for its first step (so a restart can be noticed).
    """
    n = n_steps
    status, start_t, last_ev, bout = ["not started"] * n, [None] * n, [-1e9] * n, [None] * n
    wait_until, checked_bout = [-1e9] * n, set()
    streak, ticks, looks, pending = {}, [], [], None
    last_look, last_new = -1e9, float(ts[0])
    for i, tt in enumerate(ts):
        tt = float(tt)
        if pending and pending["ready"] <= tt:
            c, pending = pending, None
            k = c["step"]
            if c["kind"] == "start":
                if c["status"] in ("in progress", "done"):
                    status[k], start_t[k], last_new = c["status"], tt, tt
                else:
                    status[k] = "not started"; wait_until[k] = tt + (s.again_s if c["status"] == "not started" else s.every_s)
            elif c["kind"] == "early_end":
                if c["status"] == "not started":
                    status[k], start_t[k] = "not started", None; wait_until[k] = tt + s.again_s
                elif c["status"] == "done":
                    status[k] = "done"
            elif c["kind"] == "restart" and c["status"] == "in progress":
                status[k] = "in progress"
            elif c["kind"] == "silent" and c["found"] is not None and status[c["found"]] == "not started":
                status[c["found"]], start_t[c["found"]], last_new = "in progress", tt, tt
        seen = {}
        for a, pa in zip(names, probs[i]):
            streak[a] = streak.get(a, 0) + 1 if pa >= seen_p else 0
            if streak[a] >= seen_k:
                open_ = [k for k in steps_of[a] if status[k] != "done"] or steps_of[a][:1]
                seen.setdefault(open_[0], a)
        for k in seen:
            if tt - last_ev[k] > 10:
                bout[k] = tt
            last_ev[k] = tt
        if not use_looks:
            for k in seen:
                if status[k] == "not started":
                    status[k], start_t[k], last_new = "in progress", tt, tt
        elif pending is None and tt - last_look >= s.every_s:
            ev = lambda k: f"{seen.get(k) or 'its actions'} around {mmss(last_ev[k])}"
            job = next((("start", k) for k in seen if status[k] == "not started" and tt >= wait_until[k]), None)
            job = job or next((("early_end", k) for k in range(n) if status[k] == "in progress" and (k, bout[k]) not in checked_bout
                               and tt - last_ev[k] >= s.early_end_s and last_ev[k] - (start_t[k] or tt) < s.early_end_s), None)
            job = job or next((("restart", k) for k in seen if status[k] == "done" and (k, bout[k]) not in checked_bout), None)
            open_steps = [k for k in range(n) if status[k] == "not started"]
            if job is None and open_steps and tt - max(last_new, last_look) >= s.silent_s:
                job = ("silent", None)
            if job:
                kind, k = job
                if kind == "start":
                    status[k] = "maybe"
                if kind in ("early_end", "restart"):
                    checked_bout.add((k, bout[k]))
                pending = look(kind, k, tt, ev(k) if k is not None else "", open_steps)
                looks.append(pending); last_look = tt
        ticks.append({"t": tt, "ledger": ["not started" if x == "maybe" else x for x in status]})
    return ticks, looks
