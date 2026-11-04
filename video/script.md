# Script: Personal Cooking Coach (draft 6, film v4)

**Audience**: cooking learners, and the hackathon judges watching for them. **Length**: 2:27 (v4), about 352 narrated words. **Voice**: a calm, warm TTS narrator. The coach's own lines ("Coach: …") use a second, flatter voice.

**Framing (draft 6)**: a typical chef, one that only watches and talks, against our whole designed system (world model, memory, coach, Liquid AI's d1 decision model, and the timing of when to speak). The "other chef" on screen is the stage-18 run: the same three models, but no memory, no checklist and no adaptive timing, so it reacts to each moment on its own. It stands in for that typical design; the film never names or measures a real product. Memory is one part of the system, shown up close in beat 11.

**Structure** (from `hook_library.md`):
1. **A question anyone can picture**: your own coaching chef, or one you design.
2. **The catch, shown**: a typical chef and the fourteen eggs.
3. **Three problems** of other chefs.
4. **"So we designed an entire system around the chef"**: one learner's story.
5. **The whole system**: three models, with the memory as one part.
6. **One number and one honest limit.**
7. **A tagline that echoes the question.**

The beat-by-beat version, with what is on screen, is `beats.json`, rendered as `beat_map.md` and on the review page.

## Narration, read straight through
**0:00 The hook.** Ever thought of having a coaching chef in your house, teaching you to cook? Or even designing your own?

**0:06 The catch.** But a typical chef, one that only watches and talks, bumps into problems. It told our learner to crack the eggs fourteen times. The eggs were already in the pan.

**0:17 Chapter 1 · Other chefs.** A typical chef repeats itself. Coach: Crack the eggs. Crack the eggs. Crack the eggs.

**0:25 It forgets.** It forgets what you did. Our learner cracked the eggs at five minutes. At nine, it asks again.

**0:32 It can't tell what's done.** And it can't tell what's finished. The eggs are on the plate, and it says: heat the pan and add the onions.

**0:39 The turn.** So we designed an entire system around the chef.

**0:42 Chapter 2 · With our system.** Start wherever you like. Our learner gets the plate ready first, and the chef goes along: fine, do it in parallel. Then the onion: keep going.

**0:54 It keeps track.** It keeps track: every action it sees is written down against a recipe step, so it always knows what has started and what is left.

**1:03 Only when it's needed.** It only speaks up when something is needed. The eggs still aren't cracked, so it steers our learner back to them. Then Liquid AI's d1 decision model lines up the next moves. Open the carton. Take an egg. Crack it. Our learner does all three.

**1:23 Another dish.** On a bacon and egg sandwich, it suggests shredding the cheese while the eggs cook, and reminds you to season the eggs before you build the sandwich.

**1:37 Chapter 3 · How it works.** Here's the whole system. Meta's V-JEPA 2 world model watches the video and answers: what is the learner about to do? Muse Glimmer, the coach, reads the memory and answers: what matters now? And Liquid AI's d1 turns that into one next move, every second.

**1:56 One part, up close.** Here is one part of it, up close. Each action, take egg, cut onion, spray oil, is mapped back to its recipe step, with the moment it was first seen.

**2:07 The result.** After the eggs were whisked, the other chef asked to crack them five more times. Ours: once. It still misses what the camera can't see, and that's what we're working on next.

**2:19 The close.** Your own coaching chef, designed as a whole system.

## Fact check (every claim, and its source)
| Claim | Source |
|---|---|
| "A typical chef … told our learner to crack the eggs fourteen times", "already in the pan" | The other chef is the stage-18 run: the same models (V-JEPA 2, Muse Glimmer, d1) with fixed triggers (a step change, or 60 s without advice) and no memory, checklist or adaptive timing. That run: 14 of 31 answers mention cracking. It says this at 13:28; the eggs were stirred in the pan 12:04–13:35 (narrations) |
| Cracked at five minutes, asked again at nine | Narrations: cracked 5:13–5:29; run answer at 8:54 |
| "Eggs on the plate … add the onions" | Plating 13:41–13:52; the answer reached the screen at 13:59 |
| "Fine, do it in parallel" | Memory run, 0:39: "fine to do in parallel" |
| (v1–v2) The oil reminder, then the learner oils the pan | Memory run, 2:07 ("step 2 … is a prerequisite for proper sautéing"); oil sprayed at 4:36. Dropped in v3: d1's top 3 never held an oil move between 2:07 and 4:36 |
| "The eggs still aren't cracked, so it steers our learner back to them" | Memory run, answer at 4:53 (asked 4:39, "off advice"): "Gently guide the cook back to cracking and whisking the eggs now"; cracked 5:13.7 (narrations) |
| "The decision model lines up the next moves: open the carton, take an egg, crack it. Our learner does all three." | d1's top 3 from 4:49 to 5:13: open package, break egg, take egg. Narrations (main action): open egg carton 5:12.1, pick up egg 5:13.1, crack egg 5:13.7 |
| Panel ticks (beats 6, 8, 9) | `video/pipeline/find_moments.py`: world model top 3 holds an action of a narration overlapping 0.5–2 s ahead; d1 move = a narration's main action within 8 s. B1 6:45–6:51 cut bread (both; the cut at 6:49.1); B3 9:20 pour salt (world model), take salt 9:24.4 (d1) |
| Cheese while the eggs cook; season before the sandwich | Bacon & Egg memory run, 6:17 and 7:01; cheese shredded 7:25, seasoned 9:19 |
| "the other chef asked to crack them five more times. Ours: once." | Requests to crack after the eggs were whisked (7:41). Other chef (stage 18): 8:54, 9:56, 10:45, 13:28, 13:43. Our system (stage 40): 7:46 |
| "Misses what the camera can't see" | The memory run said "step 1 not seen yet" from 3:39 to 7:46, although the eggs were cracked at 5:13 |
