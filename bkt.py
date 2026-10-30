"""Bayesian Knowledge Tracing (BKT) per skill: fit, track, simulate.

BKT models one skill with a binary hidden state (unlearned/learned):
  P(mastered at first sight)            = p_init
  P(unlearned -> learned) after 1 try   = p_learn
  P(correct | learned)                  = 1 - p_slip
  P(correct | unlearned)                = p_guess

Fitting maximizes total log-likelihood over the skill's (user, skill)
sequences with a coarse grid search -- transparent, dependency-free, and
fast enough for the top-N frequent skills. Belief tracking is the exact
forward update; simulation samples hidden transitions + observations from
fitted params, giving the A/B/Oracle replay a real-data dynamics engine.
"""
from __future__ import annotations

import itertools
import math


def seq_loglik(seq: list[int], p_init: float, p_learn: float,
               p_guess: float, p_slip: float) -> float:
    """Forward-algorithm log-likelihood of one correctness sequence."""
    p = p_init
    ll = 0.0
    for c in seq:
        p_correct = p * (1 - p_slip) + (1 - p) * p_guess
        p_correct = min(max(p_correct, 1e-9), 1 - 1e-9)
        ll += math.log(p_correct if c else 1 - p_correct)
        # Posterior, then the learning transition.
        post = p * (1 - p_slip) / p_correct if c else \
            p * p_slip / (1 - p_correct)
        p = post + (1 - post) * p_learn
    return ll


def fit_skill(seqs: list[list[int]],
              grid_init=(0.1, 0.3, 0.5),
              grid_learn=(0.05, 0.15, 0.3),
              grid_guess=(0.05, 0.2, 0.35),
              grid_slip=(0.05, 0.15, 0.25),
              max_len: int = 50) -> dict:
    """Grid-search BKT params maximizing total log-likelihood.

    Returns {"p_init","p_learn","p_guess","p_slip","loglik","n_seq"}.
    Sequences longer than `max_len` are truncated (early attempts carry
    almost all the information about learning speed).
    """
    seqs = [s[:max_len] for s in seqs if s]
    best: dict = {"loglik": -math.inf}
    for p_init, p_learn, p_guess, p_slip in itertools.product(
            grid_init, grid_learn, grid_guess, grid_slip):
        ll = sum(seq_loglik(s, p_init, p_learn, p_guess, p_slip) for s in seqs)
        if ll > best["loglik"]:
            best = {"p_init": p_init, "p_learn": p_learn, "p_guess": p_guess,
                    "p_slip": p_slip, "loglik": ll, "n_seq": len(seqs)}
    return best


def update_belief(p_learned: float, correct: int, params: dict) -> float:
    """One forward step: posterior on the observation, then transition."""
    p_guess, p_slip, p_learn = params["p_guess"], params["p_slip"], params["p_learn"]
    p_correct = p_learned * (1 - p_slip) + (1 - p_learned) * p_guess
    p_correct = min(max(p_correct, 1e-9), 1 - 1e-9)
    post = p_learned * (1 - p_slip) / p_correct if correct else \
        p_learned * p_slip / (1 - p_correct)
    return post + (1 - post) * p_learn


def p_correct_given(belief: float, params: dict) -> float:
    """Predicted P(correct) under a mastery belief."""
    return belief * (1 - params["p_slip"]) + (1 - belief) * params["p_guess"]
