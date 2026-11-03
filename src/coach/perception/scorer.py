"""Score every recipe step against the world model's prediction, and decide when to pause.

Batched (design doc section 4): for T predictions and N steps,
  match[T, N] = log(P_verb @ V.T) + log(P_noun @ Nn.T)
is two matrix products, with no loop over candidates. The probe's outputs
are sigmoid scores, so each row is normalised to a distribution first.

Recipes roughly run in order, so a prior favours staying on the current
step or moving to the next one. Real cooks interleave steps (HD-EPIC's
P08 cracks the eggs after starting the onions), so the prior is only a
nudge: its log is scaled by PRIOR_WEIGHT before adding it to the evidence. The guide pauses when a different step
leads by a clear margin for `patience` ticks in a row (hysteresis), so one
noisy second doesn't flip the suggestion.
"""
from __future__ import annotations

import numpy as np

from .action_bank import ActionBankRepository
from ..domain import Prediction, PredictionResult

STAY, NEXT = 0.45, 0.35  # prior mass for the current and next step; the rest is shared
PRIOR_WEIGHT = 0.3       # 1 = trust recipe order fully; 0 = ignore it


def _normalise(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.atleast_2d(p).astype(float), 1e-9, None)
    return p / p.sum(axis=1, keepdims=True)


def match_scores(bank: ActionBankRepository, p_verb: np.ndarray, p_noun: np.ndarray) -> np.ndarray:
    """[T, N] log-likelihood that each step explains each predicted verb/noun distribution."""
    V, Nn = bank.get_batched_embeddings()
    return np.log(_normalise(p_verb) @ V.T) + np.log(_normalise(p_noun) @ Nn.T)


def order_prior(n: int, current: int) -> np.ndarray:
    """log prior over the n steps given the current one (-1 = not started)."""
    prior = np.zeros(n)
    rest = [k for k in range(n) if k not in (current, current + 1)]
    if 0 <= current < n:
        prior[current] = STAY
    if current + 1 < n:
        prior[current + 1] = NEXT
    leftover = 1.0 - prior.sum()
    for k in rest:
        prior[k] = leftover / len(rest)
    if not rest:
        prior /= prior.sum()
    return np.log(np.clip(prior, 1e-9, None))


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


class LatentStateScorer:
    def __init__(self, bank: ActionBankRepository, margin: float = 0.15, patience: int = 2):
        self.bank, self.margin, self.patience = bank, margin, patience
        self.current = -1
        self._streak = (None, 0)

    def reset(self) -> None:
        self.current, self._streak = -1, (None, 0)

    def evaluate(self, pred: Prediction, match: np.ndarray | None = None) -> PredictionResult:
        """One tick. `match` lets precomputed batched scores be reused."""
        cands = self.bank.get_all_candidates()
        m = match if match is not None else match_scores(self.bank, pred.verb, pred.noun)[0]
        scores = m + PRIOR_WEIGHT * order_prior(len(cands), self.current)
        post = softmax(scores)
        best = int(post.argmax())
        lead = post[best] - (post[self.current] if self.current >= 0 else 0.0)
        candidate = best if best != self.current and lead >= self.margin else None
        streak = self._streak[1] + 1 if candidate is not None and candidate == self._streak[0] else 1
        self._streak = (candidate, streak if candidate is not None else 0)
        pause = candidate is not None and streak >= self.patience
        if pause:
            self.current, self._streak = candidate, (None, 0)
        shown = self.current if self.current >= 0 else best
        return PredictionResult(pred.timestamp, cands[shown], scores, float(post[shown]), pause,
                                {"posterior": post, "best": best, "current": self.current})
