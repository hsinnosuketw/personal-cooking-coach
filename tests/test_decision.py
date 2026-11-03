"""coach.decision.d1 on a made-up two-step recipe. Run: python3 tests/test_decision.py"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coach.decision import d1

STEPS = [SimpleNamespace(order=0, text="Crack the eggs", pairs=[("crack", "egg", 1.0)]),
         SimpleNamespace(order=1, text="Cut the onion", pairs=[("cut", "onion", 1.0), ("cut", "onion", 0.5)])]


def test_choices_questions_and_state():
    actions, steps = d1.d1_choices(STEPS, ["Crack the eggs", "Cut the onion"])
    assert list(actions) == ["s1_crack_egg", "s2_cut_onion"] and actions["s2_cut_onion"].endswith(": cut onion")
    qs = d1.d1_questions(actions, steps, skip_done=True, new_rounds=True)
    assert qs["next_step"]["instructions"].endswith(d1.SKIP_DONE + d1.NEW_ROUND)
    state = d1.with_checklist(d1.d1_state(12.4, 0, ["take egg"], "Crack them.", None),
                              {"steps": [{"status": "done"}, {"status": "not started"}]})
    assert state == {"time_s": 12, "tracker_step": 1, "predicted_next_actions": ["take egg"], "coach_advice": "Crack them.",
                     "checklist": {"done": [1], "in progress": [], "not started": [2]}}
    assert d1.best_action({"next_action": {"probabilities": {"s1_crack_egg": 0.2, "s2_cut_onion": 0.7}}}, actions) == ("cut onion", 1)


if __name__ == "__main__":
    test_choices_questions_and_state()
    print("ok")
