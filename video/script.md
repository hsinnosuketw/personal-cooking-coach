# Script: Personal Cooking Coach (draft 7, for film v5)

**Audience**: cooking learners, and the hackathon judges watching for them. **Length**: about 2:45. **Voice**: a calm, warm TTS narrator. The coach's own lines ("Coach: …") use a second, flatter voice.

**Framing (draft 7)**: Gemini Live, a service people can use today, against our whole designed system. The point is a coach that brings up what you are **not** doing, without being asked. The film tests the Gemini Live API (`gemini-3.8-live`), not the Gemini app, on the same footage and recipe, and says so on screen. It does not claim to be more accurate than Gemini: asked often enough, Gemini answers well, and the film shows that.

The footage is prerecorded, so our learner never hears either coach. No line may imply that the learner acted on advice.

**Structure**:
1. **A question anyone can picture**: your own coaching chef.
2. **The one-line catch**: with Gemini Live you have to keep asking.
3. **Fair to Gemini**: asked every ten seconds, it answers well, but follows what is in front of it and repeats itself.
4. **"So we designed an entire system around the chef"**: one learner's story.
5. **The whole system**: what each model takes in and gives back, and what the memory records.
6. **One video, its six steps, and which ones each side reminds you of ahead of time.**
7. **A tagline that echoes the question.**

The beat-by-beat version, with what is on screen, is `beats.json`, rendered as `beat_map.md` and on the review page.

## Narration, read straight through
**0:00 The hook.** Ever thought of having a coaching chef in your house, teaching you to cook?

**0:06 The catch.** You could try Gemini Live. We gave it our learner's video and the recipe. But you'll need to constantly ask questions to get the coaching step.

**0:15 Chapter 1 · Gemini Live.** So we asked, every ten seconds, and it answers well. Coach: Chop the red onion. Add a spray of olive oil. Whisk the eggs.

**0:25 Not one mention.** But for four minutes, while the onion gets done, twenty-six answers, and not one mentions the eggs, the first step in the recipe.

**0:32 Again and again.** And when a step has to wait, it just says it again. Pour the eggs. Eighteen times in three minutes.

**0:42 The turn.** So we designed an entire system around the chef.

**0:45 Chapter 2 · With our system.** Start wherever you like. Our learner gets the plate ready first, and the chef goes along: fine, do it in parallel. Then the onion: keep going.

**0:57 It keeps track.** It keeps track: every action it sees is written down against a recipe step, so it always knows what has started and what is left.

**1:06 Only when it's needed.** It only speaks up when something is needed. The eggs still aren't cracked, so it brings them up, without being asked. Then Liquid AI's d1 decision model lines up the next moves. Open the carton. Take an egg. Crack it. Those are the next three things our learner does.

**1:26 Another dish.** On a bacon and egg sandwich, it suggests shredding the cheese while the eggs cook, and reminds you to season the eggs before you build the sandwich. Gemini Live mentions seasoning twice, then eight answers say: build the sandwich. Ours still says: season first.

**1:50 Chapter 3 · How it works.** Here's the whole system. Meta's V-JEPA 2 world model takes in the last few seconds of video, and gives back the three likeliest next actions. The memory takes in those actions, and records each step's status, when it was seen, and what needs it. Muse Glimmer, the coach, takes in the recipe, the memory and the recent actions, and says where you are, what's next, and which step not to forget. And Liquid AI's d1 takes in the coach's advice, the predictions and the checklist, and picks one next move, every second.

**2:21 One video, six steps.** We used one video, a bacon and egg sandwich. It has six steps: cook the bacon, mix the eggs, cook them, shred the cheese, season, and build the sandwich. Not asked, Gemini Live reminds you of none of them ahead of time. Ours reminds you of all but the last.

**2:35 The close.** Your own coaching chef, designed as a whole system.

## Fact check (every claim, and its source)
Gemini runs are `results/gemini_live_<video>_<label>.json`, on the free tier for now. Rerun on the paid tier before the film is published. Counts come from `coach.evaluation.compare_live.mentions` (notebook stage 41). The egg recording is `P08-20240614-085000`, the sandwich `P02-20240210-113925`.

| Claim | Source |
|---|---|
| "You'll need to constantly ask questions" | No reply during the film with only the video and the recipe: eggs `A_1`, `A_2`, `B_2`, sandwich `A_2`. It answered every question in the runs that asked. We infer that it needs a turn; the docs don't say so directly. API only |
| "We asked, every ten seconds" | Eggs `D10_2`: 108 questions, 108 answers. Our own setting, stated on screen |
| "It answers well": chop the red onion, add a spray of olive oil, whisk the eggs | Eggs `D10_2`: 1:10, 3:30, 5:20. Narrations: the onion is cut 1:09–2:35, the oil spray picked up 3:29, sprayed 4:36; the eggs cracked 5:13–5:29, whisked 7:25–7:41 |
| "Four minutes … twenty-six answers, and not one mentions the eggs, the first step in the recipe" | Eggs `D10_2`: 26 answers from 1:00 to 5:10, none matching "egg"; the next mention is 5:20, after cracking began at 5:13. Before 1:00 it does mention them (0:20–0:50). Cracking the eggs is step 1 of `P08_R03`. The learner chose this order and was not forgetting the eggs |
| "Pour the eggs. Eighteen times in three minutes" | Eggs `D10_2`: 18 of 20 answers from 8:30 to 11:40. Pouring was a fair next step, and it happened at 11:47: repetition, not wrong advice |
| The shots under it: onions being stirred, cottage cheese on the plate | Step annotations: onions 8:33–9:46, cottage cheese 8:53–9:13 and 10:04–10:19 |
| "Fine, do it in parallel" | Our run, 0:39: "fine to do in parallel" |
| "The eggs still aren't cracked, so it brings them up, without being asked" | Our run, answer at 4:53 (asked 4:39, "off advice"): "Gently guide the cook back to cracking and whisking the eggs now"; cracked 5:13.7 (narrations). Also 3:55 |
| "The decision model lines up the next moves: open the carton, take an egg, crack it. Those are the next three things our learner does." | d1's top 3 from 4:49 to 5:13: open package, break egg, take egg. Narrations (main action): open egg carton 5:12.1, pick up egg 5:13.1, crack egg 5:13.7 |
| Panel ticks (beats 6, 8, 9) | `video/pipeline/find_moments.py`: world model top 3 holds an action of a narration overlapping 0.5–2 s ahead; d1 move = a narration's main action within 8 s. B1 6:45–6:51 cut bread (both; the cut at 6:49.1); B3 9:20 pour salt (world model), take salt 9:24.4 (d1) |
| Cheese while the eggs cook; season before the sandwich | Our sandwich run, 6:17 and 7:01; cheese shredded 7:25, seasoned 9:19 |
| "Gemini Live mentions seasoning twice, then eight answers say: build the sandwich" | Sandwich `D10_2`: seasoning at 7:40 and 7:50; 8 of 8 answers from 8:00 to 9:10 name the baguette or sandwich, none names seasoning; seasoned 9:19. It raises paprika again at 10:00 |
| "Ours still says: season first" | Our sandwich run, 8:55: "Pause the buttering / bread handling briefly and season the eggs" |
| V-JEPA 2: "last few seconds of video", "the three likeliest next actions" | `coach.perception.clips`: 32 frames at 8 fps, predicting about 1 s ahead. The run keeps the top 3 per second (`ticks[].wm`). README says 3.2 s and 0.8 s; the film says "last few seconds" |
| Memory: "takes in those actions", "a record for every recipe step" | `coach.coaching.reminders.memory_lines_parallel`, `coach.memory.checklist`. The coach's own status answers feed it too, which the film leaves out |
| Muse Glimmer: takes in "the recipe, the memory and the recent actions"; says "where you are, what's next, and which step not to forget" | `coach.coaching.prompts.event_prompt`, `adaptive_prompt`; `REMIND_PARALLEL_ANSWER`: Where, Next, REMIND. Its prompt also holds why it is asked now, and d1's current pick |
| d1: takes in "the coach's advice, the predictions and the checklist"; "one next move, every second" | `coach.decision.d1`: `d1_state`, `with_checklist`, `d1_questions`. One answer per tick (877 of 877, 812 of 812), ranked top 3 kept. It also gets the tracker's step |
| The memory's fields: status, first and last seen, which step needs it, times reminded | `memory_lines_parallel`: state, first sign, last, needed before step, reminded Nx |
| "It has six steps" | `P02_R04`: heat oil and cook the bacon; crack, mix and beat the eggs; cook them; shred the cheese; season; build the sandwich |
| "Ours reminds you of all but the last" | Our sandwich run (`STEP` and `REMIND` lines), then the annotations. Bacon 0:19, started 1:07. Mix the eggs 2:48, started 3:01. Cook them 3:09, started 4:56. Cheese 5:47, started 7:25. Seasoning 7:20, started 9:19. Build the sandwich: started 6:42, not reminded ahead. `goals.reminder_scores`: 5/6. The egg dish is only 1/5, which is why the film names this one video |
| "Not asked, Gemini Live reminds you of none of them ahead of time" | Sandwich `A_2`, video and recipe only: no reply during the film. **Asked every 10 s it does raise them** (`D10_2`: cheese 6:22, seasoning 7:40), bacon 0:10, eggs 2:12 too, so "not asked" in the line and the column header must stay. Only this API was tested, so the film does not say "other agents" |

## What the film does not claim, and why
- **That we are more accurate.** Hand labels in `video/gemini_labels.tsv` (30 s runs): wrong or redo 4 of 30 and 0 of 28 for Gemini, 7 of 17 for ours. From 9:33 our coach wrongly decides the eggs are in the pan.
- **That it forgets what you did.** Its status answers at the end of the eggs runs were right. It did wrongly say the cheese was still to do at the end of sandwich `A_2`, but that is one answer.
- **That it misses skipped steps.** With the frames withheld, it noticed the cheese after 47 s and the seasoning after 51 s (ours: 13 s and 38 s), though not the oil. Ours took 301 s for the onion and never reminded about the plating, and has no oil result.
- **Anything about the Gemini app, or that ten seconds is the only way to ask.**
- **The limit line.** v4's and earlier v5's "It still misses what the camera can't see" is gone at the user's request (2026-11-04): the result now only covers the video, its steps and the comparison.
