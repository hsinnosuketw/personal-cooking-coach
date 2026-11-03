"""coach.coaching.client with a fake OpenAI-style client. Run: python3 tests/test_client.py"""
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coach.coaching.client import SELF_HOSTED, ask, coach_configs


class Fake:
    def __init__(self, content, reasoning=None):
        msg = NS(content=content, reasoning_content=reasoning, model_extra={})
        reply = NS(choices=[NS(message=msg)], usage=NS(model_dump=lambda: {"prompt_tokens": 3}))
        self.sent = []
        self.chat = NS(completions=NS(create=lambda **kw: self.sent.append(kw) or reply))


def test_nim_answer_and_reasoning():
    fake = Fake(" Next: crack the eggs. ", "eggs first")
    text, thinking, sec, usage = ask(fake, coach_configs()["Glimmer, reasoning low, 1024 tok"], "p")
    assert (text, thinking, usage) == ("Next: crack the eggs.", "eggs first", {"prompt_tokens": 3})
    assert fake.sent[0]["extra_body"] == {"reasoning_effort": "low"} and fake.sent[0]["stream"] is False


def test_self_hosted_answer_is_split_from_its_reasoning():
    raw = "<|channel|>analysis<|message|>think<|eom|><|start|>assistant to=user<|message|>Next: oil the pan.<|end|>"
    text, thinking, _, _ = ask(Fake(raw), coach_configs(self_hosted=True)[SELF_HOSTED], "p")
    assert (text, thinking) == ("Next: oil the pan.", "think")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
