---
name: project-structure
description: Where code, notebooks, data, results and the demo site go in this repo, and how to move notebook code into the package. Use this whenever you add a file, a module, an experiment stage, a notebook cell, a result file or a test here, when you refactor or move code, when you wonder "where should this live?", and before writing more than a few lines of logic inside a notebook cell — even if the user doesn't mention structure.
---

# Project structure

This repo follows the [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/) layout, adapted to a cooking coach built on a world model, an LLM coach and a decision model. The goal: anyone can find a piece of logic by what it does, rerun any result from a notebook that only *calls* the package, and keep large or private files out of git.

## Layout

```
README.md                    what it is, how to run it (keep the "Run it" commands working)
pyproject.toml               package metadata (pip install -e .); requirements.txt stays for Colab/pip -r
src/coach/                   the Python package ("src layout"): ALL reusable logic lives here; imports read `from coach...`
  config.py                  paths (ROOT, DATA_RAW, DATA_PROCESSED, RESULTS, SITE); later model names and tunable constants
  domain.py                  shared types (StepSpec, Prediction…)
  data/                      getting and reading inputs: fetch, HD-EPIC/EPIC annotations, vocab, recipes
  perception/                world model + probe, step tracker, HSMM, action segments
  memory/                    the checklist (ledger, camera rule, order rule, loops), event memory
  coaching/                  LLM coach: clients (NIM, self-hosted), prompts, answer parsing, task graph
  decision/                  d1 decision model: state, questions, decide
  timing/                    when to call the coach: triggers, suppression, back-off, the run loop
  vision/                    frame checks: frame reader, contact sheets, vision-model backends
  render/                    video rendering, the demo-site export and the demo server
  evaluation/                metrics against annotations (tracker, memory, reminders, omissions), VLM comparisons
notebooks/
  pipeline.ipynb             the experiment log: each stage = markdown (why, input, output, result) + a short code cell
data/                        gitignored
  raw/                       downloads as fetched: videos, annotation files, weights (never edited)
  processed/                 derived inputs: per-second predictions (.npz), step tags, task graphs
results/                     gitignored: run outputs (coach_*.json, looks_*.json), rendered videos
site/                        the demo page (index.html is tracked; coach.js and videos are built)
tests/                       pytest; no network, no GPU, no downloaded data unless marked
scripts/                     command-line helpers (build_bundle.py packs src/coach into the notebook; replay_pin.py pins behaviour)
archive/                     earlier prototypes; read-only, not imported by src/coach/
.claude/skills/              project skills like this one
```

## Where does it go?

| You are writing… | Put it in | Not in |
|---|---|---|
| A function used by more than one stage, or longer than ~10 lines | `src/coach/<area>/` | a notebook cell |
| A tunable number (threshold, window, model name) | `src/coach/config.py` or a dataclass default in its module | scattered literals |
| A prompt template | `src/coach/coaching/prompts.py` | inline f-strings in cells |
| Something that reads a file path | take the path as an argument; defaults come from `config.py` | `ROOT / "jepa/results/..."` inside logic |
| A metric that compares to annotations | `src/coach/evaluation/` | the run loop |
| A new experiment | a new notebook stage that calls package functions | a new copy of an existing function with one change |
| A downloaded file | `data/raw/` via `python3 -m coach.data.fetch` | git |
| A run's output | `results/` with the run's settings saved inside the JSON | git, `data/` |
| A demo asset | built into `site/` by `coach.render.site` | hand-copied files |

## Rules for code in `src/coach/`

- **No hidden globals.** Notebook code relied on globals (`pred`, `texts`, `truth`, `SEGMENTS`, `STEPS_OF`…). In the package, pass them in. Group the per-video inputs in one object (e.g. `Episode`: video id, recipe, step texts, predictions, annotations, action bank) and the per-run settings in a dataclass, so a function's inputs are visible in its signature.
- **Causality is part of the interface.** Anything used live (`perception`, `memory`, `timing`, `vision`) must only read data up to time t. Name such functions after what they see (`step_posterior_until(t)`), and keep annotation-reading code in `evaluation/` only.
- **One home per concept.** Before adding a function, search for an existing one; extend it with a parameter rather than copying it (the notebook had three `finished_by` copies).
- **Side effects at the edges.** Model calls (NIM, vLLM, d1, vision) go through small client classes that can be swapped for fakes; the logic takes a client argument. File writes happen in the notebook or a runner function, not deep in helpers.
- Keep the existing style: short docstrings that say *why*, type hints, plain functions over class hierarchies.

## Rules for notebooks

- A code cell **calls** the package and **shows** results: set parameters, call one or two functions, `display()` the table. If a cell grows a `def`, move it into `src/coach/`.
- Each stage's markdown keeps the experiment record: why it exists, input → output, and the result numbers with the date. That record is the notebook's job; the code is the package's.
- Stage numbers stay stable once results cite them; add new stages at the end.
- Colab gets the package from the notebook's `BUNDLE` (rebuilt by `python3 scripts/build_bundle.py` after any change under `src/coach/`) or by `pip install git+…`, never by pasting code into cells.

## Data and results

- `data/raw/` is immutable: re-download rather than edit. Check large downloads (size or checksum) before use.
- Every results file records the settings that produced it (`settings` in the JSON), so an old file can be explained without the code version.
- Large or licensed media (HD-EPIC videos, rendered videos) never enter git history. The public site gets re-encoded copies on the `gh-pages` branch only.
- Secrets live in `.env` (gitignored) and are read from the environment; never print them or pass them on command lines that show up in logs.

## Tests

- `tests/` mirrors `src/coach/` (`tests/memory/test_checklist.py`…). Tests put `src/` on `sys.path` so they run without installing. Fast tests use fakes for models and tiny synthetic episodes; tests that need downloaded data skip when it's absent.
- When moving notebook code into the package, first pin its behaviour: run the old cell and the new function on the same input and compare outputs (a saved results JSON is a good fixture).

## Refactoring checklist (moving notebook code into `src/coach/`)

1. Pick one area (e.g. memory). List the notebook cells and globals it uses.
2. Write the module with explicit inputs; keep names and behaviour identical first, improve second.
3. Add a test that reproduces a saved result (same input → same output). For anything the run loops touch, run `python3 scripts/replay_pin.py record` before the move (or with `PIN_NOTEBOOK=<copy of the old notebook>`) and `check` after: it replays the saved runs with the saved coach and d1 answers and compares every tick, prompt and d1 input.
4. Replace the cell's body with an import and a call; run `python3 scripts/build_bundle.py`; rerun that stage locally.
5. Commit that area alone, then move to the next.
