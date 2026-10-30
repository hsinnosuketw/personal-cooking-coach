# World-Model Coach — toy benchmark for the Meta Global AI Developer Hackathon

**Interactive version:** open `index.html` for About, Training setup, Live race,
Model internals, Conclusion, and the conversation-bridge demo. The race has controls for
seed, noise, gate strength, learning-rate scale, and stove drift; the internals view pairs
session math with animated demonstrations.
Full write-up: `EXPERIMENT.md` / `EXPERIMENT-zh-TW.md`.

A runnable toy proving one claim: **an LLM coach with a learned learner
world-model beats a stateless bandit coach over long multi-session
horizons** — but only after it pays an early model-learning cost.

## Run it (30 seconds)

```bash
pip install -r requirements.txt
python3 demo.py benchmark   # A vs B vs Oracle table + results.png
                            # + results_inside.png (actions, belief vs truth)
python3 demo.py chat        # scripted multi-session conversation (Coach B)
python3 demo.py chat --live # voice the coach via Muse when MODEL_API_KEY
                            # is set, else offline templates (tagged)
python3 demo.py real-data data/assistments-2009.csv 5
                            # ASSISTments-format CSV -> fit BKT per skill ->
                            # replay A/B/Oracle on fitted dynamics
python3 demo.py real-data-junyi data/junyi_log.csv data/junyi_table.csv 2
                            # Junyi ProblemLog (+ optional exercise->KC table;
                            # headers auto-detected) -> fit -> replay
python3 test_benchmark.py   # 8 focused tests (incl. offline voice fallback)
python3 test_replay.py      # 6 real-data path tests (synthetic CSVs)
python3 test_serve.py       # 3 server tests (charsets, LAN rule, per-session replies)
```

No API key needed. Everything runs offline; the Meta Model API bridge
(extractor + coach voice) activates only when `MODEL_API_KEY` is set,
and every live call falls back to the offline path with a visible tag.

## 3D kitchen duel (`game.html`)

Two toy kitchens race through the same 40 sessions: Coach A (score
averages) on the left, World-Model Coach B on the right, with B's belief
bars, gate dial, the A/B/Oracle gain chart and per-session coach lines.
It runs the same simulation as `index.html` (`sim-core.js`).

```bash
python3 serve.py                  # http://127.0.0.1:8000/game.html (this Mac only)
python3 serve.py --host 0.0.0.0   # share on your Wi-Fi; prints the link to send
```

`game.html` needs the server (its ES modules can't load from `file://`);
`index.html` still opens by double-click. When shared on the network,
visitors get cached or template coach lines; live Muse calls stay on this
machine unless you start the server with `--token` and give it out. Only the
two pages and the files they link to are served: the git history, logs and
any keys in the folder return 404.

## Onion Sweat Challenge (`play.html`): gameplay → dataset → AI chef

A playable 3D stove with a goal: sweat the Pasta onion to translucent
(colour ≈ 0.30) without browning or scorching it, salt it while wet, and
serve before 600 s — faster scores more. Too much heat scorches the onion
before it browns, sooner with uneven dice. Keys: ←/→ heat, S salt, W water,
Enter serve, Space start.

```bash
python3 serve.py            # play at http://127.0.0.1:8000/play.html
python3 -m chef stats       # what the dataset holds
python3 -m chef evaluate    # learn a world model from the rounds, let the AI chef cook
```

Every 5 s of cooking is logged as (state, action, next state). **Save to
dataset** stores the round in `gameplay/episodes/`; the server validates it
and recomputes the score. `chef evaluate` trains a world model on those
rounds only, so it never sees the game's rules (`chef/physics.py`). It holds
out a fifth of the rounds to measure prediction error. Then an AI chef that
plans with the learned model plays 20 rounds in the real engine, and its
best runs are written to `ai_chef_runs.json` for the in-game replay.

The current `ai_chef_runs.json` was trained on scripted bot rounds
(`python3 -m chef bots`, then `evaluate --with-bots`). Those only prove the
pipeline works. Play real rounds, then rerun `python3 -m chef evaluate` to
get numbers worth reporting.

## Real student data (ASSISTments)

Network is blocked in this environment, so the pipeline is validated on
synthetic data in the exact ASSISTments 2009-2010 skill-builder schema
(`python3 demo.py make-synthetic /tmp/synth.csv`), ready for the real
file: download the skill-builder CSV, drop it in `data/`, and run
`python3 demo.py real-data data/<file>.csv`.

What the pipeline does (`datasets.py` + `bkt.py` + `replay.py`):

1. Load `(user, skill, correct)` sequences (`load_csv`, tolerant column names).
2. Fit per-skill Bayesian Knowledge Tracing by grid search; report fitted
   rates plus empirical learning curves (P(correct) by attempt number).
3. Replay Bandit A (UCB on observed correctness), World-Model B (BKT
   belief + expected-gain lookahead), and Oracle (true hidden mastery)
   on the fitted dynamics; report cumulative true mastery gain.

Honest finding on synthetic BKT dynamics: B beats A from the start there
(+0.90 by session 20) because binary BKT beliefs identify fast — there is
no gate-misspecification cost like the cooking toy's. The crossover is a
property of the cooking setup, not a universal law; the value of this
path is testing that claim per dataset instead of asserting it.

## Learner archetypes + forgetting (toy)

`benchmark.py` now ships `ARCHETYPES` (`steady`/`fast`/`slow`/`noisy`)
and an optional `forget_rate` (skills decay toward starting values;
default 0 = off). Use via `run_episode(..., archetype="slow")`.
Defaults are unchanged, so all original results reproduce exactly.

## What the numbers say (40 learners, sessions 1–40, drift at 20)

| Window | Mean B − A | Reading |
| --- | --- | --- |
| Sessions 3–9 | **−0.151** | Bandit A leads |
| Sessions 11–20 | **+0.113** | World-Model B leads |
| Session 20 | A 1.38, B 1.54, Oracle 1.65 | B near-oracle |
| Session 40 | A 1.53, B 1.68 | B still leads after drift |

Crossover is at ~session 11. Right panel of `results.png`: B's
`gate_hat` climbs 0 → ~6–8 (true value 6.0) and `alpha_hat` for heat
falls after the session-20 stove drift (true 0.14 → 0.055).

## Honest note: your snippet does not reproduce the crossover

Probed before building (probes in session, same equations):

* With the snippet's parameters, B leads from session 3 (+0.09 → +0.21)
  and spams `stretch_recipe`; both saturate near the 1.85 ceiling.
* Causes: weak gate (`exp(-3.5·shortfall)`), a flipped info-bonus sign
  (`var` grows in prediction, so the "bonus" is negative), fast Kalman
  correction, and learning rates so high that skills saturate by ~15.

Declared changes (all in [benchmark.py](/Users/samsam/Documents/muse-project/test/benchmark.py), each testable):

1. Gate strength 3.5 → **6.0**, learning rates scaled ×~0.55 so the
   late-horizon planning advantage has room to appear.
2. Coach B starts **misspecified** (`gate_hat = 0`, ignores
   prerequisites) and learns the gate from prediction error. That
   learning cost is what lets A lead sessions 3–9 — it is a stated
   assumption, not hidden tuning.
3. Bandit reward = simulator session-score jump (your env's
   `observed_gain`), matching the spec's "high initial score jump".

Not reproduced: the "B struggles on 7/20 slow/noisy learners" claim.
Measured B-losses at session 20: 2/40 (noise 0.05), 1/40 (0.12), 0/40
(0.18). The Kalman coach is noise-robust here; treat 7/20 as unproven
until learner archetypes (varied `s0`, `alpha*`) are added.

## How it maps to a real multi-session LLM coach

* [conversation.py](/Users/samsam/Documents/muse-project/test/conversation.py) Bridge 1: learner text →
  `obs_skills`. Offline keyword extractor by default;
  `extract_skills_llm()` calls Muse Spark structured extraction when
  `MODEL_API_KEY` is set (`https://api.meta.ai/v1`, OpenAI-compatible).
* Bridge 2: `build_coach_prompt()` injects belief state, `alpha_hat`,
  `gate_hat`, and the 2-step plan into the LLM system prompt, so the
  LLM voices the world model's decision instead of improvising.
* In `demo.py chat`, belief updates use simulator observations; the
  text-extracted obs is printed alongside. In production (no simulator)
  the text-extracted obs becomes the update input — one-line change.

## Hackathon fit (official page, read 2026-10-28)

Source: [Meta Global AI Developer Hackathon](https://dev.meta.ai/events/global-hackathon)
("Win $1M: Meta Global AI Developer Hackathon").

* **Track 1 — Indie developer**: "Judged on creativity, technical
  ambition, and whether it works." This toy is built to that bar:
  novel mechanism, real math, runs today.
* **Themes**: *Build for Your World* (a coach that remembers you across
  sessions) with a *Push the Frontier* angle (learned world models as
  the memory/planning layer for LLM agents).
* **Required tooling**: Muse Spark series via Meta Model API, Muse
  Code. This project uses Muse Spark for extraction/coaching voice;
  the world model is the differentiator prompting alone cannot give.
* **Dates**: hackathon Oct 26 – Nov 4, 2026; submissions due
  **Nov 4, 9:00 PM ET**; judging Nov 4–8; winners Nov 9. Virtual,
  worldwide, free if selected (20,000 cap; some countries excluded —
  check the official page for eligibility).

## Next steps toward a submission

1. Record `MODEL_API_KEY`, switch extractor + coach voice to live
   Muse Spark calls; keep the offline fallback for the demo video.
2. Add learner archetypes (varied `s0`/`alpha*`/noise) and re-test the
   "B loses on slow/noisy learners" claim honestly.
3. Thin web UI: belief chart + chat pane updating across sessions.
4. Demo video script: sessions 1–9 (bandit winning) → session 11
   crossover → stove drift → B adapts, bandit doesn't.
