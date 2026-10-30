"""Replay A/B/Oracle coaching on fitted real-data dynamics.

Protocol (mirrors benchmark.py, but the learner is BKT fitted on logs):
  * skills = top-N frequent skills, each with fitted BKT params;
  * per episode, each skill's hidden mastery ~ Bernoulli(p_init);
  * each session the coach picks one skill to practice; the environment
    samples correctness from the hidden state, transitions it with p_learn,
    and reports only the 0/1 observation;
  * metric = cumulative true mastery gain (final - initial, summed skills).

``make_synthetic_csv`` writes the ASSISTments 2009-2010 skill-builder
schema from known BKT params, so the full path (load -> fit -> replay)
is verifiable offline before the real file arrives.
"""
from __future__ import annotations

import csv
import math
import random

import bkt
import datasets

ASSISTMENTS_COLUMNS = ["order_id", "assignment_id", "user_id", "assistment_id",
                       "problem_id", "original", "correct", "ms_first_response",
                       "skill_id", "skill_name"]


def make_synthetic_csv(path: str, skills_params: dict, n_users: int = 60,
                       attempts: int = 25, seed: int = 0) -> None:
    """Write synthetic attempts in the ASSISTments skill-builder schema."""
    rng = random.Random(seed)
    order = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(ASSISTMENTS_COLUMNS)
        for u in range(n_users):
            user = f"u{u}"
            for skill, p in skills_params.items():
                mastered = rng.random() < p["p_init"]
                for _ in range(attempts):
                    order += 1
                    prob = (1 - p["p_slip"]) if mastered else p["p_guess"]
                    correct = 1 if rng.random() < prob else 0
                    if not mastered and rng.random() < p["p_learn"]:
                        mastered = True
                    w.writerow([order, 0, user, 0, 0, 1, correct, 0,
                                skill, skill])


def make_synthetic_junyi_csv(log_path: str, table_path: str | None,
                             skills_params: dict, n_users: int = 60,
                             attempts: int = 25, seed: int = 0) -> None:
    """Write Junyi-shaped files from known BKT params.

    The problem log deliberately uses *alternate* header names
    (uid / item_id / is_correct / timestamp) to exercise the loader's
    auto-detection; the optional exercise table maps exercises to skills.
    Each skill gets two exercises to prove the KC join works.
    """
    rng = random.Random(seed)
    skills = list(skills_params)
    exercises = [f"e{i // 2}" for i in range(2 * len(skills))]
    ex_to_skill = {ex: skills[i // 2] for i, ex in enumerate(exercises)}
    if table_path:
        with open(table_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["exercise", "kc"])
            for ex, sk in ex_to_skill.items():
                w.writerow([ex, sk])
    else:
        ex_to_skill = {ex: ex for ex in exercises}
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["uid", "item_id", "is_correct", "timestamp"])
        ts = 1_700_000_000
        for u in range(n_users):
            user = f"u{u}"
            for ex in exercises:
                p = skills_params[ex_to_skill[ex]]
                mastered = rng.random() < p["p_init"]
                for _ in range(attempts):
                    ts += rng.randint(30, 600)
                    prob = (1 - p["p_slip"]) if mastered else p["p_guess"]
                    correct = 1 if rng.random() < prob else 0
                    if not mastered and rng.random() < p["p_learn"]:
                        mastered = True
                    w.writerow([user, ex, correct, ts])


def fit_top_skills(rows: list[dict], n: int, **fit_kw) -> dict:
    """Fit BKT params for the n most frequent skills. Returns {skill: params}."""
    from datasets import to_skill_sequences  # local import: same package dir
    out = {}
    seqs_all = to_skill_sequences(rows)
    for skill in datasets.top_skills(rows, n):
        seqs = [seq for (u, s), seq in seqs_all.items() if s == skill]
        out[skill] = bkt.fit_skill(seqs, **fit_kw)
    return out


def _expected_best_next(beliefs: dict, params_map: dict) -> float:
    return max((1 - beliefs[k]) * params_map[k]["p_learn"] for k in beliefs)


def _bandit_select(counts: dict, means: dict, t: int, c: float = 0.06) -> str:
    return max(means, key=lambda k: means[k] + c * math.sqrt(math.log(t + 1) / (counts[k] + 1e-9)))


def _world_select(beliefs: dict, params_map: dict) -> str:
    best_k, best_v = None, -1e18
    for k in beliefs:
        imm = (1 - beliefs[k]) * params_map[k]["p_learn"]
        pc = bkt.p_correct_given(beliefs[k], params_map[k])
        next_c, next_w = dict(beliefs), dict(beliefs)
        next_c[k] = bkt.update_belief(beliefs[k], 1, params_map[k])
        next_w[k] = bkt.update_belief(beliefs[k], 0, params_map[k])
        nxt = pc * _expected_best_next(next_c, params_map) + \
            (1 - pc) * _expected_best_next(next_w, params_map)
        total = imm + 0.9 * nxt
        if total > best_v:
            best_k, best_v = k, total
    return best_k


def _oracle_select(states: dict, params_map: dict) -> str:
    best_k, best_v = None, -1e18
    for k in states:
        imm = (1 - states[k]) * params_map[k]["p_learn"]
        learned = dict(states, **{k: 1})
        nxt = imm * max((1 - learned[j]) * params_map[j]["p_learn"] for j in states) + \
            (1 - imm) * max((1 - states[j]) * params_map[j]["p_learn"] for j in states)
        if imm + 0.9 * nxt > best_v:
            best_k, best_v = k, imm + 0.9 * nxt
    return best_k


def run_real_episode(coach_kind: str, params_map: dict, seed: int,
                     sessions: int = 20) -> dict:
    """One coached run on BKT-simulated learners. Metric: true mastery gain."""
    rng = random.Random(seed)
    skills = list(params_map)
    states = {k: 1 if rng.random() < params_map[k]["p_init"] else 0 for k in skills}
    init_total = sum(states.values())
    beliefs = {k: params_map[k]["p_init"] for k in skills}
    counts = {k: 0 for k in skills}
    means = {k: 0.5 for k in skills}
    t, gains, actions = 0, [], []
    for _ in range(sessions):
        t += 1
        if coach_kind == "A":
            pick = _bandit_select(counts, means, t)
        elif coach_kind == "B":
            pick = _world_select(beliefs, params_map)
        elif coach_kind == "O":
            pick = _oracle_select(states, params_map)
        else:
            raise ValueError(coach_kind)
        p = params_map[pick]
        prob = (1 - p["p_slip"]) if states[pick] else p["p_guess"]
        obs = 1 if rng.random() < prob else 0
        if not states[pick] and rng.random() < p["p_learn"]:
            states[pick] = 1
        if coach_kind == "A":
            counts[pick] += 1
            means[pick] += (obs - means[pick]) / counts[pick]
        elif coach_kind == "B":
            beliefs[pick] = bkt.update_belief(beliefs[pick], obs, p)
        gains.append(sum(states.values()) - init_total)
        actions.append(pick)
    return {"gains": gains, "actions": actions}


def run_real_experiment(params_map: dict, seeds=range(40),
                        sessions: int = 20) -> dict:
    """Mean cumulative true mastery gain per session for A, B, Oracle."""
    out = {}
    for kind in ("A", "B", "O"):
        runs = [run_real_episode(kind, params_map, s, sessions)["gains"]
                for s in seeds]
        n = len(runs[0]) if runs else 0
        out[kind] = [[r[t] for r in runs] for t in range(n)]
        out[kind] = [sum(col) / len(col) for col in out[kind]]
    return out
