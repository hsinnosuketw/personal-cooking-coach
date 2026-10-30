"""Focused checks for the toy benchmark. Run: python3 test_benchmark.py"""
import numpy as np

from benchmark import (ACTIONS, LearnerWorldModelCoach, TrueLearnerEnv,
                       run_episode, run_experiment)
from conversation import (build_coach_prompt, extract_skills_offline,
                          generate_coach_reply)


def test_reproducible_same_seed():
    a = run_episode("B", seed=7)["gains"]
    b = run_episode("B", seed=7)["gains"]
    assert np.allclose(a, b)


def test_env_gain_bounded():
    env = TrueLearnerEnv(seed=1)
    for _ in range(40):
        env.step(ACTIONS[4])
    assert 0.0 <= env.cumulative_true_gain <= 1.85


def test_crossover_windows():
    res = run_experiment(seeds=range(40), sessions=40)
    early = float((res["B"][:, 2:9] - res["A"][:, 2:9]).mean())
    late = float((res["B"][:, 10:20] - res["A"][:, 10:20]).mean())
    assert early < 0, f"expected bandit lead in sessions 3-9, got B-A={early:+.3f}"
    assert late > 0, f"expected world-model lead in sessions 11-20, got B-A={late:+.3f}"


def test_gate_is_learned():
    coach = LearnerWorldModelCoach()
    assert coach.gate_hat == 0.0
    ep = run_episode("B", seed=7)
    assert ep["gate_hat"][-1] > 3.0, "gate_hat should approach true 6.0"


def test_drift_adaptation():
    ep = run_episode("B", seed=7, sessions=40)
    pre = float(np.mean(ep["alpha_heat"][17:20]))
    post = float(np.mean(ep["alpha_heat"][36:40]))
    assert post < pre, f"alpha_hat heat should fall after drift: {pre:.3f} -> {post:.3f}"


def test_oracle_bounds_both_coaches():
    res = run_experiment(seeds=range(10), sessions=20)
    assert res["O"][:, 19].mean() >= res["B"][:, 19].mean() - 0.05
    assert res["O"][:, 19].mean() >= res["A"][:, 19].mean()


def test_conversation_bridges():
    obs = extract_skills_offline("it burned and smoked, way too hot")
    assert obs[1] < 0.40  # heat problem lowers heat estimate
    coach = LearnerWorldModelCoach()
    prompt = build_coach_prompt(coach)
    assert "Belief State" in prompt and "2-Step Plan" in prompt


def test_coach_voice_falls_back_offline():
    import os
    os.environ.pop("MODEL_API_KEY", None)
    text, live = generate_coach_reply("system prompt", "fallback line")
    assert text == "fallback line" and live is False


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(tests)} tests passed")
