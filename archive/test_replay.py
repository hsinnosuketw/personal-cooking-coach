"""Tests for the real-data path: load ASSISTments-format CSV, fit BKT,
replay A/B/Oracle on fitted dynamics. Synthetic data only (offline)."""
import csv
import os
import tempfile

import bkt
import datasets
import replay


TRUE_PARAMS = {
    "s1": {"p_init": 0.3, "p_learn": 0.15, "p_guess": 0.2, "p_slip": 0.15},
    "s2": {"p_init": 0.1, "p_learn": 0.3, "p_guess": 0.2, "p_slip": 0.1},
}


def _synthetic_path(n_users=40, attempts=25):
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    replay.make_synthetic_csv(path, TRUE_PARAMS, n_users=n_users,
                              attempts=attempts, seed=1)
    return path


def test_loader_schema_and_drops():
    path = _synthetic_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([999, 0, "uX", 0, 0, 1, 2, 0, "s1", "s1"])  # bad correct
            w.writerow([1000, 0, "", 0, 0, 1, 1, 0, "", ""])       # missing ids
        rows, dropped = datasets.load_csv(path)
        assert dropped.get("bad_correct", 0) == 1
        assert dropped.get("missing_id", 0) == 1
        assert all(r["correct"] in (0, 1) for r in rows)
        assert rows == sorted(rows, key=lambda r: (r["user"], r["order"]))
        s = datasets.summarize(rows)
        assert s["users"] == 40 and s["skills"] == 2
    finally:
        os.unlink(path)


def test_fit_recovers_known_params():
    # p_learn/p_guess (the dynamics that drive coaching) must recover
    # tightly; p_init/p_slip are only weakly identified from short
    # sequences (a known BKT property), so they get a loose bound.
    path = _synthetic_path()
    try:
        rows, _ = datasets.load_csv(path)
        fitted = replay.fit_top_skills(rows, 2)
        for skill, true in TRUE_PARAMS.items():
            for k in ("p_learn", "p_guess"):
                assert abs(fitted[skill][k] - true[k]) < 0.06, (skill, k, fitted[skill])
            for k in ("p_init", "p_slip"):
                assert abs(fitted[skill][k] - true[k]) < 0.25, (skill, k, fitted[skill])
    finally:
        os.unlink(path)


def test_learning_curve_rises():
    path = _synthetic_path()
    try:
        rows, _ = datasets.load_csv(path)
        curve = datasets.learning_curve(rows, "s2", max_attempt=10)
        assert len(curve) >= 5
        assert curve[-1] > curve[0], "practice should raise success rate"
    finally:
        os.unlink(path)


def _synthetic_junyi_paths(n_users=30, attempts=20):
    fd, log = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    fd, table = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    replay.make_synthetic_junyi_csv(log, table, TRUE_PARAMS,
                                    n_users=n_users, attempts=attempts, seed=2)
    return log, table


def test_junyi_loader_joins_exercises_to_skills():
    log, table = _synthetic_junyi_paths()
    try:
        rows, dropped, meta = datasets.load_junyi_problem_log(log, table)
        assert meta["skill_source"] == "kc_table"
        assert meta["columns"]["user"] == "uid"  # alias auto-detection
        assert dropped == {}
        assert {r["skill"] for r in rows} == {"s1", "s2"}
        assert datasets.summarize(rows)["users"] == 30
        fitted = replay.fit_top_skills(rows, 2)
        assert abs(fitted["s2"]["p_learn"] - TRUE_PARAMS["s2"]["p_learn"]) < 0.11
    finally:
        os.unlink(log)
        os.unlink(table)


def test_junyi_without_table_treats_exercise_as_skill():
    log, table = _synthetic_junyi_paths()
    try:
        rows, _, meta = datasets.load_junyi_problem_log(log)
        assert meta["skill_source"] == "exercise_id"
        assert {r["skill"] for r in rows} == {"e0", "e1"}
    finally:
        os.unlink(log)
        os.unlink(table)


def test_replay_deterministic_bounded_oracle_best():
    fitted = {k: dict(v) for k, v in TRUE_PARAMS.items()}
    a1 = replay.run_real_episode("A", fitted, seed=7, sessions=20)
    a2 = replay.run_real_episode("A", fitted, seed=7, sessions=20)
    assert a1["gains"] == a2["gains"]
    res = replay.run_real_experiment(fitted, seeds=range(30), sessions=20)
    for kind in ("A", "B", "O"):
        assert all(0.0 <= g <= 2 for g in res[kind]), kind
    assert res["O"][-1] >= res["B"][-1] - 0.05
    assert res["O"][-1] >= res["A"][-1] - 1e-9


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(tests)} tests passed")
