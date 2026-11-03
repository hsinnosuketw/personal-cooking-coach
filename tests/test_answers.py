"""coach.coaching.answers on answers shaped like the coach's. Run: python3 tests/test_answers.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coach.coaching.answers import advice_text

HEADED = "Where:\nDone: step 3.\n\nNext:\nKeep plating; heat the pan next.\n\nDONE: 3\nSTEP: 7\nREMIND: none"


def test_heading_only_advice_takes_the_next_part():
    assert advice_text("Where:", HEADED) == "Keep plating; heat the pan next."


def test_parsed_advice_is_kept():
    assert advice_text("Heat the pan now, the onions need it.", HEADED) == "Heat the pan now, the onions need it."


def test_no_next_heading_keeps_what_was_parsed():
    assert advice_text("Where:", "Where:\nDone: step 3.") == "Where:"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
