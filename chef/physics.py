"""The cooking game's engine: onion physics, player actions and the dish score.

play.html runs a line-for-line JavaScript port of these rules, and the AI
chef is scored here. The learned world model never reads this module -- it
only sees logged gameplay (see learn.py).

Goal: sweat the Pasta onion base -- translucent and soft (colour ~0.30),
not browned (above 0.45), not scorched, salted while still wet -- and serve
it before the 600-second limit. Too much heat scorches small pieces and
edges even while the batch is still wet -- sooner with uneven dice -- so
blasting the heat is fast but ruins the dish.
"""
from __future__ import annotations

import random
from dataclasses import replace

import numpy as np

from livecoach.onion import Onion, simulate

DT = 5                 # cooking seconds per logged transition
TIME_LIMIT = 600
TARGET, MAX_COLOR = 0.30, 0.45
HEAT_MIN, HEAT_MAX = 1, 9
STATE_KEYS = ("color", "moisture", "heat", "salted", "salted_wet", "cut_cv", "scorch")


def new_state(rng: random.Random) -> dict:
    """Every round starts raw, on heat 5, with a random dice evenness."""
    return as_dict(Onion(color=0.05, moisture=1.0, heat=5.0, cut_cv=round(rng.uniform(0.05, 0.35), 3)), 0.0)


def scorch_rate(heat, cut_cv):
    """Scorch per second. Small pieces catch first, so the safe heat drops with
    uneven dice: about 5.3 for an even cut (cut_cv 0.05), 4.1 for a ragged one (0.35)."""
    return 0.0006 * np.maximum(0.0, heat - (5.5 - 4 * cut_cv)) ** 1.5 * (1 + 2 * cut_cv)


def tick(s: dict, heat: float, salt: bool, water: bool) -> dict:
    """One logged transition: actions at the start, then DT seconds of cooking."""
    o, scorch = from_dict(s)
    o = replace(o, heat=float(min(HEAT_MAX, max(HEAT_MIN, heat))))
    if salt and not o.salted:
        o = replace(o, salted=True, salted_wet=o.moisture > 0.6)
    if water:
        o = replace(o, moisture=min(1.0, o.moisture + 0.25), color=max(0.0, o.color - 0.03))
    scorch += DT * float(scorch_rate(o.heat, o.cut_cv))
    return as_dict(simulate(o, DT), scorch)


def score_parts(color, scorch, salted, salted_wet, t):
    """The score rules, vectorised so the planner can score many imagined pans at once."""
    q = np.maximum(0.0, 1 - np.abs(color - TARGET) / TARGET) * 100
    q = np.where(color > MAX_COLOR, q * 0.3, q) * np.maximum(0.0, 1 - scorch)
    salt = np.where(salted, np.where(salted_wet, 10, 0), -15)
    return q, salt, q + salt - t / 30


def score(s: dict, t: float) -> dict:
    q, salt, total = score_parts(s["color"], s["scorch"], s["salted"], s["salted_wet"], t)
    return {"total": round(float(total), 1), "quality": round(float(q), 1), "salt": int(salt),
            "time": round(-t / 30, 1), "scorch": round(s["scorch"], 3)}


def as_dict(o: Onion, scorch: float) -> dict:
    return {"color": round(o.color, 4), "moisture": round(o.moisture, 4), "heat": o.heat,
            "salted": o.salted, "salted_wet": o.salted_wet, "cut_cv": o.cut_cv,
            "scorch": round(scorch, 4)}


def from_dict(d: dict) -> tuple[Onion, float]:
    return (Onion(color=float(d["color"]), moisture=float(d["moisture"]), heat=float(d["heat"]),
                  salted=bool(d["salted"]), salted_wet=bool(d["salted_wet"]), cut_cv=float(d["cut_cv"])),
            float(d["scorch"]))
