"""Immutable data passed between the guide's layers (design doc section 2).

A recipe step's "action vector" is its verb/noun signature: how much of
each EK100 verb and noun the step involves. The released V-JEPA 2 probe
predicts verb/noun probabilities, so a signature can be scored against a
prediction directly. raw_text is kept for display, and for a future
text-conditioned predictor.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class StepSpec:
    """One recipe step as an extractor hands it over, before vectorising."""
    step_id: str
    text: str
    order: int
    pairs: tuple[tuple[str, str, float], ...]  # (verb key, noun key, weight)


@dataclass(frozen=True)
class CandidateAction:
    action_id: str
    raw_text: str
    step_order_hint: int
    verb_sig: np.ndarray  # [n_verbs], sums to 1
    noun_sig: np.ndarray  # [n_nouns], sums to 1


@dataclass(frozen=True)
class Prediction:
    """What the world model expects about 1 s ahead: probe probabilities."""
    timestamp: float
    verb: np.ndarray
    noun: np.ndarray


@dataclass(frozen=True)
class PredictionResult:
    timestamp: float
    action: CandidateAction
    scores: np.ndarray  # [N] one per candidate, same order as the bank
    confidence: float   # softmax probability of the best candidate
    should_pause: bool
    extras: dict = field(default_factory=dict)
