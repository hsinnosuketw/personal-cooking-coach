"""coach.evaluation.{advice,omissions,starts,annotations} on tiny made-up runs. Run: python3 tests/test_evaluation.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from coach.evaluation import advice, annotations, omissions, starts

TRUTH = [[0, 10.0, 30.0], [1, 40.0, 60.0], [2, 70.0, 90.0]]


def test_finished_and_good_next():
    assert advice.finished_by(TRUTH, 35.0) == {0}
    assert advice.good_next(TRUTH, 3, 35.0) == {1}            # nothing on: the next one this cook did (= recipe order)
    assert advice.repeated_step([{"coach_step": 1}, {"coach_step": 1}, {"coach_step": 2}]) == 0.5


def test_a_skipped_step_reminded_after_it_was_due():
    run = {"omitted": 1, "truth": TRUTH, "ticks": [{"ledger": ["done", "not started", "in progress"]}],
           "calls": [{"ready": 30.0, "remind": 1}, {"ready": 52.0, "remind": 1}, {"ready": 80.0, "remind": 2}]}
    got = omissions.omission_scores(run)
    assert (got["delay (s)"], got["reminded (STEP or REMIND)"], got["REMIND naming other steps"]) == (12, "2x", 1)
    assert got["checklist marked it started"] is False


def test_fetching_does_not_start_a_step():
    steps_of = {"take pan": [1, 2], "crack egg": [0], "cut onion": [2]}
    assert starts.start_actions(steps_of, False, True) == {"crack egg": [0], "cut onion": [2]}
    probs = np.zeros((5, 3)); probs[2:, 1] = 0.5
    seen = starts.replay_starts({"crack egg": [0]}, range(5), probs, {"take pan": 0, "crack egg": 1, "cut onion": 2}, 0.25, 2)
    assert seen == {0: [3.0, 4.0]}


def test_mask_step_leaves_the_input_alone():
    p = {"t": np.arange(3), "action": np.ones((3, 4))}
    out = annotations.mask_step(p, [1, 2], floor=0.0)
    assert out["action"][:, 1:3].sum() == 0 and p["action"].sum() == 12


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
