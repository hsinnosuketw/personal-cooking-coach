# Cooking coach on a V-JEPA 2 world model

A coach that watches someone cook through a head-mounted camera, remembers which recipe steps they have started, and reminds them of steps they haven't. A world model reads the video, an LLM coach decides what to say and when, and a small decision model turns the advice into the next move every second. Built for the Meta Global AI Developer Hackathon.

**Demo:** https://hsinnosuketw.github.io/personal-cooking-coach/ — two HD-EPIC recordings (Scrambled Eggs, Bacon & Egg Sandwich), each with several coach versions side by side.

## How it works

```
cooking video ─► V-JEPA 2 ViT-L ─► EK100 probe ─► verb / noun / action probabilities, every second
                  (world model)       │
                                      ├─► action segments ─┐
                                      ├─► HSMM step tracker ├─► timing: should the coach speak now?
                                      └─► checklist memory ─┘        │
              frames ─► Llama 3.2 11B Vision ─► "has this step begun?" (when the evidence is unclear)
                                                                      ▼
recipe ─► task graph (which steps repeat) ─────────────► coach: Muse Glimmer 30B
                                                         (what's done, what's left, one reminder)
                                                                      ▼
                                                         decision model: Liquid AI d1-2B, every second
```

| Part | What it does | Model |
|---|---|---|
| World model + probe | Predicts the next action about 0.8 s ahead from the last 3.2 s of video | Meta V-JEPA 2 ViT-L with the EPIC-KITCHENS-100 attentive probe |
| Memory | A checklist: each step not started / in progress / done, with rounds for repeated steps and the times each was first and last seen | rules over the probe, plus the coach's answers |
| Frame checks | When a step's evidence is unclear (first sign, stops early, restarts, long silence), looks at 4 frames from the last 20 s and asks whether the step has begun | Llama 3.2 11B Vision, ~1 s per check |
| Timing | Calls the coach on a step change, on drifting from the advice, on a skipped step or long off-task time, with a back-off when nothing changes | HSMM step tracker + rules |
| Coach | Writes where the cook is, the one most useful next thing, and a `REMIND` line for a step not started yet | Muse Glimmer 30B (self-hosted with vLLM, or NVIDIA NIM) |
| Decision model | Every second, picks the next action from the recipe's action bank, following the coach and the checklist | Liquid AI d1-2B |

## Where things are

```
src/coach/               the Python package (pip install -e .)
  config.py              where data, results and the site live
  domain.py              shared types (steps, predictions)
  data/                  downloads, EPIC-KITCHENS/HD-EPIC annotations, class vocabulary, recipe extractors
  perception/            V-JEPA 2 + probe, per-second predictions, action bank, step tracker, action segments, HSMM
  memory/                the checklist: camera rule, order rule, the coach's answers, rounds of repeated steps
  coaching/              Glimmer client, prompts, answer parsing, task graph, parallel-aware reminders
  decision/              d1's choices, questions and state
  timing/                when to ask the coach: events, suppression, back-off, wrap-up
  vision/                frame checks: contact sheets, the vision model, its cache
  render/                guide/truth videos, demo frames, the demo server
  evaluation/            scores against the annotations: goals, tracking, advice, start rules, skipped steps, upper bounds
notebooks/pipeline.ipynb the experiment, stage by stage (1–40): why, input, output and the measured result
data/raw/                downloads (git-ignored): weights, videos, annotation files
data/processed/          derived inputs (git-ignored): per-second predictions, step tags, task graphs
results/                 run outputs and rendered videos (git-ignored)
site/                    the demo page; coach.js and the videos are built into it from results/
tests/                   offline tests (no torch, no network)
scripts/                 build_bundle.py packs src/coach into the notebook; replay_pin.py checks a refactor
archive/                 earlier prototypes (POMDP benchmark, 3D kitchen, onion game, live-coach)
.claude/skills/          project skills; project-structure says where new code goes
```

Notebook cells call the package. What stays in cells is orchestration: the per-second run loops (`run_events`,
`run_adaptive`) and the experiments that swap a run's inputs (skipped steps, the perfect probe, parallel reminders).
`python3 scripts/replay_pin.py check` replays the saved runs of both dishes through the notebook's code with the saved
coach and d1 answers, and confirms every tick, prompt and d1 input is unchanged.

### Notebook stages

| Stages | What |
|---|---|
| 1–11 | Setup, download, world model, per-second predictions, recipe steps, action bank, step tracker |
| 12–19 | Latency, the Glimmer coach, d1, coach settings, the timeline, the combined video, demo export |
| 21–26 | Checklist memory, action segments, event memory, coaching every N actions (3 / 5 / 10) |
| 27–31 | Recipe loops, HSMM step tracking, a checklist that counts rounds, three-layer intent, adaptive timing |
| 32, 37 | Upper bounds: annotated events (32) and annotations as a perfect probe (37) |
| 33–36 | Scoring by the goals (remember started steps, remind unstarted ones), memory rules, the reminder coach, skipped-step tests |
| 38–39 | Frame checks with a vision model, and a coach that can ask for one |
| 40 | Parallel work: a step is only reminded once a step that needs it is under way (task graph with prerequisites) |

## Run it

On a laptop (no GPU):

```bash
pip install -e .                                   # the coach package (src/coach)
for t in tests/test_*.py; do python3 $t; done      # offline tests
python3 -m coach.data.fetch --annotations-only     # EPIC-KITCHENS + HD-EPIC labels and recipes into data/raw/
python3 -m coach.render.serve --port 8080          # the demo page on http://127.0.0.1:8080 (videos seekable)
```

The models run on a Colab GPU from VS Code (Google Colab extension → Select Kernel → Colab):

- **T4**: world model predictions, d1, the coach through NVIDIA NIM.
- **A100 40 GB**: self-hosted Glimmer (vLLM, FP8, text only) next to d1.
- **A100 80 GB (High-RAM)**: Glimmer, d1 and the 11B vision model together (stages 38–39).

Open `notebooks/pipeline.ipynb` and run it top to bottom. Stage 1 unpacks the package on Colab (after changing `src/coach/`, run `python3 scripts/build_bundle.py`). Stage 2 picks the video and recipe. Each stage reuses saved results in `results/` unless its `RERUN_*` flag is set. The NIM key is read from `.env` (`NVIDIA_API_KEY=...`).

## Results so far (measured, small samples)

All on HD-EPIC with its annotated step tags, one run per setting. Coach answers vary from run to run, so differences of a few points are noise.

| What | Result |
|---|---|
| Probe, action in the top 5, 1 s before it starts | 48% on EPIC-KITCHENS (the probe's own domain) vs 10–14% on HD-EPIC; objects suffer most |
| Coach latency | ~14 s self-hosted (A100), ~32 s on NIM; d1 57 ms per decision; a frame check ~1.1 s |
| Skipped-step test (a step's evidence removed) | Reminded 2 and 18 s after it was due (Bacon & Egg), 114 and 279 s (Eggs) |
| Reminders before the cook starts a step | 3/5 (Eggs) and 4/6 (Bacon & Egg) steps, up from 0–1 and 1–3 |
| Frame checks (11B) on memory | "Has it begun?" judged right 89% (Eggs). Bacon & Egg steps were recorded 87 s too early before; now 6 s late |
| Perfect-probe ceiling (annotations as the probe) | Eggs: 6/7 steps remembered, 7 s late |

The main limits: the probe reads HD-EPIC kitchens far worse than the EPIC-KITCHENS footage it was trained on, and fetching actions (take pan, take knife) make steps look started before they are. Frame checks address the second problem.

## Data and licences

EPIC-KITCHENS-100 and HD-EPIC are CC BY-NC 4.0 (non-commercial). The raw videos are kept out of git. The demo site shows re-encoded recordings from HD-EPIC (Damen et al., University of Bristol) for non-commercial research demonstration. V-JEPA 2 code and weights are MIT. Muse Glimmer, Llama 3.2 Vision and d1 are used under their own licences. Keys live in `.env` (git-ignored).
