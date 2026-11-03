"""coach.coaching.answers on answers shaped like the coach's. Run: python3 tests/test_answers.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coach.coaching.answers import advice_text, parse_intent, parse_ledger, parse_look, parse_remind

HEADED = "Where:\nDone: step 3.\n\nNext:\nKeep plating; heat the pan next.\n\nDONE: 3\nSTEP: 7\nREMIND: none"


def test_heading_only_advice_takes_the_next_part():
    assert advice_text("Where:", HEADED) == "Keep plating; heat the pan next."


def test_parsed_advice_is_kept():
    assert advice_text("Heat the pan now, the onions need it.", HEADED) == "Heat the pan now, the onions need it."


def test_no_next_heading_keeps_what_was_parsed():
    assert advice_text("Where:", "Where:\nDone: step 3.") == "Where:"


def test_checklist_lines_become_0_based_steps():
    assert parse_ledger(HEADED, 7) is None   # no IN PROGRESS / LEFT lines
    full = "Next: x\nDONE: 1, 2\nIN PROGRESS: 3\nLEFT: 4-5\nSTEP: 3\nREMIND: 9\nLOOK: **4**"
    assert parse_ledger(full, 7) == {"DONE": [0, 1], "IN PROGRESS": [2], "LEFT": [3, 4], "STEP": [2]}
    assert parse_remind(full, 7) is None and parse_look(full, 7) == 3   # 9 is not a step of this recipe


def test_three_layer_answer():
    got = parse_intent("Now: sealing the disc.\nGoal: step 6.\nNext: roll it.\nDOING: 6", 15)
    assert got == {"now": "sealing the disc.", "goal": "step 6.", "doing": 5}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
