"""The AI chef: plans with the learned world model, cooks in the real game.

Every DT seconds it tries 36 options (heat 1-9 x salt now or not x water or
not), imagines the next HORIZON ticks (80 s) with the *learned* model holding that
heat, and takes the option whose imagined future reaches the best score.
It serves when no option beats serving now. Its rounds are then played in
the real engine (physics.py), so the score is earned, not imagined.
"""
from __future__ import annotations

import random

import numpy as np

from . import physics
from .learn import LearnedWorldModel

HORIZON = 16  # ticks imagined ahead (80 s); it re-plans every tick
OPTIONS = [{"heat": float(h), "salt": s, "water": w} for h in range(1, 10) for s in (False, True)
           for w in (False, True)]


def decide(model: LearnedWorldModel, s: dict, t: float) -> dict | None:
    """The next action, or None to serve now. All options are imagined in parallel."""
    opts = [a for a in OPTIONS if not (a["salt"] and s["salted"])]
    n = len(opts)
    color, moist = np.full(n, s["color"]), np.full(n, s["moisture"])
    salted, wet = np.full(n, s["salted"]), np.full(n, s["salted_wet"])
    heat = np.array([a["heat"] for a in opts])
    salt = np.array([a["salt"] for a in opts]) & ~salted
    water = np.array([a["water"] for a in opts], dtype=float)
    cut, scorch, best = np.full(n, s["cut_cv"]), np.full(n, s["scorch"]), np.full(n, -1e9)
    for k in range(1, min(HORIZON, int((physics.TIME_LIMIT - t) // physics.DT)) + 1):
        dc, dm, ds = model.predict_arrays(np.column_stack([color, moist, heat, wet, salt, water, cut, scorch]))
        wet, salted = wet | (salt & (moist > 0.6)), salted | salt
        color, moist, scorch = np.clip(color + dc, 0, 1), np.clip(moist + dm, 0, 1), np.maximum(0, scorch + ds)
        best = np.maximum(best, physics.score_parts(color, scorch, salted, wet, t + k * physics.DT)[2])
        salt, water = np.zeros(n, dtype=bool), np.zeros(n)  # then just hold the heat
    i = int(np.argmax(best))
    if physics.score(s, t)["total"] >= best[i]:
        return None
    return opts[i]


def play(model: LearnedWorldModel, seed: int) -> dict:
    """One full round in the real engine, logged in the same format as human play."""
    rng = random.Random(seed)
    s, t, trs = physics.new_state(rng), 0.0, []
    while t < physics.TIME_LIMIT:
        a = decide(model, s, t)
        if a is None:
            break
        s2 = physics.tick(s, a["heat"], a["salt"], a["water"])
        trs.append({"t": t, "s": s, "a": a, "s2": s2})
        s, t = s2, t + physics.DT
    return {"schema": 1, "source": "ai-chef", "player": "AI chef", "seed": seed, "transitions": trs,
            "final": {"t": t, "state": s, "score": physics.score(s, t)}}
