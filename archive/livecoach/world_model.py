"""Action-conditioned comparison with a validity-scoped cache (plan E03/E05/E08).

One provider call compares every candidate. A cached answer is reused only
while recipe, step, the rounded relevant facts, the skill levels that shape
coaching and the candidate set are all unchanged.
"""
from __future__ import annotations

from . import belief, recipes
from .schema import Candidate, KitchenState, SkillBelief, WMPrediction

RELEVANT = ("onion_color", "moisture", "heat_level", "salted", "smoke", "cut_uniformity")


def _rounded(v):
    return round(v / 0.05) * 0.05 if isinstance(v, float) else v


class WorldModel:
    def __init__(self, provider):
        self.provider = provider
        self.cache: dict = {}
        self.hits = 0

    def key(self, state: KitchenState, beliefs: dict[str, SkillBelief],
            cands: list[Candidate], horizon_s: int) -> tuple:
        step = recipes.step(state.recipe_id, state.step_id)
        facts = tuple(sorted((k, _rounded(f.value), f.status.value)
                             for k, f in state.facts.items() if k in RELEVANT))
        return (state.recipe_id, state.step_id, facts, belief.version(beliefs, step["skills"]),
                tuple(c.candidate_id for c in cands), horizon_s)

    def compare(self, state, beliefs, cands, horizon_s: int = 120) -> tuple[list[WMPrediction], str]:
        k = self.key(state, beliefs, cands, horizon_s)
        if k in self.cache:
            self.hits += 1
            return self.cache[k], "cache"
        preds = self.provider.compare(state, beliefs, cands, horizon_s)
        self.cache[k] = preds
        return preds, "model"
