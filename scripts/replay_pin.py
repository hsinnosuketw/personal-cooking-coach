"""Pin test for refactoring: replay saved coach runs through the notebook's current code and compare.

  python3 scripts/replay_pin.py record   # replay, check against the saved results, save the prompts the coach was sent
  python3 scripts/replay_pin.py check    # replay again; compare with the saved results and the recorded prompts

Use it when moving notebook code into src/coach: record before the move, check after. It needs results/ and data/
(git-ignored), so it lives here rather than in tests/.

The coach and d1 are replaced by replayers that hand back each saved answer in order, so any change in the run
loop, the memory or the prompts shows up as a different call time, ledger, prompt text, or state and questions
given to d1 (recorded as hashes).
Everything runs in a sandbox ROOT (copies of results/ and data/processed/), so nothing in the repo is written.
"""
import contextlib, hashlib, json, os, shutil, sys, types, traceback
from pathlib import Path

import tempfile
REPO = Path(__file__).resolve().parents[1]
BOX = Path(tempfile.gettempdir()) / "coach_replay_pin"
RECORD = REPO / "results" / "replay_pin_prompts.json"
sys.path.insert(0, str(REPO / "src"))
import matplotlib; matplotlib.use("Agg")
import numpy as np

DISHES = [("P08-20240614-085000", "P08_R03"), ("P02-20240210-113925", "P02_R04")]
CELLS = ["c13c", "c15c", "c21c", "c22c", "c24c", "c25c", "c26c", "c27c", "c28c", "c29c", "c30c", "c31c", "c33c",
         "c35c", "c36c", "c40c"]
TICK_KEYS = ("t", "tracker", "hsmm", "wm", "d1", "d1_step", "speak", "should", "aligned", "ledger", "rounds", "recent")
CALL_KEYS = ("t", "ready", "trigger", "n_actions", "step", "hsmm", "coach_step", "remind", "next", "parsed")


def sandbox():
    if BOX.exists():
        shutil.rmtree(BOX)
    (BOX / "data").mkdir(parents=True)
    (BOX / "data/raw").symlink_to(REPO / "data/raw")
    shutil.copytree(REPO / "data/processed", BOX / "data/processed")
    (BOX / "results").mkdir()
    for f in (REPO / "results").glob("*.json"):
        shutil.copy2(f, BOX / "results" / f.name)
    (BOX / "site").mkdir()


class NoModel(Exception):
    pass


def no_coach(prompt, config=None):
    raise NoModel("coach")


class NoD1:
    def system_one(self, state, qs):
        raise NoModel("d1")


def cell_sources():
    notebook = Path(os.environ.get("PIN_NOTEBOOK", REPO / "notebooks/pipeline.ipynb"))   # record from an older copy
    nb = {c.get("id"): "".join(c["source"]) for c in json.load(open(notebook))["cells"]}
    def must(src, old, new):
        assert old in src, f"runner patch no longer matches: {old!r}"
        return src.replace(old, new)
    return nb, must


def setup(video, recipe):
    nb, must = cell_sources()
    stub = types.ModuleType("torch")
    class _NoGrad(contextlib.ContextDecorator):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    stub.no_grad = _NoGrad
    sys.modules.setdefault("torch", stub)
    ns = {"ROOT": BOX, "display": lambda x: None, "torch": stub, "__name__": "__main__",
          "COACH_CONFIGS": {"replay": {}}, "COACH_CONFIG": "replay", "coach": no_coach, "D1": NoD1()}
    src = must(nb["c04"], 'VIDEO_ID = "P08-20240614-085000"', f'VIDEO_ID = "{video}"')
    src = must(src, 'RECIPE = "P08_R03"', f'RECIPE = "{recipe}"')
    run = [("c04", src), ("imports", "import os, sys, json, re, time\nimport numpy as np, pandas as pd"),
           ("c14", "pred = dict(np.load(PRED))\n"), ("c16", nb["c16"]),
           ("c18", must(nb["c18"], 'STEP_TAGS = "vlm"', 'STEP_TAGS = "hdepic"')), ("c20", nb["c20"]), ("c22", nb["c22"])]
    for cid in CELLS:
        s = nb[cid]
        if cid == "c15c":  # the part after loading d1
            s = "D1_INCLUDE_THINKING = True\n" + s[s.index("ACTIONS") if "dm.d1_choices" not in s else s.index("from coach.decision"):s.index("state = d1_state(T_COACH")]
        run.append((cid, s))
    errors = {}
    with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet):
        for cid, s in run:
            try:
                exec(s, ns)
            except NoModel:
                pass   # a cell tried to run a model for a result the sandbox lacks: its definitions are in place
            except Exception:
                errors[cid] = traceback.format_exc(limit=3)
            ns["coach"], ns["D1"] = no_coach, NoD1()
    return ns, errors


class Replay:
    """Hands back saved answers in order; one queue per run, used one after another."""
    def __init__(self, runs, ns):
        self.calls = [c for r in runs for c in r["calls"]]
        self.ticks = [k for r in runs for k in r["ticks"]]
        self.prompts = []
        key = {(v.split(": ")[-1], int(k.split("_")[0][1:])): k for k, v in ns["ACTIONS"].items()}
        self.key = key

    def coach(self, prompt, config=None):
        self.prompts.append(prompt)
        if not self.calls:
            return "Next: (no saved answer)", "", 1000.0, {}
        c = self.calls.pop(0)
        return c["text"], c.get("thinking", ""), c["ready"] - c["t"], {}

    def system_one(self, state, qs):
        self.prompts.append("d1 " + hashlib.sha1(json.dumps([state, qs], sort_keys=True).encode()).hexdigest())
        k = self.ticks.pop(0)
        probs = {self.key[(a, s)]: p for a, s, p in k["d1"]}
        return {"answers": {"next_action": {"probabilities": probs}, "next_step": {"choice": f"step{k['d1_step']}"},
                            "should_speak": {"noul": k["speak"]}}}


def compare(new, old, label):
    bad = []
    if len(new["calls"]) != len(old["calls"]):
        bad.append(f"{label}: {len(new['calls'])} calls vs {len(old['calls'])} saved")
    for a, b in zip(new["calls"], old["calls"]):
        for key in CALL_KEYS:
            if key in b and a.get(key) != b.get(key) and not (key == "ready" and abs(a[key] - b[key]) < 1e-6):
                bad.append(f"{label}: call at {b['t']:.0f} s, {key}: {str(a.get(key))[:60]!r} vs {str(b.get(key))[:60]!r}")
    if len(new["ticks"]) != len(old["ticks"]):
        bad.append(f"{label}: {len(new['ticks'])} ticks vs {len(old['ticks'])}")
    for a, b in zip(new["ticks"], old["ticks"]):
        for key in TICK_KEYS:
            x, y = a.get(key), b.get(key)
            if key == "wm":   # tied probabilities sort differently on this machine than on the GPU's: compare the values
                x, y = [p for _, p in x or []], [p for _, p in y or []]
            if key in b and x != y:
                bad.append(f"{label}: tick {b['t']:.0f} s, {key}: {str(a.get(key))[:60]!r} vs {str(b.get(key))[:60]!r}")
    return bad


def replays(ns):
    """(label, saved run files in the order the code runs them, function that reruns them) per pinned stage."""
    vid, sfx = ns["VIDEO_ID"], ns["TAGS_SUFFIX"]
    res = BOX / "results"
    out = [("stage 26 every 10 actions", [res / f"coach_events_N10{sfx}_{vid}.json"], lambda: [ns["run_events"](10)]),
           ("stage 31 timing+loops", [res / f"coach_adaptive_timing_loops{sfx}_{vid}.json"],
            lambda: [ns["run_adaptive"](**ns["ADAPTIVE_VARIANTS"]["timing+loops"])]),
           ("stage 35 reminders", [res / f"coach_adaptive_remind{sfx}_{vid}.json"],
            lambda: [ns["run_adaptive"](**ns["REMIND_RUNS"]["remind"])])]
    omit = ns["OMIT"].get(vid, [])
    files = [res / f"coach_adaptive_remind_parallel{sfx}_{vid}.json"] + [res / f"coach_omit{k + 1}_parallel{sfx}_{vid}.json" for k in omit]
    def stage40():
        saved = {f: f.read_bytes() for f in files}
        for f in files:
            f.unlink()
        try:
            ns["RERUN_PARALLEL"] = True
            got = ns["parallel_runs"]()
            return list(got.values())
        finally:
            for f, b in saved.items():
                f.write_bytes(b)
    out.append(("stage 40 parallel reminders", files, stage40))
    return out


def main(mode):
    sandbox()
    record = RECORD
    recorded = json.loads(record.read_text()) if mode == "check" and record.exists() else {}
    prompts, problems = {}, []
    for video, recipe in DISHES:
        ns, errors = setup(video, recipe)
        for cid, e in errors.items():
            problems.append(f"{video[:3]} cell {cid} failed:\n{e}")
        for label, files, rerun in replays(ns):
            if not all(f.exists() for f in files):
                problems.append(f"{video[:3]} {label}: saved files missing"); continue
            saved = [json.loads(f.read_text()) for f in files]
            rep = Replay(saved, ns)
            ns["coach"], ns["D1"] = rep.coach, rep
            with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet):
                try:
                    new = rerun()
                except Exception:
                    problems.append(f"{video[:3]} {label} crashed:\n{traceback.format_exc(limit=4)}"); continue
                finally:
                    ns["coach"], ns["D1"] = no_coach, NoD1()
            for n, o, f in zip(new, saved, files):
                bad = compare(n, o, f"{video[:3]} {f.name}")
                problems += bad[:5] + ([f"... {len(bad) - 5} more"] if len(bad) > 5 else [])
            key = f"{video} {label}"
            prompts[key] = rep.prompts
            if mode == "check" and key in recorded and recorded[key] != rep.prompts:
                diff = next(i for i, (a, b) in enumerate(zip(rep.prompts + [None] * 99, recorded[key] + [None] * 99)) if a != b)
                problems.append(f"{key}: prompt {diff} differs from the recorded one")
            print(f"{video[:3]} {label}: {sum(len(r['calls']) for r in new)} calls replayed, "
                  f"{sum(len(r['ticks']) for r in new)} ticks", flush=True)
    if mode == "record":
        record.write_text(json.dumps(prompts))
        print(f"recorded {sum(map(len, prompts.values()))} prompts and d1 inputs")
    print("\n".join(problems) if problems else "PIN OK: every replayed run matches its saved results" +
          (" and the recorded prompts" if mode == "check" else ""))
    return not problems


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1] if len(sys.argv) > 1 else "check") else 1)
