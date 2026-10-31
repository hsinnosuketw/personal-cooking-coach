# Hack plan: a 3D cooking-agent game on the World-Model Coach

> **Pitch:** an agent inside a cooking game; its cooking actions are numerical vectors; a
> chatbot-like world model coaches it to cook better; rendered in 3D so people can watch it
> improve.
> **Researched:** 2026-10-30 · **Deadline:** Wed Nov 4, 2026, 9:00 PM ET (= Nov 5 02:00 UTC;
> README.md:129-132)

## 1. Verdict
**Yes, and about 80% of the pitch already exists here under other names.** The repo has a
cooking agent with a hidden skill vector, actions defined as numeric vectors, a learned world
model that plans the agent's practice, and an LLM bridge that voices the plan. What's missing:
(1) the 3D scene, (2) an explicit **execution vector** (what the chef's hands did each session),
(3) the live Muse Spark voice (still templates: IMPLEMENTATION_ISSUES.md §五.3).

Carry over the repo's rule: **the world model decides, the LLM speaks** (conversation.py:9-11).
The chatbot never invents the curriculum.

## 2. Pitch → existing code
| Pitch term | Already implemented as | Where |
|---|---|---|
| Cooking agent | Simulated learner: hidden skills s = [knife, heat, timing] ∈ [0,1]³, learns by s' = s + α ⊙ w_a · g(s,a) ⊙ (1−s) | `TrueLearnerEnv` benchmark.py:64-103; JS `makeEnv`/`envStep` index.html:513-530 |
| Actions as numeric vectors | 5 actions, each an exposure vector `weights` ∈ ℝ³ plus a prerequisite vector `min_prereq` ∈ ℝ³ | `ACTIONS` benchmark.py:39-45; index.html:478-484 |
| Meals / cuisines | `easy_recipe`, `stretch_recipe` (compound, prerequisite-gated) vs. 3 single-skill drills | same |
| "How well it cooked" | Noisy observation vector o = clip(s' + 𝒩(0,σ²)) plus a scalar session score | `step()` benchmark.py:87-99 |
| World model | Coach B: Kalman belief 𝒩(μ,σ²) over skills, learned rates α̂, learned gate strength `gate_hat` (starts at 0), 2-step lookahead | `LearnerWorldModelCoach` benchmark.py:126-190 |
| Chatbot that teaches | Bridge 2: belief + plan → LLM system prompt; Muse voice with offline fallback. Bridge 1: free text → obs vector | conversation.py:91-107, 74-88, 33-71 |
| Baselines | Coach A (UCB bandit, no model); Oracle (plans on the truth) | benchmark.py:106-123, 193-216 |
| Visual front end | 2D canvas race, session inspector, belief bars, scripted chat. **No 3D.** | index.html (1180 lines; sim core :477-730) |
| Learner variety | `ARCHETYPES` steady/fast/slow/noisy; `forget_rate` (off by default) | benchmark.py:51-56 |
| Real-data path | ASSISTments/Junyi loaders → BKT fit → A/B/Oracle replay | datasets.py, bkt.py, replay.py |

## 3. Measured facts (this machine, 2026-10-30)
- `python3 test_benchmark.py` → 8/8 pass; `python3 test_replay.py` → 4/4 pass.
- Python 3.13.2, numpy 2.3.0, torch 2.9.1, fastapi 0.124.2, uvicorn 0.38.0, websockets 15.0.1;
  Node 22.22.0, npm 10.9.4. No gymnasium; no Godot, Unity or Blender.
- jsdelivr serves `three@0.169.0` `build/three.module.js` and
  `examples/jsm/controls/OrbitControls.js` (HTTP 200, `access-control-allow-origin: *`).
- The folder is **not a git repo** (`git log` → "not a git repository").
- The JS sim core's only UI dependency: `envDrift` reads the global `currentOpts.lrScale`
  (index.html:520; called at :680 and :1016).
- **JS port (what the 3D page will run)**, 40 seeds, run in Node: sessions 3–9 mean B−A
  **−0.138**, sessions 11–20 **+0.118**; S20 A 1.38 / B 1.55 / Oracle 1.65; S40 A 1.51 / B 1.68.
  Python gives −0.151 / +0.113, so the claim survives the port. Per-seed numbers differ
  (different RNG; index.html footer).
- **Demo-seed scan (JS)**: 27 of 41 seeds (0–39, 42) show a clean crossover (early B−A < 0,
  late > 0, B ahead from S≤12 through S20, ahead at S40). **Seed 7 is the best demo seed**:
  early −0.155, late +0.266, B ahead from **S9**, B−A at S40 +0.233. B attempts the stretch
  recipe "before ready" (true gate < 0.5) at S1, 2, 3, 4, 6. Seed 21 has no lead by S20
  (late −0.086), and B only edges ahead after the drift (+0.041 at S40). That makes it a good
  "honest edge" seed.
- **B repeats itself**: in JS seeds 3, 7, 12, 21 and 42, B cooks `stretch_recipe` in 33–34 of the
  34 sessions from S7 to S40. In the full Python seed-7 run it's 34/34, and the true gate stays at
  1.00 from S9 to S40, *including after the drift*. Dish quality, not dish choice, has to carry
  the visuals.
- B's heat observation, JS seed 7: 0.16 (S1) → 0.57 (S9) → 0.86 (S20) → 0.58 (S21, new stove)
  → 0.79 (S40).

## 4. Gap to close
1. 3D scene and chef avatars (nothing exists yet).
2. A per-session **execution vector**: the visible "what the agent did" that the pitch asks for.
3. A live Muse voice through a key-safe endpoint. The browser can't hold `MODEL_API_KEY`, and
   CORS would block a direct call anyway.
4. The JS sim core is inline in index.html and has the hidden global above. Extract and
   parameterize it before a second page uses it.

## 5. Architecture (recommended)

### 5.1 Agent and vectors
**Decision (2026-10-30):** the chef agent **is** the existing learner, with execution vectors
added for display, so the validated dynamics, the tests and the crossover claim all stay
intact. A trainable motor-policy chef is post-deadline work (§6). Per session:

```
coach picks a_t = (w_a, p_a)         ← action vector (existing)
s_t ──validated dynamics──▶ s_{t+1}   ← hidden skill vector (existing)
o_t = noisy plate quality             ← what the coach observes (existing)
u_t = decode(o_t, a_t) + jitter       ← execution vector, render-side only (NEW)
```

There are two visual layers, and the split stays explicit on screen:
- **Coach's view**: plate, char, dice and timer come from o_t, so viewers see what the coach saw.
- **Truth layer**: the flare-up comes from the hidden true gate, and the XP burst from the hidden
  true gain. Both are labeled "truth" on screen. Put XP behind the x-ray toggle (along with the
  true skill bars) if the "coach's view only" rule should hold strictly.

| Component | Formula (q = o_t) | 3D visual |
|---|---|---|
| `cut_spread` | 0.05 + 0.55·(1 − q_knife) | spread of dice sizes on the board |
| `pan_temp_c` | 180 + 140·(1 − q_heat) | continuous colour ramp: golden 180 °C → brown 230 °C → black 290 °C; smoke ∝ (T − 220)/80 |
| `late_s` | 45·(1 − q_timing) | late ingredient drop; boil-over and red timer past 20 s |
| `ready` | true gate g(s_t, a_t) (environment physics) | g < 0.5 → "attempted before ready": pan flare-up, chef stumbles |
| `learned` | Δ cumulative true gain this session | size of the XP burst into the chef |

- Only stations with w_{a,k} ≥ 0.3 animate: a drill uses one station, a recipe uses all three.
  A numeric readout under each kitchen ("pan 298 °C · dice ±24 % · 30 s late" at S1) shows the
  pitch's "quantified vectors" literally.
- On the default archetype, knife starts at 0.65, so dice spread only moves from about 24 % to
  8 % and the board barely changes. Heat and timing carry the story.
- JS seed-7 heat calibration: S1 298 °C (black + smoke), S9 240 °C, S20 200 °C (golden),
  S21 239 °C (brown + smoke again: the new stove), S40 209 °C. Use a continuous ramp, not a
  threshold, so the S20 → S21 drift beat stays visible.

### 5.2 Sim engine: extract the JS port
- Move index.html:477-730 (`SKILLS` … `aggregate`) verbatim into **`sim-core.js`** and load it as
  a *classic* `<script src>`, not an ES module. Local module imports fail under `file://`, and
  index.html has to keep opening by double-click. Top-level declarations stay global, so the
  rest of index.html runs unchanged.
- Change `envDrift(env)` to `envDrift(env, o)` using `o.lrScale`, and update both call sites.
- End with `globalThis.SimCore = {…}` so Node can `require` it for parity tests.
- Add `execVector(obs, action, gate, gain, rng)` and `trace(seed, opts)`.
  `runEpisode(kind, seed, o, 40, true)` already records per-step `obs`, `env.gate`, belief,
  `gateHat` and `alphaHeat` (index.html:674-719).

### 5.3 3D page: `game.html`
- Load three@0.169.0 and OrbitControls through an inline importmap from jsdelivr. Build
  everything from primitives (box counters, cylinder pans, capsule chef with a hat), so there's
  no asset pipeline and no licensing.
- **Two kitchens side by side, same learner seed.** The left chef is coached by Bandit A, the
  right chef by World-Model B. The Oracle appears only as a line in the HUD chart.
- Each session takes about 3 s: the action card flips up (w_a and p_a as small bar triplets),
  the chef walks to the station(s), u animates, the plate lands with a quality ring, and the
  coach's speech bubble appears.
- HUD as a DOM overlay:
  - play, step, speed and a session scrubber (1–40)
  - B's belief bars μ ± σ vs. truth (x-ray toggle)
  - a `gate_hat` dial (true 6.0) and α̂_heat (true 0.14 → 0.055)
  - a mini A/B/Oracle gain chart with a synced pointer
  - a "New stove" banner and stove swap at S21

### 5.4 Coach voice: `serve.py` (stdlib, no new dependencies)
- `python3 serve.py [--port 8000]` binds 127.0.0.1 and serves the folder. It adds
  `POST /api/coach {system_prompt, fallback}`, which calls `generate_coach_reply()`
  (conversation.py:74) and returns `{text, live}`. Page and endpoint share an origin, so CORS
  needs no setup.
- The browser builds the prompt the way index.html:1018-1020 already does, plus one
  execution-vector line ("pan hit 298 °C vs 180 target; dice spread 24 %; 30 s late").
- Over `file://`, or when the call fails, the bubble shows the template line tagged
  `[offline template]`. A successful call is tagged `[live Muse]`. Cache replies per
  (seed, session) so scrubbing doesn't re-bill and the video is reproducible.
- Coach A keeps template lines because it has no belief to explain. Coach B gets the Muse voice.

### 5.5 Demo beats (3-minute video, seed 7)
1. Two identical chefs with the same skills.
2. S1–6: B's chef attempts the stretch recipe "before ready": flare-ups and tiny XP while its
   `gate_hat` dial climbs. A's chef drills and leads.
3. S9: B passes A, and B's plates turn golden.
4. S21: new stove. Char returns in both kitchens; B's σ bars widen, then shrink.
5. S40: B is ahead and close to the Oracle.
6. Closing card: the crossover is a property of this cooking setup. On BKT-fitted data B leads
   from the start (README.md:50-54), which is why the method is "test it per dataset" (§五.5).

Narrate only numbers the page computes (JS RNG), never the EXPERIMENT.md tables.

## 6. Day by day (Fri Oct 30 → Wed Nov 4, 9 PM ET)
| Day | Work | Done when |
|---|---|---|
| Fri 10/30 | `git init` + baseline commit; record parity numbers; extract `sim-core.js`; fix `envDrift` | index.html looks unchanged; Node parity identical |
| Sat 10/31 | `game.html`: importmap, two kitchens, chefs, camera, session loop + scrubber on `SimCore.trace` | 40 sessions play for both chefs |
| Sun 11/1 | Execution-vector visuals (char/smoke, dice, timer), XP burst, "before ready" beat, stove swap, HUD | S1, S9 and S21 read correctly with the sound off |
| Mon 11/2 | `serve.py`, live Muse, cache, tags (needs `MODEL_API_KEY`, §五.3) | both the live and offline tags observed |
| Tue 11/3 | Record the video on seed 7; add a "3D game" section to README; screenshots | the cut follows §5.5 |
| Wed 11/4 | Buffer; public repo; submit before 9 PM ET | index.html roadmap §6 checklist ticked |

Stretch goals, only if ahead of schedule:
- The chef's self-report text goes through `extract_skills_offline`, putting Bridge 1 on screen.
- Muse Image dish photos per quality tier (the hackathon stack lists Muse Image, EXPERIMENT.md:58).
- A "you be the coach" mode (index.html roadmap §2).

After Nov 4:
- A trainable motor-policy chef (continuous heat, chop and timing per frame; torch is
  available) with the world model as teacher.
- A "menu pack" of cuisine vectors behind a flag. New actions change the benchmark, so re-run it
  and report the results honestly.

## 7. Risks
| Risk | Mitigation |
|---|---|
| JS RNG ≠ NumPy, so per-seed numbers differ from EXPERIMENT.md | Narrate page-computed numbers only; seed 7 is verified clean in JS |
| B's kitchen looks static (`stretch_recipe` 34× in a row) | Quality-driven visuals (§5.1), the drift beat, fast-forward through S12–19 and S25–39 |
| No `MODEL_API_KEY` on demo day | Offline templates with a visible tag; cached live replies for the video |
| `file://` limits | Classic-script core; three.js from the CDN (needs network), or `serve.py` with a vendored copy |
| Breaking the working index.html | Extraction-only diff plus a parity check before any feature work |
| Scope creep into RL | The motor-policy chef is explicitly post-deadline |
| Port clash (8765 is AnkiConnect, §四) | `--port` flag, default 8000 |

## 8. Open questions
The six items in IMPLEMENTATION_ISSUES.md §五 still stand. This plan touches:
- #3: who holds `MODEL_API_KEY`
- #5: the plan uses the crossover as the main beat and the per-dataset method as the close
- #6: who records the video

New questions:
- Does `game.html` become the submission's front page, or is it linked from index.html?
- README.md:126-128 lists **Muse Code** as required tooling. Confirm on the official page how
  its use has to be shown.

## 9. Verification (for the build)
- `python3 test_benchmark.py` (8) and `python3 test_replay.py` (4) still pass; the Python is
  untouched.
- `node --check sim-core.js` passes. For Node parity, `SimCore.runEpisode("B", 7, opts).gains`
  equals the pre-extraction inline result for the same opts.
- index.html shows the same seed-7 verdict numbers (before/after screenshots with the `run` skill).
- `game.html` opened by double-click, online, with no key: the scene renders (three.js comes from
  jsdelivr) and coach bubbles show `[offline template]`. Via `python3 serve.py` with the key, they
  show `[live Muse]`.
- Offline check: `serve.py` plus a vendored three.js served over http, with the network off.
  The scene still renders.
- Visual spot checks on seed 7: S1 B charred with a flare-up; S20 golden; S21 char returns in
  both kitchens.
