"""Which film the pipeline works on. Unset: v4's files, so that film can still be rebuilt.

    DEMO_VERSION=v5 python3 video/pipeline/build_v5.py

Each version keeps its own beat map, narration, pages, cuts and renders, so one never overwrites another.
"""
import os
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
VERSION = os.environ.get("DEMO_VERSION", "")
SUFFIX = f"_{VERSION}" if VERSION else ""
FILM = VERSION or "v4"
BEATS_FILE = VIDEO / f"beats{SUFFIX}.json"
BEAT_MAP = VIDEO / f"beat_map{SUFFIX}.md"
AUDIO = VIDEO / f"audio{SUFFIX}"
HF = VIDEO / f"hyperframes{SUFFIX}"
HD = VIDEO / "media" / f"hd{SUFFIX}"
OUT = VIDEO / "out"
RENDERS = OUT / f"beats{SUFFIX}"
STORYBOARD = OUT / f"storyboard{SUFFIX}"
