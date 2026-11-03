# Script: Personal Cooking Coach (draft 2)

**Audience**: cooking learners, and the hackathon judges watching for them. **Length**: about 2:50, 342 narrated words. **Voice**: a calm, warm TTS narrator. The coach's own lines ("Coach: …") use a second, flatter voice.

**Structure** (from `hook_library.md`):
1. **The learner's juggle**: everyone's problem, said first.
2. **A good teacher keeps track**: the gap.
3. **The vivid failure**: fourteen eggs.
4. **The promise.**
5. **Three problems.**
6. **"So we built"**: one learner's story.
7. **The secret sauce**: three models.
8. **One number and one honest limit.**
9. **A tagline that echoes the opening.**

The beat-by-beat version, with what is on screen, is `beats.json`, rendered as `beat_map.md` and on the review page.

## Narration, read straight through
**0:00 The background.** Anyone learning to cook knows the juggle: chop one thing, check the recipe, start another, then come back.

**0:08 The problem.** A good cooking teacher keeps track of all that for you. An AI coach without memory can't. This one told our learner to crack the eggs fourteen times. The eggs were already in the pan.

**0:20 The promise.** Ours remembers what you've done, so you can learn your way.

**0:26 Chapter 1 · It repeats.** Without memory, a coach repeats itself. Coach: Crack the eggs. Crack the eggs. Crack the eggs.

**0:37 It forgets.** It forgets what you did. Our learner cracked the eggs at five minutes. At nine, it asks again.

**0:48 It can't tell what's done.** And it can't tell what's finished. The eggs are on the plate, and it says: heat the pan and add the onions.

**0:59 The turn.** So we built a coach that remembers.

**1:04 Chapter 2 · Learn your way.** Start wherever you like. Our learner gets the plate ready first, then chops the onion, and the coach goes along: fine, do it in parallel.

**1:17 It remembers.** Every action it sees is written down against a recipe step, so it always knows what has started and what is left.

**1:28 Only when it's needed.** It only speaks up when something is needed. The onions will need a hot pan, so it reminds you to oil the skillet. A couple of minutes later, you do.

**1:41 Another dish.** On a bacon and egg sandwich, it suggests shredding the cheese while the eggs cook, and reminds you to season the eggs before you build the sandwich.

**1:55 Chapter 3 · How it works.** Here's how. Meta's V-JEPA 2 world model watches the video and answers: what is the learner about to do? Muse Glimmer, the coach, reads the memory and answers: what matters now? And Liquid AI's d1 turns that into one next move, every second.

**2:17 The secret: memory.** The secret is the memory. Each action, take egg, cut onion, spray oil, is mapped back to its recipe step, with the moment it was first seen.

**2:29 The result.** After the eggs were whisked, the coach without memory asked to crack them five more times. With memory: once. It still misses what the camera can't see, and that's what we're working on next.

**2:42 The close.** Learn to cook your way. Your coach remembers.

## Fact check (every claim, and its source)
| Claim | Source |
|---|---|
| "crack the eggs fourteen times", "already in the pan" | No-memory run: 14 of 31 answers mention cracking. It says this at 13:28; the eggs were stirred in the pan 12:04–13:35 (narrations) |
| Cracked at five minutes, asked again at nine | Narrations: cracked 5:13–5:29; run answer at 8:54 |
| "Eggs on the plate … add the onions" | Plating 13:41–13:52; the answer reached the screen at 13:59 |
| "Fine, do it in parallel" | Memory run, 0:39: "fine to do in parallel" |
| The oil reminder, then the learner oils the pan | Memory run, 2:07 ("step 2 … is a prerequisite for proper sautéing"); oil sprayed at 4:36 |
| Cheese while the eggs cook; season before the sandwich | Bacon & Egg memory run, 6:17 and 7:01; cheese shredded 7:25, seasoned 9:19 |
| 5 → 1 | Requests to crack after the eggs were whisked (7:41). No memory: 8:54, 9:56, 10:45, 13:28, 13:43. Memory: 7:46 |
| "Misses what the camera can't see" | The memory run said "step 1 not seen yet" from 3:39 to 7:46, although the eggs were cracked at 5:13 |
