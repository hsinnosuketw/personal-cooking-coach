"""B0 / S1 / A1 comparison on structured cases (plan H01-H05).

  python3 -m livecoach.evaluate [--cases livecoach/cases/dev.json]
                                [--provider mock|meta[:model]] [--repeats 3]

S1 is the full pipeline; A1 is S1 without memory across recipes; B0 asks
the same provider once for the next move with no candidates, world model
or memory. Every run gets a fresh session and provider (isolated state,
memory and cache). A case passes for a system when at least two thirds of
its repeats choose a move from the case's acceptable set; any repeat
choosing from its high_risk set counts as a high-risk error.

On MockProvider the numbers only show the harness runs end to end. The dev
cases are synthetic and were used to develop the rules, so S1 doing well on
them says nothing about real performance (see livecoach/README.md).
"""
from __future__ import annotations

import argparse
import json
import pathlib

from . import state
from .provider import MetaProvider, MockProvider
from .schema import ObservationEvent
from .session import Session

SYSTEMS = ("B0", "S1", "A1")
CATEGORIES = ("correct", "normal", "clarify")
DEFAULT_CASES = pathlib.Path(__file__).with_name("cases") / "dev.json"


def make_provider(name: str):
    if name == "mock":
        return MockProvider()
    return MetaProvider(model=name.split(":", 1)[1]) if ":" in name else MetaProvider()


def run_case(case: dict, system: str, provider) -> str:
    events = [ObservationEvent(**e) for e in case["events"]]
    if system == "B0":
        s = state.initial_state(case["recipe_id"])
        for e in events:
            s = state.apply_event(s, e)
        return provider.direct_decide(s)
    history = case.get("history")
    sess = Session("eval", history["recipe_id"] if history else case["recipe_id"], provider,
                   memory=(system == "S1"))
    if history:
        for e in history["events"]:
            sess.observe(ObservationEvent(**e))
        sess.switch_recipe(case["recipe_id"], events[0].ts)
    decision = None
    for e in events:
        decision = sess.observe(e)
    return decision.candidate_id


def evaluate(cases: list[dict], provider_name: str = "mock", repeats: int = 1) -> list[dict]:
    rows = []
    for case in cases:
        for system in SYSTEMS:
            for r in range(repeats):
                provider = make_provider(provider_name)
                try:
                    move, error = run_case(case, system, provider), None
                except Exception as e:  # keep failures and timeouts in the results (plan H05)
                    move, error = None, f"{type(e).__name__}: {e}"
                rows.append({"case_id": case["case_id"], "category": case["category"], "system": system,
                             "repeat": r, "move": move, "error": error,
                             "pass": move in case["acceptable"],
                             "high_risk": move in case.get("high_risk", []),
                             "calls": provider.calls})
    return rows


def summarize(rows: list[dict], repeats: int) -> dict:
    """Per system: passed cases by category, high-risk errors, errors, calls."""
    need = -(-2 * repeats // 3)  # at least two thirds of the repeats
    out = {s: {"by_cat": {c: [0, 0] for c in CATEGORIES}, "high_risk": 0, "errors": 0, "calls": 0}
           for s in SYSTEMS}
    cases = {(r["case_id"], r["category"]) for r in rows}
    for case_id, cat in cases:
        for s in SYSTEMS:
            mine = [r for r in rows if r["case_id"] == case_id and r["system"] == s]
            out[s]["by_cat"][cat][1] += 1
            out[s]["by_cat"][cat][0] += sum(r["pass"] for r in mine) >= need
            out[s]["high_risk"] += sum(r["high_risk"] for r in mine)
            out[s]["errors"] += sum(r["error"] is not None for r in mine)
            out[s]["calls"] += sum(r["calls"] for r in mine)
    return out


def markdown(rows: list[dict], cases_meta: dict, provider_name: str, repeats: int) -> str:
    s = summarize(rows, repeats)
    lines = [f"Provider `{provider_name}` · {len({r['case_id'] for r in rows})} cases × {repeats} "
             f"repeat(s) · split `{cases_meta.get('split')}`"
             + (" · **synthetic: harness check only, not a result**" if cases_meta.get("synthetic") else ""),
             "", "| System | Passed | Correct | Normal | Clarify | High-risk moves | Errors | Calls |",
             "|---|---|---|---|---|---|---|---|"]
    for sys_ in SYSTEMS:
        b = s[sys_]["by_cat"]
        passed = sum(v[0] for v in b.values())
        total = sum(v[1] for v in b.values())
        lines.append(f"| {sys_} | {passed}/{total} | " + " | ".join(f"{b[c][0]}/{b[c][1]}" for c in CATEGORIES)
                     + f" | {s[sys_]['high_risk']} | {s[sys_]['errors']} | {s[sys_]['calls']} |")
    lines += ["", "| Case | Category | B0 | S1 | A1 |", "|---|---|---|---|---|"]
    for case_id in dict.fromkeys(r["case_id"] for r in rows):
        mine = [r for r in rows if r["case_id"] == case_id]
        cells = []
        for sys_ in SYSTEMS:
            first = next(r for r in mine if r["system"] == sys_)
            mark = "✓" if first["pass"] else ("✗ high-risk" if first["high_risk"] else "✗")
            cells.append(f"{first['move'] or first['error']} {mark}")
        lines.append(f"| {case_id} | {mine[0]['category']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cases", default=str(DEFAULT_CASES))
    ap.add_argument("--provider", default="mock")
    ap.add_argument("--repeats", type=int, default=1)
    args = ap.parse_args()
    data = json.loads(pathlib.Path(args.cases).read_text(encoding="utf-8"))
    rows = evaluate(data["cases"], args.provider, args.repeats)
    print(markdown(rows, data, args.provider, args.repeats))


if __name__ == "__main__":
    main()
