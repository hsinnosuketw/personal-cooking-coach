"""Demo entry point.

  python3 demo.py benchmark        # A vs B vs Oracle curves + results.png
  python3 demo.py chat [--live]    # scripted conversation (--live voices
                                   #   the coach via Muse when MODEL_API_KEY
                                   #   is set, else offline templates)
  python3 demo.py make-synthetic out.csv [users] [attempts] [seed]
                                   # write ASSISTments-schema CSV from known
                                   # BKT params (offline pipeline check)
  python3 demo.py real-data data.csv [n_skills]
                                   # load -> fit BKT -> replay A/B/Oracle
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")

import numpy as np

from benchmark import ACTIONS, LearnerWorldModelCoach, TrueLearnerEnv, run_experiment
from conversation import (build_coach_prompt, coach_message,
                          extract_skills_offline, generate_coach_reply)


def benchmark_demo(seeds=range(40), sessions: int = 40) -> None:
    res = run_experiment(seeds=seeds, sessions=sessions)
    mean = {k: v.mean(axis=0) for k, v in res.items()}
    print(f"{'sess':>4} {'Bandit A':>9} {'World B':>9} {'Oracle':>9} {'B-A':>7}")
    for t in [2, 4, 6, 8, 10, 12, 15, 19, 24, 29, 39]:
        print(f"{t + 1:>4} {mean['A'][t]:>9.3f} {mean['B'][t]:>9.3f} "
              f"{mean['O'][t]:>9.3f} {mean['B'][t] - mean['A'][t]:>+7.3f}")
    early = float((res["B"][:, 2:9] - res["A"][:, 2:9]).mean())
    late = float((res["B"][:, 10:20] - res["A"][:, 10:20]).mean())
    print(f"\nSessions 3-9  mean B-A = {early:+.3f}  (bandit leads)")
    print(f"Sessions 11-20 mean B-A = {late:+.3f}  (world model leads)")
    print(f"Session 20: A={mean['A'][19]:.2f}  B={mean['B'][19]:.2f}  "
          f"Oracle={mean['O'][19]:.2f}")
    print(f"Session 40 (post-drift): A={mean['A'][39]:.2f}  B={mean['B'][39]:.2f}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.arange(1, sessions + 1)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for key, label in [("A", "Bandit A"), ("B", "World-Model B"), ("O", "Oracle")]:
        axes[0].plot(x, mean[key], label=label)
        lo = np.percentile(res[key], 25, axis=0)
        hi = np.percentile(res[key], 75, axis=0)
        axes[0].fill_between(x, lo, hi, alpha=0.15)
    axes[0].axvline(20.5, ls="--", c="grey")
    axes[0].annotate("stove drift", (21, axes[0].get_ylim()[0] + 0.05))
    axes[0].set_xlabel("session")
    axes[0].set_ylabel("cumulative true skill gain")
    axes[0].set_title("A leads early, B overtakes ~session 11")
    axes[0].legend()

    from benchmark import run_episode
    ep = run_episode("B", seed=7, sessions=sessions)
    axes[1].plot(x, ep["alpha_heat"], label="alpha_hat heat (B's estimate)")
    axes[1].axhline(0.14, ls=":", c="tab:blue", label="true alpha heat (pre-drift)")
    axes[1].axhline(0.055, ls=":", c="tab:red", label="true alpha heat (post-drift)")
    axes[1].plot(x, np.array(ep["gate_hat"]) / 40.0, label="gate_hat / 40 (scaled)")
    axes[1].axvline(20.5, ls="--", c="grey")
    axes[1].set_xlabel("session")
    axes[1].set_title("B learns the gate, then re-learns heat after drift")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("results.png", dpi=150)
    print("\nChart saved to results.png")
    _inside_figure(sessions)


def _inside_figure(sessions: int = 40) -> None:
    """What happens *inside* sessions: actions chosen, belief vs truth.

    Saved to results_inside.png: (1) per-session action strips for A/B/O
    on seed 7; (2) B's heat belief (mu +/- std) against the true heat
    skill; (3) true per-skill trajectories under B.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    from benchmark import ACTIONS, run_episode

    seed = 7
    eps = {k: run_episode(k, seed=seed, sessions=sessions) for k in ("A", "B", "O")}
    # Re-run B to capture per-session belief means (stored only as alpha/gate
    # traces, so replay beliefs via a fresh coached run).
    from benchmark import LearnerWorldModelCoach, TrueLearnerEnv
    env = TrueLearnerEnv(seed=seed, obs_noise=0.05)
    coach = LearnerWorldModelCoach(obs_noise=0.05)
    mus, sds, truths = [], [], []
    for t in range(1, sessions + 1):
        if t == 21:
            env.trigger_stove_drift()
        idx = coach.select_action()
        obs, _ = env.step(ACTIONS[idx])
        coach.update(idx, obs)
        import numpy as _np
        mus.append(coach.mu.copy())
        sds.append(_np.sqrt(coach.var))
        truths.append(env.true_skills.copy())
    mus = np.array(mus)
    sds = np.array(sds)
    truths = np.array(truths)

    palette = ["#1b7f7a", "#31a9a3", "#7fc8bc", "#f2c572", "#e4572e"]
    cmap = ListedColormap(palette)
    name_to_i = {a.name: i for i, a in enumerate(ACTIONS)}

    fig, axes = plt.subplots(3, 1, figsize=(11, 8),
                             gridspec_kw={"height_ratios": [1, 1.4, 1.4]})
    x = np.arange(1, sessions + 1)
    for row, kind in enumerate(["A", "B", "O"]):
        seq = np.array([[name_to_i[a]] for a in eps[kind]["actions"]]).T
        axes[0].imshow(seq, aspect="auto", cmap=cmap, extent=[0.5, sessions + 0.5, 2.5 - row, 3.5 - row])
    axes[0].set_yticks([1, 2, 3])
    axes[0].set_yticklabels(["Oracle", "World B", "Bandit A"])
    axes[0].set_xlim(0.5, sessions + 0.5)
    axes[0].set_title("Seed 7: action chosen each session (teal=drills, gold=easy, red=stretch)")
    axes[0].axvline(20.5, ls="--", c="grey")

    axes[1].plot(x, truths[:, 1], c="black", lw=2, label="true heat skill")
    axes[1].plot(x, mus[:, 1], c="#e4572e", label="B belief mu heat")
    axes[1].fill_between(x, mus[:, 1] - sds[:, 1], mus[:, 1] + sds[:, 1],
                         color="#e4572e", alpha=0.2, label="B ±1 std")
    axes[1].axvline(20.5, ls="--", c="grey")
    axes[1].set_ylabel("heat skill")
    axes[1].set_title("B's heat belief vs truth (seed 7): early overestimate, drift re-learned")
    axes[1].legend(fontsize=8)

    for k, skill in enumerate(["knife", "heat", "timing"]):
        axes[2].plot(x, truths[:, k], label=f"true {skill}")
    axes[2].axvline(20.5, ls="--", c="grey")
    axes[2].set_xlabel("session")
    axes[2].set_ylabel("skill")
    axes[2].set_title("True skill trajectories under Coach B (seed 7)")
    axes[2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("results_inside.png", dpi=150)
    print("Chart saved to results_inside.png")


_REPORTS = [
    "My onions browned way too fast and burned before the garlic was even chopped.",
    "Heat felt calmer today, but my cuts are still uneven.",
    "The pan stayed steady and nothing burned - timing was still rushed at the end.",
    "Everything landed together and the heat was smooth. Felt great.",
    "New stove is weird - the pan got too hot fast and smoked again.",
    "Getting used to the stove. Cuts were even and timing felt smooth.",
]


def chat_demo(live: bool = False) -> None:
    """Scripted multi-session loop: report -> obs -> update -> plan -> prompt."""
    env = TrueLearnerEnv(seed=7, obs_noise=0.05)
    coach = LearnerWorldModelCoach(obs_noise=0.05)
    for t, report in enumerate(_REPORTS, start=1):
        if t == 5:
            env.trigger_stove_drift()
            print("\n--- learner got a new stove (drift) ---\n")
        idx = coach.select_action(horizon=2)
        action = ACTIONS[idx]
        system_prompt = build_coach_prompt(coach)
        print(f"[Session {t}] Coach plan: {action.name}")
        print(f"  System prompt: {system_prompt}")
        if live:
            reply, is_live = generate_coach_reply(system_prompt,
                                                 coach_message(action.name))
            tag = "[live Muse]" if is_live else "[offline template]"
            print(f"  Coach {tag}: {reply}")
        else:
            print(f"  Coach: {coach_message(action.name)}")
        obs, _ = env.step(action)
        coach.update(idx, obs)
        obs_from_text = extract_skills_offline(report)
        print(f"  Learner: \"{report}\"")
        print(f"  Extractor(obs from text): {np.round(obs_from_text, 2)}  "
              f"belief mu: {np.round(coach.mu, 2)}  "
              f"alpha_hat: {np.round(coach.alpha_hat, 2)}  "
              f"gate_hat: {coach.gate_hat:.1f}\n")


def real_data_demo(path: str, n_skills: int = 3, sessions: int = 20) -> None:
    """ASSISTments-format CSV -> fit BKT -> replay A/B/Oracle -> report."""
    import datasets
    import replay

    rows, dropped = datasets.load_csv(path)
    info = datasets.summarize(rows)
    print(f"Loaded {info['attempts']} attempts from {info['users']} users, "
          f"{info['skills']} skills (base rate {info['base_rate']:.3f}); "
          f"dropped rows: {dropped or 'none'}")
    params_map = replay.fit_top_skills(rows, n_skills)
    for skill, p in params_map.items():
        curve = datasets.learning_curve(rows, skill, max_attempt=10)
        shown = " ".join(f"{v:.2f}" for v in curve[:10])
        print(f"  {skill}: p_init={p['p_init']:.2f} p_learn={p['p_learn']:.2f} "
              f"p_guess={p['p_guess']:.2f} p_slip={p['p_slip']:.2f} "
              f"(n_seq={p['n_seq']})  curve[{shown}]")
    res = replay.run_real_experiment(params_map, sessions=sessions)
    print(f"\n{'sess':>4} {'Bandit A':>9} {'World B':>9} {'Oracle':>9} {'B-A':>7}")
    for t in [4, 9, 14, 19][:sessions]:
        print(f"{t + 1:>4} {res['A'][t]:>9.3f} {res['B'][t]:>9.3f} "
              f"{res['O'][t]:>9.3f} {res['B'][t] - res['A'][t]:>+7.3f}")
    final_a, final_b = res["A"][-1], res["B"][-1]
    print(f"\nSession {sessions}: A={final_a:.2f} B={final_b:.2f} "
          f"O={res['O'][-1]:.2f}  (B-A={final_b - final_a:+.3f})")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "benchmark"
    if mode == "chat":
        chat_demo(live="--live" in sys.argv)
    elif mode == "make-synthetic":
        import replay as _replay

        out = sys.argv[2]
        users = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        attempts = int(sys.argv[4]) if len(sys.argv) > 4 else 25
        seed = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        _replay.make_synthetic_csv(
            out,
            {"s1": {"p_init": 0.3, "p_learn": 0.15, "p_guess": 0.2, "p_slip": 0.15},
             "s2": {"p_init": 0.1, "p_learn": 0.30, "p_guess": 0.2, "p_slip": 0.1},
             "s3": {"p_init": 0.5, "p_learn": 0.10, "p_guess": 0.25, "p_slip": 0.1}},
            n_users=users, attempts=attempts, seed=seed)
        print(f"Wrote synthetic ASSISTments-schema CSV to {out}")
    elif mode == "real-data":
        real_data_demo(sys.argv[2],
                       int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    else:
        benchmark_demo()
