"""coach.evaluation.goals on a tiny made-up run. Run: python3 tests/test_goals.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coach.evaluation.goals import memory_scores, reminder_scores

# step 0 starts at 10 s, step 1 at 40 s, step 2 never; the checklist marks 0 at 12 s and 1 at 20 s (20 s early)
RUN = {"steps": ["a", "b", "c"], "truth": [[0, 10.0, 30.0], [1, 40.0, 60.0]],
       "ticks": [{"t": float(t), "d1_step": 2,
                  "ledger": ["in progress" if t >= 12 else "not started", "in progress" if t >= 20 else "not started", "not started"]}
                 for t in range(0, 70)],
       "calls": [{"t": 25.0, "ready": 30.0, "coach_step": 1}, {"t": 50.0, "ready": 55.0, "coach_step": 1}]}


def test_memory_counts_lag_and_early_marks():
    m = memory_scores(RUN)
    assert m["remembered by the end"] == "2/2"
    assert m["median lag of the memory (s)"] == -9          # (+2 and -20) / 2
    assert m["remembered >10 s before it happened"] == 1
    assert m["steps never done but remembered"] == 0


def test_reminders_split_by_what_the_step_was_at_the_time():
    r = reminder_scores(RUN)
    assert r["coach → not started yet"] == 0.5              # step 1 at 30 s (starts at 40 s)
    assert r["coach → started, more to come"] == 0.5        # step 1 at 55 s (runs to 60 s)
    assert r["steps reminded before the cook started them"] == "1/1"
    assert r["never-done steps the coach named"] == "3: 0x"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
