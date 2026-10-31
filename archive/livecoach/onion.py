"""Deterministic onion-in-the-pan model: the mock world model's physics.

Not food science -- a small, explainable stand-in so offline predictions
really differ by candidate action. Scales: colour 0 raw, 0.3 translucent,
0.6 golden, 0.75 deep golden-brown, 1.0 burnt; moisture 1 raw ... 0 dry;
heat is the stove dial 1-10; cut_cv is the spread of piece sizes.
"""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Onion:
    color: float = 0.05
    moisture: float = 1.0
    heat: float = 5.0
    salted: bool = False
    salted_wet: bool = False  # salted while wet: the drawn-out water delays browning
    cut_cv: float = 0.10      # 0.05 even dice ... 0.4 very uneven


def simulate(o: Onion, seconds: float) -> Onion:
    """Advance one second at a time: sweat while wet, brown once dry enough."""
    color, moisture = o.color, o.moisture
    brown_below = 0.35 if o.salted_wet else 0.45
    for _ in range(int(seconds)):
        moisture = max(0.0, moisture - 0.00025 * o.heat)
        if moisture > brown_below:  # still steaming: only goes translucent
            color += 0.0008 * o.heat * max(0.0, 0.30 - color) / 0.30
        else:                       # dry enough to brown; small pieces race ahead
            color += 0.00018 * max(0.0, o.heat - 2) ** 1.5 * (1 + o.cut_cv)
    return replace(o, color=min(1.0, color), moisture=moisture)


def burn_risk(o: Onion) -> float:
    """How likely some pieces scorch: rises near brown, worse with uneven cuts."""
    return max(0.0, min(1.0, (o.color + 0.6 * o.cut_cv - 0.75) / 0.25))


def apply_action(o: Onion, candidate_id: str) -> Onion:
    if candidate_id == "lower_heat":
        return replace(o, heat=max(2.0, o.heat - 2))
    if candidate_id == "raise_heat":
        return replace(o, heat=min(9.0, o.heat + 2))
    if candidate_id == "add_salt_now":
        return replace(o, salted=True, salted_wet=o.moisture > 0.6)
    if candidate_id == "add_water_splash":
        return replace(o, moisture=min(1.0, o.moisture + 0.25), color=max(0.0, o.color - 0.03))
    return o


def describe(o: Onion) -> str:
    c = o.color
    word = ("還是生的" if c < 0.2 else "透明變軟" if c < 0.45 else "金黃"
            if c < 0.7 else "深金褐" if c < 0.88 else "焦黑")
    return f"{word}（色度 {c:.2f}，水分 {o.moisture:.2f}）"
