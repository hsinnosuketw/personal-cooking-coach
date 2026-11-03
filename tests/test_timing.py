"""coach.timing.adaptive on made-up ticks. Run: python3 tests/test_timing.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coach.timing.adaptive import AdaptiveTimer, TimingSettings

S = TimingSettings(min_gap_s=20, max_gap_s=80, wrap_every_s=180)
SEG = lambda steps, t0=0.0, t1=5.0: {"steps": steps, "t0": t0, "t1": t1}


def test_back_off_doubles_on_the_same_step_and_resets_on_another():
    timer, calls = AdaptiveTimer(4, {}, S), [{"t": t, "coach_step": k} for t, k in enumerate([1, 1, 1, 2])]
    gaps = []
    for c in calls[1:]:
        timer.back_off(c, calls)
        gaps.append(timer.gap)
    assert gaps == [40, 80, 20]
    timer.back_off(calls[3], calls)   # once per answer
    assert timer.gap == 20


def test_a_step_change_already_advised_is_suppressed():
    timer = AdaptiveTimer(4, {5: 2}, S)
    timer.observe(5, 2, [0, 0, 0.9, 0.1], advised=2)
    assert timer.reason(100.0, [], 0, ["in progress"] * 4, 2, advised=2) is None
    assert timer.suppressed["step change"] == 1


def test_forgotten_step_fires_once_per_step():
    timer, statuses = AdaptiveTimer(4, {}, S), ["not started", "in progress", "not started", "not started"]
    assert timer.reason(100.0, [SEG([2])], 1, statuses, 2, None) == "forgotten step"
    timer.asked(100.0, 10.0, 1, 2, statuses)
    assert timer.reason(200.0, [SEG([2])], 2, statuses, 2, None) is None


def test_wrap_up_on_the_last_step_at_most_every_180_s():
    timer, statuses = AdaptiveTimer(4, {}, S, wrap_up=True), ["done", "done", "not started", "in progress"]
    timer.reminded.update({2})
    assert timer.reason(100.0, [SEG([3])], 1, statuses, 3, None) == "steps left"
    timer.asked(100.0, 10.0, 1, 3, statuses)
    assert timer.reason(200.0, [SEG([3])], 2, statuses, 3, None) is None
    assert timer.reason(300.0, [SEG([3])], 3, statuses, 3, None) == "steps left"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
