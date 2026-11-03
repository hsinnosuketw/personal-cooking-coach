"""coach.memory.checklist on tiny made-up evidence. Run: python3 tests/test_memory.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coach.memory import checklist as mem

NAMES, STEPS_OF = ["crack egg", "cut onion"], {"crack egg": [0], "cut onion": [2]}


def test_rule_needs_a_streak_and_marks_the_step_started():
    ledger = mem.new_ledger(3)
    assert mem.rule_update(ledger, 1.0, [0.3, 0.0], NAMES, STEPS_OF, 0.25, 2) == []
    assert ledger["steps"][0]["status"] == "not started"
    assert mem.rule_update(ledger, 2.0, [0.3, 0.0], NAMES, STEPS_OF, 0.25, 2) == ["crack egg"]
    assert ledger["steps"][0] == {"status": "in progress", "t": 2.0, "by": "rule"}
    assert ledger["seen"]["crack egg"] == [2.0, 2.0, 1]


def test_coach_cannot_move_a_step_back_when_monotonic():
    ledger = mem.new_ledger(3)
    ledger["steps"][2]["status"] = "in progress"
    mem.apply_coach(ledger, {"DONE": [0], "IN PROGRESS": [], "LEFT": [1, 2], "STEP": [1]}, 100.0, monotonic=True)
    assert [s["status"] for s in ledger["steps"]] == ["done", "not started", "in progress"]


def test_order_rule_spares_the_advised_step():
    ledger = mem.new_ledger(3)
    for k in (0, 1):
        ledger["steps"][k]["status"] = "in progress"
    mem.infer_order(ledger, {2: 3}, 50.0, min_segments=3, coach_step=1)
    assert [s["status"] for s in ledger["steps"]] == ["done", "in progress", "not started"]


def test_a_finished_loop_step_reopens_after_new_segments():
    ledger = mem.new_loop_ledger(3)
    mem.set_status(ledger, 1, "done", 10.0, "coach")
    seg = {"steps": [1]}
    assert mem.reopen_loops(ledger, seg, 20.0, {1: 0}, 2) == []
    assert mem.reopen_loops(ledger, seg, 30.0, {1: 0}, 2) == [1]
    assert mem.loop_status(ledger["steps"][1]) == "in progress, round 2"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
