"""Reading the coach's answers.

The reminder prompts ask for two headings, "Where:" and "Next:". When the coach put each heading on its own line,
the old parser kept only the first paragraph, so the advice read just "Where:". The advice is the Next part.
"""
from __future__ import annotations

import re

_NEXT = re.compile(r"^\W*Next\W*:\s*", re.I | re.M)
_END = re.compile(r"\n\s*\n|^\W*(DONE|IN PROGRESS|LEFT|STEP|REMIND|LOOK)\W*:", re.I | re.M)


def advice_text(next_: str, text: str | None) -> str:
    """The advice to show: `next_` as parsed, or the answer's Next part when `next_` is only a heading."""
    if len(next_.strip()) >= 12 or not text or not _NEXT.search(text):
        return next_
    part = _NEXT.split(text, maxsplit=1)[1]
    return _END.split(part, maxsplit=1)[0].strip() or next_


def _numbers(line: str, n_steps: int) -> list[int]:
    return [int(x) - 1 for x in re.findall(r"\d+", line) if 1 <= int(x) <= n_steps]


def parse_ledger(text: str, n_steps: int) -> dict | None:
    """The DONE / IN PROGRESS / LEFT / STEP lines as 0-based step lists; None if any line is missing."""
    out = {}
    for key in ("DONE", "IN PROGRESS", "LEFT", "STEP"):
        found = re.findall(rf"^\W*{key}\W*:\s*(.*)$", text or "", re.I | re.M)
        if not found:
            return None
        out[key] = sorted(set(_numbers(found[-1], n_steps)))
    return out


def _one_step(text: str, key: str, n_steps: int) -> int | None:
    """The first step number on the last `key:` line (REMIND, LOOK), or None."""
    found = re.findall(rf"^\W*{key}\W*:\s*(.*)$", (text or "").replace("*", ""), re.I | re.M)
    nums = _numbers(found[-1], n_steps) if found else []
    return nums[0] if nums else None


def parse_remind(text: str, n_steps: int) -> int | None:
    return _one_step(text, "REMIND", n_steps)


def parse_look(text: str, n_steps: int) -> int | None:
    return _one_step(text, "LOOK", n_steps)


def parse_intent(text: str, n_steps: int) -> dict:
    """The Now / Goal headings and the DOING line of a three-layer answer (stage 30)."""
    clean = (text or "").replace("*", "")
    grab = lambda head: " ".join((re.findall(rf"^\W*{head}\W*:\s*(.*)$", clean, re.I | re.M) or [""])[0].split())
    doing = re.findall(r"^\W*DOING\W*:\s*(.*)$", clean, re.I | re.M)
    nums = _numbers(doing[-1], n_steps) if doing else []
    return {"now": grab("Now"), "goal": grab("Goal"), "doing": nums[0] if nums else None}


def advice_part(text: str) -> str:
    """The "Next" paragraph, without the checklist lines.

    The checklist starts at the last DONE line: a "Done: step 3 …" line inside the Where section used to cut the
    answer there, leaving only "Where:" as the advice (25 of 862 saved answers)."""
    text = text or ""
    starts = [m.start() for m in re.finditer(r"^\W*DONE\W*:", text, re.M | re.I)]
    body = text[:starts[-1]] if starts else text
    body = body.split("Next:")[-1] if "Next:" in body else body
    return " ".join(body.replace("*", "").split())


def next_of(text: str) -> str:
    """The advice of a stage 30+ answer (also without a DOING line)."""
    return advice_part(re.sub(r"^\W*DOING\W*:.*$", "", text or "", flags=re.I | re.M))


def next_part(text: str) -> str:
    """The advice of a stage 18 answer (no checklist lines)."""
    part = text.split("Next:")[-1] if "Next:" in text else text
    return " ".join(part.replace("*", "").replace("STEP:", " STEP:").split())


def parse_step_number(text: str) -> int | None:
    """Stage 17's appended "STEP: <n>" line (0-based), without checking it is a step of the recipe."""
    found = re.findall(r"^\W*STEP\W*(\d+)", text or "", re.I | re.M)
    return int(found[-1]) - 1 if found else None
