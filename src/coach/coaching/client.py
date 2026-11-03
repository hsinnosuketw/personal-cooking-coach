"""Asking the coach (Muse Glimmer 30B) through an OpenAI-compatible endpoint: NVIDIA NIM, or vLLM on our own GPU.

The client objects are made by the caller (they need the API key), so this module can be tested with a fake.
"""
from __future__ import annotations

import time

GLIMMER = "meta/muse-glimmer-30b"
NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}, "reasoning_effort": "none"}
SELF_HOSTED = "Glimmer self-hosted, reasoning low, 1024 tok"


def coach_configs(self_hosted: bool = False) -> dict[str, dict]:
    """name -> model, max_tokens, extra request fields; all Muse Glimmer, varying reasoning and length.
    self_hosted: Glimmer is served on this machine (stage 14a, FP8 on an A100)."""
    configs = {
        "Glimmer, reasoning on, 8192 tok": dict(model=GLIMMER, max_tokens=8192),
        "Glimmer, reasoning on, 2048 tok": dict(model=GLIMMER, max_tokens=2048),
        "Glimmer, reasoning on, 1024 tok": dict(model=GLIMMER, max_tokens=1024),
        "Glimmer, reasoning low, 1024 tok": dict(model=GLIMMER, max_tokens=1024, extra={"reasoning_effort": "low"}),
        "Glimmer, reasoning off, 1024 tok": dict(model=GLIMMER, max_tokens=1024, extra=NO_THINKING),
        "Glimmer, reasoning off, 512 tok": dict(model=GLIMMER, max_tokens=512, extra=NO_THINKING),
    }
    if self_hosted:
        configs[SELF_HOSTED] = dict(model="glimmer", max_tokens=1024, local=True,
                                    extra={"chat_template_kwargs": {"reasoning_strength": "low"}, "skip_special_tokens": False})
    return configs


def split_reasoning(text: str) -> tuple[str, str]:
    """Self-hosted answers come as "<reasoning><|eom|><|start|>assistant to=user<|message|><answer>": (reasoning, answer)."""
    thinking, text = text.split("to=user<|message|>", 1)
    thinking = thinking.split("<|message|>", 1)[-1].replace("<|eom|>", "").replace("<|start|>assistant", "")
    return thinking, text.replace("<|eom|>", "").replace("<|end|>", "")


def ask(client, cfg: dict, prompt: str) -> tuple[str, str, float, dict]:
    """One answer, not streamed (NIM's streamed Glimmer answers came back empty): (answer, reasoning, seconds, usage)."""
    t0 = time.perf_counter()
    c = client.chat.completions.create(model=cfg["model"], messages=[{"role": "user", "content": prompt}],
                                       temperature=1, top_p=0.95, max_tokens=cfg["max_tokens"], stream=False,
                                       extra_body=cfg.get("extra") or None)
    m = c.choices[0].message
    thinking = getattr(m, "reasoning_content", None) or (m.model_extra or {}).get("reasoning_content") or ""
    text = m.content or ""
    if "to=user<|message|>" in text:
        thinking, text = split_reasoning(text)
    return text.strip(), thinking.strip(), time.perf_counter() - t0, c.usage.model_dump()
