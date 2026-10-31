# Live cooking coach (即時料理教學) — foundation slice

The real-time coaching track, built alongside the 3D kitchen duel. It
corrects mistakes while someone cooks, remembers skills across recipes
(Pasta Pomodoro → the Curry onion base), and compares B0 / S1 / A1 fairly.
Everything below runs offline with no API key.

```bash
python3 -m livecoach.server        # http://127.0.0.1:8100/ — demo page + JSON API
python3 -m livecoach.evaluate      # B0 / S1 / A1 table on the dev cases
python3 test_livecoach.py          # 10 tests
```

## How a decision is made

```
ObservationEvent (camera | transcript | manual | replay)
  → state.py      facts with status + source; conflicts kept; versioned
  → policy rules  smoke / burnt → lower the heat (no model call)
  → candidates    2–3 feasible moves, always including "keep watching"
  → world model   one call compares them (cache keyed on recipe, step,
                  rounded facts, skill levels, candidate set)
  → policy        ask if the unknown fact changes the advice; otherwise
                  risk → goal → teaching value → interruption cost
  → Decision      one action line + one reason line, tagged rule/cache/model
  → response / step outcome → belief.py (only observed outcomes move a level)
```

Skill levels: unknown → needs_prompt → guided_success → independent_success.
A prompt, an acknowledgement, a self-report and ignored advice are all
recorded but never raise a level. When a step closes well, skills the
coach prompted during it count as guided, the rest as independent.

## What is and isn't real yet

- **MockProvider is not a learned model.** It is a small deterministic
  onion model (`onion.py`) so the pipeline runs offline and predictions
  really differ by action.
- **MetaProvider is untested.** It follows the Meta Model API docs read on
  2026-10-30 (`POST https://api.meta.ai/v1/chat/completions`, JSON-schema
  `response_format`) and defaults to `muse-spark-1.3`, which the docs
  recommend for new work. `muse-wonder-1.0` is in preview. The first live
  call is plan task A05: `python3 -m livecoach.server --provider meta`.
- **The dev cases are synthetic** (`cases/dev.json`) and were used to
  build the rules, so S1 passing them is a harness check, not a result.
  Real numbers need recorded cases, a test split frozen with a hash before
  any run, the live model for all three systems, and three repeats.
- **The recipes are drafts.** A cook should confirm the targets and the
  salt timing (plan C07).
- **Not built yet:**
  - camera / VLM observations (D05, D06)
  - voice input (G03, G04). The plan is push-to-talk with batch
    transcription. Traditional Chinese output is unconfirmed, and the
    transcriber returns no confidence scores.
  - latency on real calls (H07)
  - blind evaluation (H06)
- **Privacy:** never send real camera or microphone data to a
  `-contributor` model variant; Meta may train on those requests.
