"""Let the VLM read the world model's predictions and decide the recipe step, offline.

  NVIDIA_API_KEY=... python3 -m coach.evaluation.vlm_tracker [--runs 2] [--window 60]

The scorer matches probe words to step tags with fixed rules. Here the VLM
gets the recipe's own step texts plus, for each second, the probe's top
verbs, nouns and actions, and says which step the cook is on. It can use
common sense the scorer can't (a predicted object the recipe never uses is
probably a mistake for one it does). One call per window of `window` seconds;
the step chosen at the end of a window is passed into the next one.

Two controls show whether the predictions are really used: an even split
of the timeline across the steps (no model), and the same VLM prompt with
the predictions removed. Not real time: each call takes tens of seconds.
Writes results/vlm_tracker.json.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import numpy as np

from ..data.extractors import HDEpicExtractor, NIMRecipeExtractor
from ..render.guide_video import action_names, active, truth_steps
from ..data.vocab import Vocab

from ..config import RESULTS
RECIPE, VIDEO = "P08_R03", "P08-20240614-085000"


def evidence_line(t: float, i: int, pred: dict, names: dict) -> str:
    def top(key, k):
        p = pred[key][i].astype(float)
        return ", ".join(f"{names[key][j]} {p[j]:.2f}" for j in np.argsort(-p)[:k])
    return f"t={int(t)}: verbs {top('verb', 3)} | nouns {top('noun', 3)} | actions {top('action', 3)}"


def prompt(name: str, texts: list[str], lines: list[str], prev: int | None, with_evidence: bool,
           t0: int, t1: int, total: int) -> str:
    steps = "\n".join(f"{k + 1}. {s}" for k, s in enumerate(texts))
    head = (f"A cook is making {name}, filmed by a head-mounted camera. The recipe:\n{steps}\n\n"
            f"The video is {total} s long. ")
    if prev:
        head += f"Just before t={t0} the cook was on step {prev}. "
    if with_evidence:
        head += ("Below, for each second, is what an action-recognition model expects the cook to do about 1 s "
                 "later (its top guesses with confidence; it is often wrong, especially about objects). Use the recipe and common sense to decide which recipe step the cook is on each "
                 "second. Cooks sometimes go back to an earlier step or do steps in a different order.\n\n"
                 + "\n".join(lines) + "\n\n")
    else:
        head += (f"Guess which recipe step the cook is most likely on during t={t0}..{t1}, using only the recipe "
                 "and typical timing (no other information is available).\n\n")
    return head + (f"Cover every second from t={t0} to t={t1}. Return only JSON: {{\"segments\": "
                   "[{\"from\": <t>, \"to\": <t>, \"step\": <1-" + str(len(texts)) + ">}]} with segments in time "
                   "order, no gaps.")


def parse_segments(text: str, ticks: np.ndarray, n_steps: int) -> dict[int, int]:
    m = re.search(r"\{.*\}", text, re.S)
    segs = json.loads(m.group(0) if m else text)["segments"]
    out = {}
    for s in segs:
        k = int(s["step"]) - 1
        if 0 <= k < n_steps:
            for t in ticks[(ticks >= float(s["from"])) & (ticks <= float(s["to"]) + 0.99)]:
                out[int(t)] = k
    return out


def score(assign: dict[int, int], ticks: np.ndarray, truth) -> float:
    rows = [(assign.get(int(t)), active(truth, t + 1.0)) for t in ticks]
    rows = [(a, s) for a, s in rows if s]
    return round(float(np.mean([a in s for a, s in rows])), 3)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--window", type=int, default=60)
    args = ap.parse_args()
    vocab = Vocab.load()
    hd = HDEpicExtractor(vocab)
    pred = dict(np.load(RESULTS / "demo/P08.npz"))
    ticks = pred["t"]
    truth = truth_steps(hd, RECIPE, VIDEO)
    texts = [s.text for s in hd.extract_steps(RECIPE)]
    name = hd.recipes[RECIPE]["name"]
    names = {"verb": sorted(vocab.verb_row, key=vocab.verb_row.get),
             "noun": sorted(vocab.noun_row, key=vocab.noun_row.get), "action": action_names()}
    total = int(ticks[-1])

    even = {int(t): min(len(texts) - 1, int(len(texts) * (t - ticks[0]) / (ticks[-1] - ticks[0] + 1))) for t in ticks}
    out = {"recipe": RECIPE, "chance": round(float(np.mean([len(s) / len(texts) for t in ticks
                                                            if (s := active(truth, t + 1.0))])), 3),
           "even_split": score(even, ticks, truth), "runs": []}
    print(f"chance {out['chance']}, even time split {out['even_split']}", flush=True)

    for with_evidence in (True, False):
        for run in range(args.runs):
            ex = NIMRecipeExtractor(vocab)
            assign, prev, calls, t_start = {}, None, [], time.time()
            for w0 in range(int(ticks[0]), total + 1, args.window):
                w1 = min(total, w0 + args.window - 1)
                idx = [i for i, t in enumerate(ticks) if w0 <= t <= w1]
                lines = [evidence_line(ticks[i], i, pred, names) for i in idx]
                body = {"model": ex.model, "temperature": 0.2, "max_tokens": 800, "messages": [
                    {"role": "user", "content": prompt(name, texts, lines, prev, with_evidence, w0, w1, total)}]}
                data, got = {}, {}
                for attempt in range(3):
                    try:
                        data = ex.post(body)
                        got = parse_segments(data["choices"][0]["message"]["content"], ticks[idx], len(texts))
                        break
                    except (ValueError, KeyError, TypeError, TimeoutError, OSError) as e:
                        got = {}
                        if attempt == 2:  # a skipped window counts as wrong (coverage shows how many)
                            print(f"  window {w0}: no usable answer ({type(e).__name__})", flush=True)
                usage = data.get("usage") or {}
                calls.append([usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)])
                assign.update(got)
                if got:
                    prev = got[max(got)] + 1
            label = "VLM reads predictions" if with_evidence else "VLM, no predictions (control)"
            row = {"variant": label, "run": run + 1, "accuracy": score(assign, ticks, truth),
                   "coverage": round(len(assign) / len(ticks), 3), "calls": len(calls),
                   "tokens": [sum(c[0] for c in calls), sum(c[1] for c in calls)],
                   "seconds": round(time.time() - t_start), "steps": {str(k): v for k, v in sorted(assign.items())}}
            out["runs"].append(row)
            print(f"{label:32} run {run + 1}: accuracy {row['accuracy']}  coverage {row['coverage']}  "
                  f"{row['calls']} calls {row['seconds']} s tokens {row['tokens']}", flush=True)
            (RESULTS / "vlm_tracker.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
