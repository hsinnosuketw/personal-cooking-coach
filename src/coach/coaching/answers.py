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
