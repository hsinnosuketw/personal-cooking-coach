"""coach.perception.segments and .hsmm on tiny made-up inputs. Run: python3 tests/test_perception.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from coach.perception.hsmm import HSMMParams, hsmm_transitions, stable_changes
from coach.perception.segments import build_segments, doing_step, seg_line


def test_segments_smooth_merge_and_know_when_they_ended():
    labels = ["take egg"] * 4 + ["put phone"] * 3 + ["check phone"] * 3 + ["cut onion"] * 4
    segs = build_segments(labels, list(range(len(labels))), {"take egg": [0], "cut onion": [2]}, 1, 2, 3)
    assert [s["action"] for s in segs] == ["take egg", "put/check phone", "cut onion"]
    assert segs[0]["done_at"] == 4 and segs[1]["steps"] == [] and segs[2]["steps"] == [2]
    assert seg_line(segs[0]) == "0-4 s take egg (step 1)"
    assert doing_step(segs) in (0, 2)


def test_transitions_are_a_distribution_and_loops_jump_back():
    loop, plain = hsmm_transitions(3, [{"first": 0, "last": 1}], HSMMParams()), hsmm_transitions(3, [], HSMMParams())
    assert np.allclose(loop.sum(1), 1.0)
    end_of_step_2 = 1 * 4 + 3
    assert loop[end_of_step_2, 0] > plain[end_of_step_2, 0]   # the repeated run makes going back to step 1 likelier


def test_a_change_counts_once_it_holds():
    assert stable_changes(np.array([0, 0, 0, 1, 0, 1, 1, 1]), 3) == [(2, 0), (7, 1)]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
