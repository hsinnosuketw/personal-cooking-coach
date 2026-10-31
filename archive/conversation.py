"""Bridges between natural-language sessions and the world model.

Bridge 1 (Conversation -> obs_skills): turn a learner's free-text report
into the noisy observation vector the world model consumes.
  * Default: deterministic offline keyword extractor (no key needed).
  * Live: Meta Model API (Muse Spark) structured extraction when
    MODEL_API_KEY is set. Base URL https://api.meta.ai/v1 (OpenAI-compatible).

Bridge 2 (select_action -> system prompt): inject the belief state and
the 2-step plan into the LLM coach's system prompt so the conversation
follows the world model's decision instead of the LLM guessing.
"""
from __future__ import annotations

import json
import os
import urllib.request

import numpy as np

from benchmark import ACTIONS, SKILLS, LearnerWorldModelCoach

BASELINE = np.array([0.40, 0.40, 0.40])

_CUES = {
    0: (["knife", "chop", "slice", "diced", "uneven cuts"], 0.18),
    1: (["burn", "smoke", "too hot", "browned too fast", "heat"], 0.20),
    2: (["timing", "too late", "waited", "rushed", "before the garlic"], 0.16),
}
_GOOD = ["well", "great", "perfect", "nailed", "smooth", "evenly"]


def extract_skills_offline(text: str) -> np.ndarray:
    """Deterministic fallback extractor: problems lower the matching skill."""
    obs = BASELINE.copy()
    low = text.lower()
    positive = any(w in low for w in _GOOD)
    for k, (words, drop) in _CUES.items():
        if any(w in low for w in words):
            obs[k] += 0.12 if positive else -drop
    return np.clip(obs, 0.0, 1.0)


def _post_chat(messages: list[dict], model: str = "muse-spark-1.3") -> str:
    """One Meta Model API chat call. Raises on missing key or any failure."""
    key = os.environ.get("MODEL_API_KEY")
    if not key:
        raise RuntimeError("MODEL_API_KEY is not set")
    body = json.dumps({"model": model, "messages": messages}).encode()
    req = urllib.request.Request(
        "https://api.meta.ai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def extract_skills_llm(text: str, model: str = "muse-spark-1.3") -> np.ndarray:
    """Live extractor via Meta Model API; falls back to offline on any error."""
    prompt = (
        "Estimate the learner's current cooking skills from their report. "
        f"Skills: {SKILLS}, each in [0,1]. Report: {text!r}. "
        'Reply with ONLY JSON like {"knife": 0.6, "heat": 0.2, "timing": 0.3}.'
    )
    try:
        content = _post_chat([{"role": "user", "content": prompt}], model)
        parsed = json.loads(content[content.index("{"):content.rindex("}") + 1])
        return np.clip([float(parsed[s]) for s in SKILLS], 0.0, 1.0)
    except Exception:
        return extract_skills_offline(text)


def generate_coach_reply(system_prompt: str, fallback_line: str,
                         model: str = "muse-spark-1.3") -> tuple[str, bool]:
    """Voice the world model's plan through Muse. Returns (text, live_flag).

    Without MODEL_API_KEY (or on any API failure) returns the offline
    template line with live_flag False, so demos never die on stage.
    """
    try:
        text = _post_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Coach this session in 2-3 sentences."},
        ], model)
        return text.strip(), True
    except Exception:
        return fallback_line, False


def build_coach_prompt(coach: LearnerWorldModelCoach) -> str:
    """Bridge 2: belief state + lookahead plan as an LLM system prompt."""
    idx = coach.select_action(horizon=2)
    plan = coach.planned_sequence(horizon=2)
    belief = ", ".join(
        f"{s} {m:.2f} ± {np.sqrt(v):.2f}"
        for s, m, v in zip(SKILLS, coach.mu, coach.var))
    alpha = ", ".join(f"{s}={a:.2f}" for s, a in zip(SKILLS, coach.alpha_hat))
    return (
        f"Current Learner Belief State: {belief}. "
        f"Estimated learning rates: {alpha}. "
        f"Prerequisite-gate estimate: {coach.gate_hat:.1f} (0 = not yet learned). "
        f"Optimal 2-Step Plan: run `{ACTIONS[idx].name}` now, then `{plan[-1]}`. "
        f"Guide the learner through {ACTIONS[idx].name.replace('_', ' ')} this "
        "session. Do not jump ahead to the second step until the prerequisite "
        "skill crosses its threshold."
    )


_TEMPLATES = {
    "knife_drill": "Today: knife drill. Slow, even cuts - accuracy before speed.",
    "heat_drill": "Today: pan-temperature control drill. Hold a steady medium heat; watch the oil shimmer, not smoke.",
    "timing_drill": "Today: timing drill. Stage ingredients so everything lands together.",
    "easy_recipe": "Today: an easy recipe that combines all three skills gently.",
    "stretch_recipe": "Today: a stretch recipe combining all three skills.",
}


def coach_message(action_name: str) -> str:
    return _TEMPLATES.get(action_name, f"Today: {action_name.replace('_', ' ')}.")
