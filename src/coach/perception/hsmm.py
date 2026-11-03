"""HSMM step tracking (stage 28): which recipe step the cook is on, from the probe's verb and noun probabilities.

Each step is a chain of `shape` sub-states, so a stay has a minimum and a typical length (negative binomial); when a
stay ends the cook moves on, skips one, goes back, or starts a repeated run again. Forward filtering only: the step
posterior at t uses predictions up to t.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .scorer import match_scores


@dataclass(frozen=True)
class HSMMParams:
    """One prior for every recipe, tuned on the scrambled eggs only (a 144-setting grid)."""
    shape: int = 4           # a stay on a step lasts at least 4 s ...
    mean_s: float = 20       # ... and 20 s on average
    temp: float = 1.0        # the probe's evidence as is
    floor: float = 0.05      # never rule a step out on one second
    p_next: float = 0.80     # where a stay goes when it ends (cooks interleave steps)
    p_skip: float = 0.10
    p_back: float = 0.50
    p_loop: float = 0.50


def hsmm_transitions(n: int, loops: list[dict], p: HSMMParams) -> np.ndarray:
    """[n*m, n*m]: each step is a chain of m sub-states (its duration); the chain's end jumps to another step."""
    m, stay = p.shape, 1 - p.shape / p.mean_s
    loop_back = {lp["last"]: lp["first"] for lp in loops}
    A = np.zeros((n * m, n * m))
    for k in range(n):
        for j in range(m):
            s = k * m + j
            A[s, s] = stay
            if j < m - 1:
                A[s, s + 1] = 1 - stay
                continue
            out = np.zeros(n)  # leaving step k
            if k + 1 < n: out[k + 1] += p.p_next
            if k + 2 < n: out[k + 2] += p.p_skip
            if k > 0: out[:k] += p.p_back / k
            if k in loop_back: out[loop_back[k]] += p.p_loop   # the recipe repeats this run of steps
            if out.sum() == 0:
                A[s, s] = 1.0
                continue
            A[s, np.arange(n) * m] += (1 - stay) * out / out.sum()
    return A


def hsmm_track(bank, pred: dict, n_steps: int, loops: list[dict], p: HSMMParams = HSMMParams(),
               drop=()) -> tuple[np.ndarray, np.ndarray]:
    """(most likely step per tick, step posterior per tick). drop: steps whose evidence is removed
    (stage 36 pretends the cook skipped them)."""
    n, m = n_steps, p.shape
    A = hsmm_transitions(n, loops, p)
    ev = match_scores(bank, pred["verb"].astype(float), pred["noun"].astype(float)) / p.temp
    ev = np.exp(ev - ev.max(1, keepdims=True))
    ev = (1 - p.floor) * ev / ev.sum(1, keepdims=True) + p.floor / n
    ev[:, list(drop)] = p.floor / n
    alpha = np.zeros(n * m); alpha[0] = 0.6; alpha[np.arange(1, n) * m] = 0.4 / max(1, n - 1)
    post = np.zeros((len(ev), n))
    for i in range(len(ev)):
        alpha = (alpha @ A) * np.repeat(ev[i], m)
        alpha /= alpha.sum()
        post[i] = alpha.reshape(n, m).sum(1)
    return post.argmax(1), post


def stable_changes(seq, hold: int) -> list[tuple[int, int]]:
    """(tick, new step) when a step has led `hold` ticks in a row after a different one."""
    out, shown = [], None
    for i in range(hold - 1, len(seq)):
        k = int(seq[i])
        if k != shown and all(int(x) == k for x in seq[i - hold + 1: i + 1]):
            out.append((i, k)); shown = k
    return out
