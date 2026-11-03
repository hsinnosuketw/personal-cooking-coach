"""Which actions show that a step began (stage 34): the camera rule with different sets of starting actions."""
from __future__ import annotations

import numpy as np

from .goals import STARTED_SLACK_S

# fetching, tidying and checking happen for every step (and before it), so on their own they don't show a step began
FETCH_VERBS = {"take", "put", "open", "close", "move", "check", "insert", "remove", "hold", "lift", "pat", "touch", "press",
               "turn-on", "turn-off", "wash", "dry", "throw", "search", "look", "pull", "push", "slide", "turn", "carry"}
OFF_NOUNS = {"phone", "recipe", "tablet", "cupboard", "drawer", "fridge", "lid", "tap", "hand", "towel", "scale", "clothes"}


def start_actions(steps_of: dict, specific_only: bool, doing_verbs: bool) -> dict:
    """Bank action -> steps it can start. specific_only: the action belongs to one step; doing_verbs: not fetching/tidying."""
    out = {}
    for a, ks in steps_of.items():
        verb, noun = a.split(" ", 1)
        if doing_verbs and (verb in FETCH_VERBS or noun.split(":")[0] in OFF_NOUNS):
            continue
        if specific_only and len(ks) > 1:
            continue
        out[a] = ks
    return out


def hybrid_starters(steps_of: dict) -> dict:
    """Doing-verb actions for steps that have any; every bank action for steps that don't."""
    doing = start_actions(steps_of, False, True)
    has = {k for ks in doing.values() for k in ks}
    return {a: [k for k in ks if (k in has) == (a in doing)] for a, ks in steps_of.items()
            if any((k in has) == (a in doing) for k in ks)}


def replay_starts(starters: dict, ts, action_probs, action_row: dict, p_min: float, k_s: int) -> dict:
    """The camera rule alone: step -> [first, last] second its actions were seen (p >= p_min for k_s seconds in a row).
    action_probs: the probe's action head per tick."""
    names = list(starters)
    rows = np.array([action_row[a] for a in names], int)
    run, out = {}, {}
    for i, tt in enumerate(np.asarray(ts, dtype=float)):
        for a, pa in zip(names, action_probs[i].astype(float)[rows]):
            run[a] = run.get(a, 0) + 1 if pa >= p_min else 0
            if run[a] >= k_s:
                for k in starters[a]:
                    rec = out.setdefault(k, [tt, tt]); rec[1] = tt
    return out


def start_scores(starts: dict, truth, ts, n_steps: int) -> dict:
    first = {}
    for k, s0, s1 in truth:
        first[k] = min(first.get(k, 1e9), s0)
    lag = [starts[k][0] - first[k] for k in first if k in starts]
    tp = fp = fn = 0
    for tt in np.asarray(ts, dtype=float)[::5]:
        for k in range(n_steps):
            said, real = k in starts and starts[k][0] <= tt, first.get(k, 1e9) <= tt + STARTED_SLACK_S
            tp, fp, fn = tp + (said and real), fp + (said and not real), fn + (real and not said)
    return {"remembered": f"{sum(k in starts for k in first)}/{len(first)}", "F1 over time": round(2 * tp / max(1, 2 * tp + fp + fn), 2),
            "median lag (s)": round(float(np.median(lag))) if lag else None,
            "median |lag| (s)": round(float(np.median(np.abs(lag)))) if lag else None,
            "too early (>10 s)": sum(l < -STARTED_SLACK_S for l in lag),
            "never done but remembered": sum(k not in first for k in starts)}
