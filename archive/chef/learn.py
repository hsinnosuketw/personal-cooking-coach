"""Gameplay -> transitions -> a learned world model of the pan.

Each logged transition is (state, action) -> next state over DT seconds.
The model predicts the change in colour and moisture with gradient-boosted
trees (they handle the sweat-then-brown regime switch well). Salt
bookkeeping (salted / salted_wet) is copied from the action, since the
player sees it directly; everything physical is learned from data.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

FEATURES = ["color", "moisture", "heat", "salted_wet", "salt", "water", "cut_cv", "scorch"]
TARGETS = ("d_color", "d_moisture", "d_scorch")


def rows(s: dict, a: dict) -> list[float]:
    return [s["color"], s["moisture"], a["heat"], float(s["salted_wet"]),
            float(a["salt"] and not s["salted"]), float(a["water"]), s["cut_cv"], s["scorch"]]


def transitions(episodes: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    X, Y = [], []
    for ep in episodes:
        for tr in ep["transitions"]:
            X.append(rows(tr["s"], tr["a"]))
            Y.append([tr["s2"][k] - tr["s"][k] for k in ("color", "moisture", "scorch")])
    return np.array(X), np.array(Y)


class LearnedWorldModel:
    def __init__(self):
        self.models = [HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, random_state=0)
                       for _ in TARGETS]
        self.n_train = 0

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "LearnedWorldModel":
        for k, m in enumerate(self.models):
            m.fit(X, Y[:, k])
        self.n_train = len(X)
        return self

    def predict_arrays(self, X: np.ndarray) -> tuple[np.ndarray, ...]:
        """(d_colour, d_moisture, d_scorch) for rows in FEATURES order. One thread: for the
        planner's small batches, thread start-up costs ~6x the prediction."""
        with threadpool_limits(1):
            return tuple(m.predict(X) for m in self.models)

    def predict_batch(self, states: list[dict], actions: list[dict]) -> list[dict]:
        dc, dm, ds = self.predict_arrays(np.array([rows(s, a) for s, a in zip(states, actions)]))
        out = []
        for s, a, c, w, z in zip(states, actions, dc, dm, ds):
            salt_now = a["salt"] and not s["salted"]
            out.append({"color": float(np.clip(s["color"] + c, 0, 1)),
                        "moisture": float(np.clip(s["moisture"] + w, 0, 1)), "heat": a["heat"],
                        "salted": s["salted"] or a["salt"],
                        "salted_wet": s["salted_wet"] or (salt_now and s["moisture"] > 0.6),
                        "cut_cv": s["cut_cv"], "scorch": float(max(0.0, s["scorch"] + z))})
        return out

    def error(self, X: np.ndarray, Y: np.ndarray) -> dict:
        """Mean absolute error on held-out transitions, per predicted quantity."""
        return {name: float(np.mean(np.abs(m.predict(X) - Y[:, k])))
                for k, (name, m) in enumerate(zip(TARGETS, self.models))}
