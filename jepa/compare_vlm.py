"""Which way of asking the VLM gives the step tracker the most useful tags?

  NVIDIA_API_KEY=... python3 -m jepa.compare_vlm [--runs 2]

Each variant tags HD-EPIC P08_R03's own step texts (the recipe as the cook
wrote it, not the annotations of what they did), so the steps line up with
HD-EPIC's and the tracker's accuracy needs no hand mapping. Uses the saved
world-model predictions (results/demo/P08.npz); no GPU. Writes every run,
with its raw answer, to results/vlm_variants.json.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from .action_bank import ActionBankRepository
from .domain import Prediction
from .extractors import HDEpicExtractor, NIMRecipeExtractor
from .guide_video import active, truth_steps
from .scorer import LatentStateScorer, match_scores
from .vocab import Vocab, class_frequencies

HERE = Path(__file__).parent
RECIPE, VIDEO = "P08_R03", "P08-20240614-085000"
VARIANTS = {
    "hand-level tags": dict(distinct=False, image=False, hand_level=True),
    "tags": dict(distinct=False, image=False),
    "distinct tags": dict(distinct=True, image=False),
    "distinct tags + kitchen photo": dict(distinct=True, image=True),
}


def tracker_accuracy(vocab, steps, pred, truth) -> dict:
    bank = ActionBankRepository(vocab).from_steps(steps)
    scorer = LatentStateScorer(bank)
    match = match_scores(bank, pred["verb"].astype(float), pred["noun"].astype(float))
    res = [scorer.evaluate(Prediction(float(t), pred["verb"][i], pred["noun"][i]), match[i])
           for i, t in enumerate(pred["t"])]
    rows = [(r.extras["current"], r.extras["best"], active(truth, t + 1.0)) for r, t in zip(res, pred["t"])]
    rows = [r for r in rows if r[2]]
    return {"current_step": round(float(np.mean([c in a for c, _, a in rows])), 3),
            "best_each_second": round(float(np.mean([b in a for _, b, a in rows])), 3),
            "chance": round(float(np.mean([len(a) / len(steps) for *_, a in rows])), 3)}


def distinctness(steps) -> float:
    """Share of tags that belong to exactly one step."""
    seen: dict[tuple, int] = {}
    for s in steps:
        for v, n, _ in set(s.pairs):
            seen[(v, n)] = seen.get((v, n), 0) + 1
    return round(sum(c == 1 for c in seen.values()) / max(1, len(seen)), 2)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--only", default="", help="run just this variant, e.g. 'hand-level tags'")
    ap.add_argument("--photo", type=Path, default=HERE / "results/demo/frames/t0003.jpg",
                    help="a frame of the kitchen before cooking starts")
    args = ap.parse_args()
    vocab = Vocab.load()
    hd = HDEpicExtractor(vocab)
    pred = dict(np.load(HERE / "results/demo/P08.npz"))
    truth = truth_steps(hd, RECIPE, VIDEO)
    hd_steps = hd.extract_steps(RECIPE)
    texts = [s.text for s in hd_steps]
    name = hd.recipes[RECIPE]["name"]
    freqs = class_frequencies()

    def summary(steps):
        return {"accuracy": tracker_accuracy(vocab, steps, pred, truth), "distinct_share": distinctness(steps)}

    out = {"recipe": RECIPE, "reference": {"HD-EPIC annotated tags (in-sample)": summary(hd_steps)}, "runs": []}
    print("HD-EPIC annotated tags (in-sample):", out["reference"])
    for label, opt in VARIANTS.items():
        if args.only and label != args.only:
            continue
        for run in range(args.runs):
            ex = NIMRecipeExtractor(vocab, distinct=opt["distinct"], images=[args.photo] if opt["image"] else [],
                                    hand_level=opt.get("hand_level", False), frequencies=freqs)
            t0 = time.time()
            steps = ex.tag_steps(name, texts)
            row = {"variant": label, "run": run + 1, "seconds": round(time.time() - t0, 1), **summary(steps),
                   "tokens": [ex.prompt_tokens, ex.completion_tokens], "dropped": ex.dropped,
                   "mapped": [{"step": k + 1, "from": f, "to": t} for k, f, t in ex.mapped],
                   "steps": [{"step": s.order + 1, "text": s.text, "pairs": [f"{v} {n}" for v, n, _ in s.pairs]}
                             for s in steps],
                   "raw_answer": ex.last_raw}
            out["runs"].append(row)
            print(f"{label:30} run {run + 1}: {row['accuracy']}  distinct {row['distinct_share']}  "
                  f"{row['seconds']}s dropped {ex.dropped}", flush=True)
    name = "vlm_variants" + (f"_{args.only.replace(' ', '_')}" if args.only else "")
    (HERE / f"results/{name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
