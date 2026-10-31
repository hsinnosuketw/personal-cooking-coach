"""Scripted test players -- SYNTHETIC, for exercising the pipeline only.

They let the dataset -> training -> AI-chef loop run before any human has
played. Their rounds are tagged source "synthetic-bot", live in
gameplay/synthetic/ (git-ignored) and are only used when asked for. They
are never reported as human results.
"""
from __future__ import annotations

import random

from . import physics

STYLES = {  # (heat range, salt when moisture below, serve when colour reaches, water when colour above)
    "careful": ((3, 5), 0.95, 0.27, 0.40),
    "hurried": ((6, 9), 0.55, 0.38, 0.60),
    "erratic": ((1, 9), 0.75, 0.32, 0.50),
}


def play(style: str, seed: int) -> dict:
    rng = random.Random(seed)
    (lo, hi), salt_at, serve_at, water_at = STYLES[style]
    s, t, trs = physics.new_state(rng), 0.0, []
    heat = float(rng.randint(lo, hi))
    while t < physics.TIME_LIMIT and s["color"] < serve_at + rng.uniform(-0.05, 0.08):
        if rng.random() < 0.15:
            heat = float(min(9, max(1, heat + rng.choice((-2, -1, 1, 2)))))
        a = {"heat": heat, "salt": not s["salted"] and s["moisture"] < salt_at + rng.uniform(-0.05, 0.05),
             "water": s["color"] > water_at and rng.random() < 0.3}
        s2 = physics.tick(s, a["heat"], a["salt"], a["water"])
        trs.append({"t": t, "s": s, "a": a, "s2": s2})
        s, t = s2, t + physics.DT
    return {"schema": 1, "source": "synthetic-bot", "player": f"bot-{style}", "seed": seed,
            "transitions": trs, "final": {"t": t, "state": s, "score": physics.score(s, t)}}
