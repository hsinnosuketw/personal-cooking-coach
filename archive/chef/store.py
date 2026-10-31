"""Gameplay storage: validate a played round and save it to the dataset.

Rounds arrive from browsers (possibly other people on the local network),
so everything is checked: shapes, ranges, sizes and a file-count cap. The
score is recomputed from the final state rather than trusted.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import time
import uuid

from . import physics

ROOT = pathlib.Path(__file__).resolve().parent.parent / "gameplay"
HUMAN_DIR = ROOT / "episodes"
AI_RUNS = pathlib.Path(__file__).resolve().parent.parent / "ai_chef_runs.json"
MAX_BYTES = 1_500_000
MAX_TRANSITIONS = physics.TIME_LIMIT // physics.DT + 2
MAX_FILES = 5000
STATE_KEYS = physics.STATE_KEYS


def _state(d) -> dict:
    if not isinstance(d, dict) or set(d) < set(STATE_KEYS):
        raise ValueError("state needs " + ", ".join(STATE_KEYS))
    out = {}
    for k in ("color", "moisture", "heat", "cut_cv", "scorch"):
        v = d[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{k} must be a number")
        out[k] = float(v)
    if not (0 <= out["color"] <= 1 and 0 <= out["moisture"] <= 1 and 0 <= out["cut_cv"] <= 0.5
            and 0 <= out["scorch"] <= 20 and physics.HEAT_MIN <= out["heat"] <= physics.HEAT_MAX):
        raise ValueError("state out of range")
    for k in ("salted", "salted_wet"):
        if not isinstance(d[k], bool):
            raise ValueError(f"{k} must be true/false")
        out[k] = d[k]
    return out


def _action(d) -> dict:
    if not isinstance(d, dict):
        raise ValueError("action must be an object")
    heat = d.get("heat")
    if isinstance(heat, bool) or not isinstance(heat, (int, float)) or not physics.HEAT_MIN <= heat <= physics.HEAT_MAX:
        raise ValueError("action heat out of range")
    if not isinstance(d.get("salt"), bool) or not isinstance(d.get("water"), bool):
        raise ValueError("salt and water must be true/false")
    return {"heat": float(heat), "salt": d["salt"], "water": d["water"]}


def validate(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise ValueError("round too large")
    ep = json.loads(raw)
    trs = ep.get("transitions")
    if not isinstance(trs, list) or not 1 <= len(trs) <= MAX_TRANSITIONS:
        raise ValueError("transitions must be a non-empty list")
    clean = [{"t": float(tr["t"]), "s": _state(tr["s"]), "a": _action(tr["a"]), "s2": _state(tr["s2"])}
             for tr in trs]
    final = _state(ep.get("final", {}).get("state"))
    t_end = float(ep["final"]["t"])
    if not 0 <= t_end <= physics.TIME_LIMIT + physics.DT:
        raise ValueError("final time out of range")
    player = re.sub(r"[^\w .\-]", "", str(ep.get("player", "player")))[:24].strip() or "player"
    return {"schema": 1, "source": "human", "player": player, "transitions": clean,
            "final": {"t": t_end, "state": final, "score": physics.score(final, t_end)}}


def save(ep: dict, folder: pathlib.Path | None = None) -> pathlib.Path:
    folder = folder or HUMAN_DIR  # read at call time, so tests can point it elsewhere
    folder.mkdir(parents=True, exist_ok=True)
    if sum(1 for _ in folder.glob("*.json")) >= MAX_FILES:
        raise ValueError("dataset is full")
    ep = dict(ep, episode_id=uuid.uuid4().hex[:12], saved_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    path = folder / f"{time.strftime('%Y%m%d-%H%M%S')}-{ep['episode_id']}.json"
    path.write_text(json.dumps(ep, ensure_ascii=False), encoding="utf-8")
    return path


def load(folder: pathlib.Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]


def leaderboard(n: int = 10) -> dict:
    humans = load(HUMAN_DIR) if HUMAN_DIR.exists() else []
    top = sorted(({"player": e["player"], "score": e["final"]["score"]["total"], "t": e["final"]["t"]}
                  for e in humans), key=lambda r: -r["score"])[:n]
    ai = json.loads(AI_RUNS.read_text(encoding="utf-8")) if AI_RUNS.exists() else None
    return {"human_rounds": len(humans), "top": top,
            "ai": ai and {"mean": ai["summary"]["ai_mean"], "trained_on": ai["trained_on"]}}
