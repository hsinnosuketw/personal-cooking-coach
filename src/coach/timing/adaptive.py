"""When to ask the coach (stage 31): on events, with a back-off when the coach keeps saying the same thing.

Events, checked once per tick and only when the coach is free and at least min_gap_s after the last question:
- steps left: the cook is on the last step while some steps show no sign yet (wrap_up, at most every wrap_every_s);
- forgotten step: a later step's segment closed while an earlier step has no sign (once per step);
- off task: off_task_s of segments outside the recipe;
- step change: the HSMM moved to another step with confidence >= change_conf and held it (skipped if the advice on
  screen is already about that step);
- off advice: the HSMM has been off the step the advice named for deviation_s seconds;
- N actions: fallback_n new segments, unless the step and checklist are as they were at the last question.
The first three ignore the back-off; the rest wait until `gap` seconds have passed. Each answer that names the same
STEP as the one before doubles the gap (up to max_gap); a different STEP resets it to min_gap_s.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimingSettings:
    fallback_n: int = 10       # without a step change, still advise after this many actions (stage 26's N = 10)
    deviation_s: int = 60      # the HSMM step differs from the step the advice named for this many seconds in a row
    change_conf: float = 0.6   # a step change only counts if the HSMM gives the new step at least this probability
    wrap_every_s: float = 180  # the wrap-up check repeats at most this often
    max_gap_s: float = 160     # the back-off's longest quiet time
    min_gap_s: float = 20.0    # never ask more often than this
    off_task_s: float = 60.0   # seconds of non-recipe segments that count as off task


class AdaptiveTimer:
    """The timing state of one run. Call, per tick: segment_closed() for each segment that ended, observe(),
    back_off(), then reason(); after asking, asked()."""

    def __init__(self, n_steps: int, changes: dict[int, int], s: TimingSettings, wrap_up: bool = False,
                 max_gap: float | None = None):
        self.n, self.changes, self.s, self.wrap_up = n_steps, changes, s, wrap_up
        self.max_gap = max_gap or s.max_gap_s
        self.free_at, self.last_ask, self.used, self.off_since = -1.0, -1e9, 0, 0.0
        self.reminded: set[int] = set()
        self.want, self.off_advice, self.snapshot = None, 0, (None, None)
        self.gap, self.wrapped_at = s.min_gap_s, -1e9
        self.suppressed = {"step change": 0, "N actions": 0}

    def segment_closed(self, seg: dict) -> None:
        if not seg["steps"]:
            self.off_since += seg["t1"] - seg["t0"]

    def observe(self, i: int, hsmm: int, post_i, advised: int | None) -> None:
        """The HSMM's step at tick i (post_i: its posterior) against the step the advice on screen names."""
        if i in self.changes and post_i[self.changes[i]] >= self.s.change_conf:
            self.want = self.changes[i]
        elif self.want is not None and hsmm != self.want:
            self.want = None                         # the change didn't hold
        self.off_advice = self.off_advice + 1 if advised is not None and hsmm != advised else 0

    def back_off(self, visible: dict | None, calls: list[dict]) -> None:
        """Once per answer, when it reaches the screen: same STEP as the answer before doubles the gap."""
        if visible and calls.index(visible) > 0 and visible.get("gap_set") is None:
            before = calls[calls.index(visible) - 1].get("coach_step")
            same = visible.get("coach_step") is not None and visible["coach_step"] == before
            self.gap = min(self.max_gap, self.gap * 2) if same else self.s.min_gap_s
            visible["gap_set"] = self.gap

    def reason(self, tt: float, closed: list[dict], n_done: int, statuses: list[str], hsmm: int,
               advised: int | None) -> str | None:
        """Why to ask the coach at time tt, or None. n_done: segments closed so far; statuses: the checklist."""
        if not (tt >= self.free_at and tt - self.last_ask >= self.s.min_gap_s):
            return None
        later = [k for s in closed for k in s["steps"]]
        forgot = [j for k in later for j in range(k) if statuses[j] == "not started" and j not in self.reminded]
        final = self.n - 1
        untouched = [k for k, st in enumerate(statuses) if st == "not started"]
        if (self.wrap_up and tt - self.wrapped_at >= self.s.wrap_every_s and untouched and len(untouched) <= self.n // 2
                and (hsmm == final or any(final in s["steps"] for s in closed))):
            self.wrapped_at = tt                     # at most every wrap_every_s, before the back-off
            return "steps left"
        if forgot:
            self.reminded.update(forgot)
            return "forgotten step"
        if closed and self.off_since >= self.s.off_task_s:
            return "off task"
        if tt - self.last_ask < self.gap:            # the back-off holds everything but the events above
            return None
        if self.want is not None:
            want, self.want = self.want, None
            if want == advised:                      # the advice on screen is already about this step: stay quiet
                self.suppressed["step change"] += 1
                return None
            return "step change"
        if self.off_advice >= self.s.deviation_s:
            return "off advice"
        if closed and n_done - self.used >= self.s.fallback_n:
            if (hsmm, statuses) == self.snapshot:    # same step, same checklist as at the last call: nothing new
                self.suppressed["N actions"] += 1
                self.used = n_done
                return None
            return "N actions"
        return None

    def recent(self, done_segs: list[dict]) -> tuple[list[dict], list[dict]]:
        """(the segments to list in full, the older ones to summarise): the new ones since the last question,
        at most fallback_n, or the last three when fewer than three are new."""
        fresh = done_segs[self.used:]
        recent = fresh[-self.s.fallback_n:] if len(fresh) >= 3 else done_segs[-3:]
        return recent, done_segs[:len(done_segs) - len(recent)]

    def asked(self, tt: float, sec: float, n_done: int, hsmm: int, statuses: list[str]) -> None:
        self.free_at, self.last_ask, self.used, self.off_since, self.off_advice = tt + sec, tt, n_done, 0.0, 0
        self.snapshot = (hsmm, statuses)
