"""Which film the pipeline works on. Unset: v4's files, so that film can still be rebuilt.

    DEMO_VERSION=v5 python3 video/review/build_review.py OUT_DIR

Each version keeps its own beat map, so changing one never overwrites another.
"""
import os
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
VERSION = os.environ.get("DEMO_VERSION", "")
SUFFIX = f"_{VERSION}" if VERSION else ""
BEATS_FILE = VIDEO / f"beats{SUFFIX}.json"
BEAT_MAP = VIDEO / f"beat_map{SUFFIX}.md"
