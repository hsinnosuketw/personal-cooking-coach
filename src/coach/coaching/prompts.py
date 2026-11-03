"""The coach's prompts, from the first stateless one (stage 13) to the reminder coach (stage 35).

Later prompts are built from earlier ones by cutting and swapping parts of the text, so every version keeps the
same recipe block and wording; a change in one shows up in all of them (and in scripts/replay_pin.py).
Everything here is plain text in, text out: the caller gathers the evidence up to time t.
"""
from __future__ import annotations

from ..memory.checklist import loop_status
from .reminders import mmss


def coach_prompt(name: str, texts: list[str], steps, history: list[str], t: float, now: str, tracker_step: int,
                 source: str, lang: str) -> str:
    """Stage 13: recipe, the actions each step involves, the history, what the probe expects next, the tracker's step.

    now: the probe's top actions in about 1 s, as "take egg (0.31), …"; source: who wrote the history lines.
    """
    recipe = "\n".join(f"{k + 1}. {s}" for k, s in enumerate(texts))
    bank = "\n".join(f"{s.order + 1}. " + ", ".join(dict.fromkeys(f"{v} {n}" for v, n, _ in s.pairs)) for s in steps)
    return f"""You are a cooking coach watching a home cook through a head-mounted camera.

Recipe: {name}
{recipe}

Hand actions each step usually involves:
{bank}

What the cook has done so far, from {source}:
{chr(10).join(history)}

Now (t = {t:.0f} s) the model expects in about 1 s: {now}.
A step tracker thinks the cook is on {'step ' + str(tracker_step + 1) if tracker_step >= 0 else 'no step yet'} (it is right about half the time).

Answer in {lang}, briefly, with these three headings:
Fundamentals: the 1-3 principles of this dish that matter at this moment.
Where: which step the cook is on and what is done or still missing.
Next: the single next thing the cook should do, and why (2-3 sentences)."""


def checklist_lines(ledger: dict, texts: list[str]) -> str:
    return "\n".join(f"{k + 1}. [{s['status']}] {texts[k][:80]}" for k, s in enumerate(ledger["steps"]))


def checklist_lines_loops(ledger: dict, texts: list[str], loops: list[dict]) -> str:
    """Stage 29: statuses with rounds, plus the recipe's repeated runs."""
    rows = "\n".join(f"{k + 1}. [{loop_status(s)}] {texts[k][:80]}" for k, s in enumerate(ledger["steps"]))
    runs = "; ".join(f"steps {lp['first'] + 1}-{lp['last'] + 1} repeat ({lp['times']}: {lp['what']})" for lp in loops)
    return rows + (f"\nRepeated runs in this recipe: {runs}. A finished step in a repeated run can start a new round."
                   if runs else "")


def memory_prompt(base: str, checklist: str, last: dict | None, aligned_share: float | None, should: str,
                  seen_since: list[str], doing: list[str], lang: str) -> str:
    """Stage 23: stage 13's prompt (`base`) plus the checklist, the last advice and whether the cook followed it."""
    follow = "" if aligned_share is None else f" Since then, the camera matched the suggested next action {aligned_share:.0%} of the time."
    return base.split("\nAnswer in")[0] + f"""

Your checklist so far (from your earlier answers; "in progress" can also come from the camera):
{checklist}
Recipe actions the camera recognised with confidence since your last answer: {', '.join(seen_since) or 'none'}.
Your previous advice: {last['next'] if last else 'none yet'}.{follow}
Right now the decision model says the cook should: {should}. The camera says the cook appears to: {', '.join(doing)}.

Answer in {lang}, briefly, with two headings:
Where: what is done, what is in progress, what is still left.
Next: the single next thing the cook should do, and why (2-3 sentences). Do not repeat advice for a step that is done.
Then end with exactly these four lines:
DONE: <step numbers, or none>
IN PROGRESS: <step numbers, or none>
LEFT: <step numbers, or none>
STEP: <the step the cook should work on now>"""


def older_summary(segs: list[dict]) -> str:
    """Segments before the recent ones, as one line per step: how many, how long, when last."""
    by_step = {}
    for s in segs:
        for k in s["steps"] or [None]:
            rec = by_step.setdefault(k, [0, 0.0, 0.0])
            rec[0] += 1; rec[1] += s["t1"] - s["t0"]; rec[2] = s["t1"]
    rows = [f"{'step ' + str(k + 1) if k is not None else 'other (not in the recipe)'}: {n} segments, {sec:.0f} s, last at {last:.0f} s"
            for k, (n, sec, last) in sorted(by_step.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))]
    return "\n".join(rows) or "nothing yet"


EVENT_WHY = {"N actions": "The cook has finished {n} more actions since your last advice.",
             "forgotten step": "A later recipe step has started while an earlier one has no sign of being done.",
             "off task": "The cook has spent a while on things that are not in the recipe."}


def event_prompt(base: str, checklist: str, recent_lines: list[str], older: str, last: dict | None, should: str,
                 reason: str, lang: str) -> str:
    """Stage 25: stage 13's recipe block (`base`), the checklist, older actions per step, the recent segments."""
    head = base.split("What the cook has done so far")[0]
    now = "Now (t =" + base.split("Now (t =")[1].split("\nAnswer in")[0]
    why = EVENT_WHY[reason].format(n=len(recent_lines))
    return head + f"""Your checklist so far ("in progress"/"done" can also come from the camera and the recipe order):
{checklist}

Earlier actions, summarised per recipe step:
{older}

The cook's last {len(recent_lines)} actions, in order (from an action-recognition model that is often wrong about objects):
{chr(10).join(recent_lines)}

{now.strip()}
Your previous advice: {last['next'] if last else 'none yet'}
The decision model now says the cook should: {should}.
Why you are asked now: {why}

Look at the whole sequence of actions, not just the last one. If a later step is clearly under way, earlier steps are probably done.
Answer in {lang}, briefly, with two headings:
Where: what is done, what is in progress, what is still left.
Next: the single next thing the cook should do, and why (2-3 sentences). Do not repeat advice for a step that is done.
Then end with exactly these four lines:
DONE: <step numbers, or none>
IN PROGRESS: <step numbers, or none>
LEFT: <step numbers, or none>
STEP: <the step the cook should work on now>"""


WHY = {"N actions": "The cook has finished {n} more actions since your last advice.",
       "forgotten step": "A later recipe step has started while an earlier one has no sign of being done.",
       "off task": "The cook has spent a while on things that are not in the recipe.",
       "step change": "The cook seems to have moved to a different recipe step.",
       "off advice": "For a while the cook has not been working on the step your last advice named.",
       "steps left": "The cook seems to be finishing the dish, but some steps show no sign of having been started."}

INTENT_ANSWER = """Answer in {lang}, briefly, with three headings:
Now: what the cook is doing at this moment and what they are trying to achieve with it (one sentence).
Goal: which recipe step that serves{rounds}, what is done and what is still left.
Next: the single next thing the cook should do, and why (2-3 sentences). Do not repeat advice for a step that is done.
Then end with exactly these five lines:
DOING: <the step the cook is working on now, or none>
DONE: <step numbers, or none>
IN PROGRESS: <step numbers, or none>
LEFT: <step numbers, or none>
STEP: <the step the cook should work on now>"""

REMIND_ANSWER = """The cook may do the steps in any order; the recipe order is only a guide. Your job is to remember what has been done and make sure no step is left out.
Answer in {lang}, briefly, with two headings:
Where: what has been done (with times), what is in progress, and which steps have not been started.
Next: the single most useful thing to do now (2-3 sentences). If a step that has not been started can be done now, remind the cook of it; otherwise help finish the current step. Never ask the cook to redo a step that is done.
Then end with exactly these five lines:
DONE: <step numbers, or none>
IN PROGRESS: <step numbers, or none>
LEFT: <step numbers, or none>
STEP: <the step the cook should work on now>
REMIND: <one step not started yet that the cook should not forget, or none>"""


def adaptive_prompt(event: str, n_recent: int, reason: str, plain_checklist: str, checklist: str | None = None,
                    answer: str | None = None) -> str:
    """Stage 31: stage 25's prompt (`event`, asked as "N actions") with the real reason for asking, and optionally
    another checklist (loop-aware, or stage 35's memory lines) and another answer format (three-layer, reminders)."""
    p = event
    swaps = [(WHY["N actions"].format(n=n_recent), WHY[reason].format(n=n_recent))]
    if checklist is not None:
        swaps.append((plain_checklist, checklist))
    if answer is not None:
        swaps.append((p[p.index("Answer in "):], answer))
    for old, new in swaps:
        assert old in p, old[:60]
        p = p.replace(old, new, 1)
    return p


def memory_lines(ledger: dict, t: float, texts: list[str], steps_of: dict, loops: list[dict] | None,
                 frame_notes: dict[int, str] | None = None) -> str:
    """Stage 35: the checklist with when each step was first and last seen, and which steps show no sign yet.
    loops: the recipe's repeated runs for loop-aware statuses, or None for plain statuses."""
    frame_notes = frame_notes or {}
    rows = []
    for k, s in enumerate(ledger["steps"]):
        seen = [(rec[0], rec[1], a) for a, rec in ledger["seen"].items() if k in steps_of.get(a, [])]
        when = (f"; first sign {mmss(min(seen)[0])} ({min(seen)[2]}), last sign {mmss(max(r[1] for r in seen))}" if seen else "")
        note = f"; {frame_notes[k]}" if k in frame_notes else ""
        rows.append(f"{k + 1}. [{loop_status(s) if loops is not None else s['status']}{when}{note}] {texts[k][:70]}")
    untouched = [k + 1 for k, s in enumerate(ledger["steps"]) if s["status"] == "not started"]
    loops_note = ("\nRepeated runs in this recipe: " + "; ".join(f"steps {lp['first'] + 1}-{lp['last'] + 1} ({lp['times']})" for lp in loops)
                  if loops else "")
    return "\n".join(rows) + f"\nNo sign at all yet (now {mmss(t)}): " + (", ".join(f"step {k}" for k in untouched) or "none") + loops_note
