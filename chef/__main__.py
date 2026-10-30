"""Gameplay dataset -> learned world model -> AI chef.

  python3 -m chef bots [--n 90]            synthetic test rounds (pipeline check only)
  python3 -m chef stats                    what the dataset holds
  python3 -m chef evaluate [--with-bots]   train on human rounds (held-out check),
                                           let the AI chef cook --n rounds in the real
                                           engine, compare with the players, and write
                                           ai_chef_runs.json for the replay in play.html
"""
from __future__ import annotations

import argparse
import json
import random
import statistics

from . import agent, bots, store
from .learn import LearnedWorldModel, transitions

SYNTH_DIR = store.ROOT / "synthetic"


def _dataset(with_bots: bool) -> tuple[list[dict], list[dict]]:
    humans = store.load(store.HUMAN_DIR) if store.HUMAN_DIR.exists() else []
    synth = store.load(SYNTH_DIR) if (with_bots and SYNTH_DIR.exists()) else []
    return humans, synth


def cmd_bots(n: int) -> None:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    for old in SYNTH_DIR.glob("*.json"):
        old.unlink()
    styles = list(bots.STYLES)
    for i in range(n):
        ep = bots.play(styles[i % len(styles)], seed=1000 + i)
        (SYNTH_DIR / f"bot-{i:03d}.json").write_text(json.dumps(ep), encoding="utf-8")
    print(f"wrote {n} synthetic rounds to {SYNTH_DIR} (pipeline check only, never reported as human)")


def cmd_stats() -> None:
    humans, synth = _dataset(True)
    for name, eps in (("human", humans), ("synthetic", synth)):
        if eps:
            sc = [e["final"]["score"]["total"] for e in eps]
            print(f"{name}: {len(eps)} rounds, {sum(len(e['transitions']) for e in eps)} transitions, "
                  f"score mean {statistics.mean(sc):.1f}, best {max(sc):.1f}")
        else:
            print(f"{name}: 0 rounds")


def cmd_evaluate(with_bots: bool, n: int) -> None:
    humans, synth = _dataset(with_bots)
    eps = humans + synth
    if len(eps) < 5:
        raise SystemExit("need at least 5 rounds: play some at play.html (or add --with-bots to test)")
    random.Random(0).shuffle(eps)
    cut = max(1, len(eps) // 5)  # hold out a fifth of the rounds, not just of the transitions
    model = LearnedWorldModel().fit(*transitions(eps[cut:]))
    err = model.error(*transitions(eps[:cut]))
    runs = [agent.play(model, seed=50_000 + i) for i in range(n)]
    ai = [r["final"]["score"]["total"] for r in runs]
    summary = {"ai_mean": round(statistics.mean(ai), 1), "ai_best": max(ai),
               "human_mean": round(statistics.mean(e["final"]["score"]["total"] for e in humans), 1) if humans else None,
               "bot_mean": round(statistics.mean(e["final"]["score"]["total"] for e in synth), 1) if synth else None,
               "heldout_error": {k: round(v, 4) for k, v in err.items()}}
    trained_on = {"human_rounds": len(humans), "synthetic_rounds": len(synth), "transitions": model.n_train}
    store.AI_RUNS.write_text(json.dumps({"trained_on": trained_on, "summary": summary,
                                         "runs": sorted(runs, key=lambda r: -r["final"]["score"]["total"])[:10]}),
                             encoding="utf-8")
    print(json.dumps({"trained_on": trained_on, **summary}, indent=1))
    if synth:
        print("NOTE: includes synthetic bot rounds -- a pipeline check, not a result.")


def main() -> None:
    ap = argparse.ArgumentParser(prog="python3 -m chef", description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=("bots", "stats", "evaluate"))
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--with-bots", action="store_true")
    args = ap.parse_args()
    if args.command == "bots":
        cmd_bots(args.n or 90)
    elif args.command == "stats":
        cmd_stats()
    else:
        cmd_evaluate(args.with_bots, args.n or 20)


if __name__ == "__main__":
    main()
