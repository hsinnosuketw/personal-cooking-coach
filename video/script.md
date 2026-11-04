# Script: Personal Cooking Coach (draft 5, film v3)

**Audience**: cooking learners, and the hackathon judges watching for them. **Length**: 2:17 (v3), about 335 narrated words. **Voice**: a calm, warm TTS narrator. The coach's own lines ("Coach: …") use a second, flatter voice.

**Structure** (from `hook_library.md`):
1. **A question anyone can picture**: your own coaching chef, or one you design.
2. **The catch, shown**: our first coach and the fourteen eggs.
3. **Three problems.**
4. **"So we gave our coach a memory"**: one learner's story.
5. **The secret sauce**: three models.
6. **One number and one honest limit.**
7. **A tagline that echoes the question.**

The beat-by-beat version, with what is on screen, is `beats.json`, rendered as `beat_map.md` and on the review page.

## Narration, read straight through
**0:00 The hook.** Ever thought of having a coaching chef in your house, teaching you to cook? Or even designing your own?

**0:07 The catch.** But build one, and you bump into problems. Our first coach told our learner to crack the eggs fourteen times. The eggs were already in the pan.

**0:18 Chapter 1 · It repeats.** Without memory, a coach repeats itself. Coach: Crack the eggs. Crack the eggs. Crack the eggs.

**0:29 It forgets.** It forgets what you did. Our learner cracked the eggs at five minutes. At nine, it asks again.

**0:40 It can't tell what's done.** And it can't tell what's finished. The eggs are on the plate, and it says: heat the pan and add the onions.

**0:51 The turn.** So we gave our coach a memory.

**0:56 Chapter 2 · Learn your way.** Start wherever you like. Our learner gets the plate ready first, then chops the onion, and the coach goes along: fine, do it in parallel.

**1:09 It remembers.** Every action it sees is written down against a recipe step, so it always knows what has started and what is left.

**1:20 Only when it's needed.** It only speaks up when something is needed. The eggs still aren't cracked, so it steers our learner back to them. The decision model lines up the next moves: open the carton, take an egg, crack it. Our learner does all three.

**1:33 Another dish.** On a bacon and egg sandwich, it suggests shredding the cheese while the eggs cook, and reminds you to season the eggs before you build the sandwich.

**1:47 Chapter 3 · How it works.** Here's how. Meta's V-JEPA 2 world model watches the video and answers: what is the learner about to do? Muse Glimmer, the coach, reads the memory and answers: what matters now? And Liquid AI's d1 turns that into one next move, every second.

**2:09 The secret: memory.** The secret is the memory. Each action, take egg, cut onion, spray oil, is mapped back to its recipe step, with the moment it was first seen.

**2:21 The result.** After the eggs were whisked, the coach without memory asked to crack them five more times. With memory: once. It still misses what the camera can't see, and that's what we're working on next.

**2:34 The close.** Your own coaching chef, one that remembers what you've done.

## Fact check (every claim, and its source)
| Claim | Source |
|---|---|
| "crack the eggs fourteen times", "already in the pan" | No-memory run: 14 of 31 answers mention cracking. It says this at 13:28; the eggs were stirred in the pan 12:04–13:35 (narrations) |
| Cracked at five minutes, asked again at nine | Narrations: cracked 5:13–5:29; run answer at 8:54 |
| "Eggs on the plate … add the onions" | Plating 13:41–13:52; the answer reached the screen at 13:59 |
| "Fine, do it in parallel" | Memory run, 0:39: "fine to do in parallel" |
| (v1–v2) The oil reminder, then the learner oils the pan | Memory run, 2:07 ("step 2 … is a prerequisite for proper sautéing"); oil sprayed at 4:36. Dropped in v3: d1's top 3 never held an oil move between 2:07 and 4:36 |
| "The eggs still aren't cracked, so it steers our learner back to them" | Memory run, answer at 4:53 (asked 4:39, "off advice"): "Gently guide the cook back to cracking and whisking the eggs now"; cracked 5:13.7 (narrations) |
| "The decision model lines up the next moves: open the carton, take an egg, crack it. Our learner does all three." | d1's top 3 from 4:49 to 5:13: open package, break egg, take egg. Narrations (main action): open egg carton 5:12.1, pick up egg 5:13.1, crack egg 5:13.7 |
| Panel ticks (beats 6, 8, 9) | `video/pipeline/find_moments.py`: world model top 3 holds an action of a narration overlapping 0.5–2 s ahead; d1 move = a narration's main action within 8 s. B1 6:45–6:51 cut bread (both; the cut at 6:49.1); B3 9:20 pour salt (world model), take salt 9:24.4 (d1) |
| Cheese while the eggs cook; season before the sandwich | Bacon & Egg memory run, 6:17 and 7:01; cheese shredded 7:25, seasoned 9:19 |
| 5 → 1 | Requests to crack after the eggs were whisked (7:41). No memory: 8:54, 9:56, 10:45, 13:28, 13:43. Memory: 7:46 |
| "Misses what the camera can't see" | The memory run said "step 1 not seen yet" from 3:39 to 7:46, although the eggs were cracked at 5:13 |
