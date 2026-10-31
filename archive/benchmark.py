"""Toy benchmark: multi-session coaching as a POMDP.

Implements the exact mechanics from the project spec:
  s_{t+1,k} = s_{t,k} + alpha*_k * w_{a,k} * g(s_t, a) * (1 - s_{t,k})
  g(s, a)   = exp(-GATE_K * sum_k max(0, prereq_{a,k} - s_k))
  o_t       = clip(s_{t+1} + N(0, obs_noise^2))

Two coaches get identical copies of the same simulated learner:
  A: Model-free bandit (UCB over per-action average session score)
  B: Learner world model (Kalman belief + learned dynamics + 2-step lookahead)
Plus an omniscient Oracle reference that plans on the true dynamics.

Declared modelling choices (see README for rationale):
  * Learning rates are scaled x~0.55 vs the video so skills do not saturate
    before session 11; otherwise no crossover can exist.
  * Coach B starts misspecified: it initially ignores prerequisites
    (gate_hat = 0) and must learn the gate from prediction error. This is
    the cost that lets the bandit lead sessions ~3-9.
  * The bandit reward is the simulator-provided session score jump,
    matching the spec's "high initial score jump" wording.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SKILLS = ["knife", "heat", "timing"]
GATE_K = 6.0  # true prerequisite-gate strength in the environment


@dataclass(frozen=True)
class Action:
    name: str
    weights: np.ndarray
    min_prereq: np.ndarray


ACTIONS = [
    Action("knife_drill", np.array([1.0, 0.0, 0.1]), np.array([0.0, 0.0, 0.0])),
    Action("heat_drill", np.array([0.0, 1.0, 0.2]), np.array([0.0, 0.0, 0.0])),
    Action("timing_drill", np.array([0.1, 0.1, 1.0]), np.array([0.0, 0.0, 0.0])),
    Action("easy_recipe", np.array([0.5, 0.5, 0.5]), np.array([0.2, 0.2, 0.2])),
    Action("stretch_recipe", np.array([0.9, 0.9, 0.9]), np.array([0.5, 0.45, 0.4])),
]
ACTION_NAMES = [a.name for a in ACTIONS]

# Named learner archetypes: (initial skills, learning rates, observation noise).
# "steady" reproduces the default Seed-7 behavior; the others vary learning
# speed and noise so claims about slow/noisy learners can be tested honestly.
ARCHETYPES = {
    "steady": {"initial": [0.65, 0.15, 0.35], "alpha": [0.11, 0.14, 0.12], "noise": 0.05},
    "fast": {"initial": [0.50, 0.30, 0.40], "alpha": [0.14, 0.17, 0.15], "noise": 0.05},
    "slow": {"initial": [0.60, 0.10, 0.30], "alpha": [0.07, 0.09, 0.08], "noise": 0.05},
    "noisy": {"initial": [0.65, 0.15, 0.35], "alpha": [0.11, 0.14, 0.12], "noise": 0.12},
}


def gate(skill: np.ndarray, action: Action, k: float) -> float:
    shortfall = np.maximum(0.0, action.min_prereq - skill)
    return float(np.exp(-k * np.sum(shortfall)))


class TrueLearnerEnv:
    """Ground-truth learner. Coaches never see `true_skills` directly."""

    def __init__(self, seed: int = 7, obs_noise: float = 0.05,
                 initial_skills: np.ndarray | None = None,
                 true_alpha: np.ndarray | None = None,
                 forget_rate: float = 0.0):
        self.rng = np.random.default_rng(seed)
        self.obs_noise = obs_noise
        self.forget_rate = float(forget_rate)
        # Default archetype: Seed 7, "strong knife, weak heat".
        self.initial_skills = (np.array([0.65, 0.15, 0.35])
                               if initial_skills is None else initial_skills.copy())
        self.true_skills = self.initial_skills.copy()
        self.true_alpha = (np.array([0.11, 0.14, 0.12])
                           if true_alpha is None else true_alpha.copy())
        self.session = 0

    def trigger_stove_drift(self) -> None:
        """New stove after session 20: heat skill and heat rate drop."""
        self.true_skills[1] *= 0.65
        self.true_alpha[1] = 0.055

    def step(self, action: Action) -> tuple[np.ndarray, float]:
        self.session += 1
        prev = self.true_skills.copy()
        delta = (self.true_alpha * action.weights
                 * gate(self.true_skills, action, GATE_K) * (1.0 - self.true_skills))
        self.true_skills = np.clip(self.true_skills + delta, 0.0, 1.0)
        if self.forget_rate > 0.0:
            # Toy forgetting: skills decay toward their starting values.
            self.true_skills = np.clip(
                self.true_skills + (self.initial_skills - self.true_skills)
                * self.forget_rate, 0.0, 1.0)
        obs = np.clip(self.true_skills + self.rng.normal(0, self.obs_noise, 3), 0.0, 1.0)
        return obs, float(np.sum(obs - prev))

    @property
    def cumulative_true_gain(self) -> float:
        return float(np.sum(self.true_skills - self.initial_skills))


class ModelFreeBanditCoach:
    """Coach A: stateless UCB over average session score per action."""

    def __init__(self, c_explore: float = 0.06, q_init: float = 0.22):
        self.counts = np.zeros(len(ACTIONS))
        self.q_values = np.full(len(ACTIONS), q_init)
        self.c = c_explore
        self.t = 0

    def select_action(self) -> int:
        self.t += 1
        ucb = self.q_values + self.c * np.sqrt(np.log(self.t + 1) / (self.counts + 1e-9))
        return int(np.argmax(ucb))

    def update(self, action_idx: int, obs_skills: np.ndarray, score: float) -> None:
        self.counts[action_idx] += 1
        n = self.counts[action_idx]
        self.q_values[action_idx] += (score - self.q_values[action_idx]) / n


class LearnerWorldModelCoach:
    """Coach B: belief b(s)=N(mu,var) + learned dynamics + 2-step lookahead.

    Starts misspecified (gate_hat=0: ignores prerequisites), learns the
    gate strength from prediction error on compound actions, learns each
    skill's learning rate alpha_hat online, and re-plans every session.
    """

    def __init__(self, obs_noise: float = 0.05, ema: float = 0.25, gate_lr: float = 1.2):
        self.mu = np.array([0.40, 0.40, 0.40])
        self.var = np.array([0.05, 0.05, 0.05])
        self.alpha_hat = np.array([0.12, 0.12, 0.12])
        self.obs_var = obs_noise ** 2
        self.ema = ema
        self.gate_hat = 0.0
        self.gate_lr = gate_lr

    def predict_next(self, mu, var, action):
        g = gate(mu, action, self.gate_hat)
        nxt = np.clip(mu + self.alpha_hat * action.weights * g * (1.0 - mu), 0.0, 1.0)
        return nxt, var + 0.002

    def select_action(self, horizon: int = 2) -> int:
        best_score, best_idx = -np.inf, 0
        for i, a1 in enumerate(ACTIONS):
            mu1, var1 = self.predict_next(self.mu, self.var, a1)
            score = float(np.sum(mu1 - self.mu))
            if horizon >= 2:
                score += 0.9 * max(
                    float(np.sum(self.predict_next(mu1, var1, a2)[0] - mu1))
                    for a2 in ACTIONS)
            if score > best_score:
                best_score, best_idx = score, i
        return best_idx

    def planned_sequence(self, horizon: int = 2) -> list[str]:
        """Greedy action sequence under the current belief (for display/LLM)."""
        mu, var, seq = self.mu.copy(), self.var.copy(), []
        for _ in range(horizon):
            gains = [float(np.sum(self.predict_next(mu, var, a)[0] - mu)) for a in ACTIONS]
            i = int(np.argmax(gains))
            seq.append(ACTIONS[i].name)
            mu, var = self.predict_next(mu, var, ACTIONS[i])
        return seq

    def update(self, action_idx: int, obs_skills: np.ndarray, score: float = 0.0) -> None:
        action = ACTIONS[action_idx]
        prev_mu = self.mu.copy()
        pred_mu, pred_var = self.predict_next(self.mu, self.var, action)
        pred_gain = float(np.sum(pred_mu - prev_mu))
        innovation = obs_skills - pred_mu
        if np.any(np.abs(innovation) > 0.12):  # drift / surprise: trust obs more
            pred_var = pred_var + 0.03
        k_gain = pred_var / (pred_var + self.obs_var)
        self.mu = np.clip(pred_mu + k_gain * innovation, 0.0, 1.0)
        self.var = (1.0 - k_gain) * pred_var
        realized = float(np.sum(self.mu - prev_mu))
        if np.sum(action.min_prereq) > 0 and pred_gain > 0.03:
            miss = float(np.clip(1.0 - realized / max(pred_gain, 1e-9), 0.0, 1.0))
            self.gate_hat = float(np.clip(self.gate_hat + self.gate_lr * miss, 0.0, 8.0))
        denom = action.weights * gate(prev_mu, action, self.gate_hat) * (1.0 - prev_mu)
        for k in range(3):
            if denom[k] > 0.05:
                est = float(np.clip((self.mu[k] - prev_mu[k]) / denom[k], 0.02, 0.50))
                self.alpha_hat[k] = (1 - self.ema) * self.alpha_hat[k] + self.ema * est


class OracleCoach:
    """Omniscient reference: plans on the true skills and true alphas."""

    def __init__(self, env: TrueLearnerEnv):
        self.env = env

    def select_action(self) -> int:
        s, alpha = self.env.true_skills, self.env.true_alpha

        def nxt(state, a):
            return np.clip(state + alpha * a.weights * gate(state, a, GATE_K)
                           * (1.0 - state), 0.0, 1.0)

        best_score, best_idx = -np.inf, 0
        for i, a1 in enumerate(ACTIONS):
            s1 = nxt(s, a1)
            score = float(np.sum(s1 - s)) + 0.9 * max(
                float(np.sum(nxt(s1, a2) - s1)) for a2 in ACTIONS)
            if score > best_score:
                best_score, best_idx = score, i
        return best_idx

    def update(self, action_idx: int, obs_skills: np.ndarray, score: float = 0.0) -> None:
        pass


def _resolve_archetype(archetype: str | dict | None) -> dict:
    if archetype is None:
        return {"initial": None, "alpha": None, "noise": None}
    if isinstance(archetype, str):
        if archetype not in ARCHETYPES:
            raise ValueError(f"unknown archetype {archetype!r}; choose from {sorted(ARCHETYPES)}")
        return ARCHETYPES[archetype]
    return archetype


def run_episode(coach_kind: str, seed: int, sessions: int = 40,
                drift_at: int | None = 20, obs_noise: float = 0.05,
                archetype: str | dict | None = None,
                forget_rate: float = 0.0) -> dict:
    """Run one learner under one coach; drift fires after session `drift_at`.

    `archetype` selects a named learner profile (see ARCHETYPES) or a dict
    with "initial"/"alpha"/"noise" keys. `forget_rate` enables toy
    forgetting (skills decay toward starting values each session).
    Defaults reproduce the original Seed-7 behavior exactly.
    """
    arch = _resolve_archetype(archetype)
    env = TrueLearnerEnv(
        seed=seed,
        obs_noise=arch["noise"] if arch["noise"] is not None else obs_noise,
        initial_skills=(None if arch["initial"] is None
                        else np.array(arch["initial"])),
        true_alpha=(None if arch["alpha"] is None
                    else np.array(arch["alpha"])),
        forget_rate=forget_rate,
    )
    if coach_kind == "A":
        coach = ModelFreeBanditCoach()
    elif coach_kind == "B":
        coach = LearnerWorldModelCoach(obs_noise=obs_noise)
    elif coach_kind == "O":
        coach = OracleCoach(env)
    else:
        raise ValueError(f"unknown coach {coach_kind!r}")
    gains, actions = [], []
    alpha_heat, gate_hat = [], []
    for t in range(1, sessions + 1):
        if drift_at is not None and t == drift_at + 1:
            env.trigger_stove_drift()
        idx = coach.select_action()
        obs, score = env.step(ACTIONS[idx])
        coach.update(idx, obs, score)
        gains.append(env.cumulative_true_gain)
        actions.append(ACTIONS[idx].name)
        if isinstance(coach, LearnerWorldModelCoach):
            alpha_heat.append(float(coach.alpha_hat[1]))
            gate_hat.append(float(coach.gate_hat))
    return {"gains": np.array(gains), "actions": actions,
            "alpha_heat": np.array(alpha_heat), "gate_hat": np.array(gate_hat)}


def run_experiment(seeds=range(40), sessions: int = 40) -> dict:
    """Mean cumulative true gain per session for A, B and Oracle."""
    out = {}
    for kind in ("A", "B", "O"):
        runs = [run_episode(kind, s, sessions=sessions)["gains"] for s in seeds]
        out[kind] = np.array(runs)
    return out

