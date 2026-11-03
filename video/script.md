# Script: Personal Cooking Coach (draft 1)

**Length and voice**: about 2:50 of English narration (≈380 words at 150 wpm, plus pauses). The narrator is a calm, warm TTS voice. The coach's own lines ("Crack the eggs.") use a second, flatter TTS voice, so they sound like the device speaking.

**Structure** (from `hook_library.md`): contrast hook → gap sentence → three problems → "so we built" → one cook's story → secret sauce + three models → honest limit + one number → tagline that echoes the gap. Clip IDs refer to `clips.md`.

| # | Beat | Narration | Picture | ≈ s |
|---|---|---|---|---|
| 0 | Hook: contrast | "This cooking coach has told our cook to crack the eggs **fourteen times**. The eggs are already in the pan." … "This one remembers." | Split screen: N6 (eggs in the pan, ×14) left, M2 (onion, "Keep going.") right | 10 |
| 1 | Gap | "Real cooks don't follow a recipe line by line. We prep, we wander, we come back. A coach that forgets can't keep up." | One shot per sentence: M1 fridge, N2 phone, M2 onion | 11 |
| 2 | Problem: repeats | "Without memory, a coach repeats itself." *Coach voice:* "Crack the eggs." ×3 | N1 → N2 → N3, bubble and counter 1, 2, 3 | 11 |
| 3 | Problem: forgets | "It forgets what you did. The eggs were cracked at five minutes. At nine, it asks again." | N4 (cracking, ✓ step 1) → N5 (whisked eggs by the stove, "Crack the eggs.") | 11 |
| 4 | Problem: can't tell done | "And it can't tell what's finished. The eggs are on the plate, and it says: heat the pan and add the onions." | N6 → N7 (plating, "Add the onions.") | 11 |
| 5 | Turn | "So we built a coach that remembers." | Card: *What if it **remembered**?* | 5 |
| 6 | Cook freely | "Start wherever you like. Our cook gets the plate ready first, then chops the onion, and the coach goes along: fine, do it in parallel." | M1 ("Plate first? Fine.") → M2 ("Keep going.") | 13 |
| 7 | Remembers | "Every action it sees is written down against a recipe step, so it always knows what has started and what is left." | The step row fills over a fast montage: plate 0:13, onion 1:50, pan 4:36, eggs 5:13 | 11 |
| 8 | Reminds only when needed | "It only speaks up when something is needed. The onions will need a hot pan, so it reminds you to oil the skillet. A couple of minutes later, you do." | M4 ("Oil the pan first.") → M5 (spraying, ✓ step 2) | 13 |
| 9 | Another dish | "On a bacon and egg sandwich, it suggests shredding the cheese while the eggs cook, and reminds you to season the eggs before you build the sandwich." | B1 ("Shred cheese meanwhile.") → B2 ("Season the eggs first.") → B3 (seasoning, ✓) | 14 |
| 10 | How it works | "Here's how. Meta's V-JEPA 2 world model watches the video and answers: what is the cook about to do? Muse Glimmer, the coach, reads the memory and answers: what matters now? And Liquid AI's d1 turns that into one next move, every second." | Three nodes light up in turn over a dimmed clip: video → V-JEPA 2 → memory → Muse Glimmer → d1 → next move | 22 |
| 11 | Secret sauce: memory | "The secret is the memory. Each action — take egg, cut onion, spray oil — is mapped back to its recipe step, with the moment it was first seen." | Action tokens fly from a timeline into recipe-step slots | 12 |
| 12 | Number + honest limit | "After the eggs were whisked, the coach without memory asked to crack them five more times. With memory: once. It still misses what the camera can't see, and that's what we're working on next." | Big number: **5 → 1** | 13 |
| 13 | Tagline + credits | "Cook your way. Your coach remembers." | Card: tagline, then credits: Built with Meta V-JEPA 2 · Muse Glimmer · Liquid AI d1. Footage: HD-EPIC, University of Bristol (CC BY-NC 4.0) | 8 |

**Total ≈ 2:45.** Each beat's real length comes from the TTS file. If the total runs over 3:00, beat 9 is the first to trim.

## Fact check (every claim → its source)
| Claim | Source |
|---|---|
| "Crack the eggs" fourteen times | No-memory run: 14 of 31 answers mention cracking |
| "The eggs are already in the pan" | It says this at 13:28; the eggs were stirred in the pan 12:04–13:35 (narrations) |
| Cracked at 5:13, asked again at 8:54 | Narrations; run answer at 8:54 |
| "Eggs on the plate … add the onions" | Plating 13:41–13:52; the answer reached the screen at 13:59 |
| "Fine, do it in parallel" | Memory run, 0:39: "fine to do in parallel" |
| Oil reminder, then the cook oils the pan | Memory run, 2:07 ("step 2 … is a prerequisite for proper sautéing"); the cook sprays at 4:36 |
| Cheese while the eggs cook; season before the sandwich | Bacon & Egg memory run, 6:17 and 7:01; cheese shredded 7:25, seasoned 9:19 |
| 5 → 1 | Requests to crack after the eggs were whisked (7:41): no memory 8:54, 9:56, 10:45, 13:28, 13:43; memory 7:46 |
| "Misses what the camera can't see" | The memory run said "step 1 not seen yet" from 3:39 to 7:46, although the eggs were cracked at 5:13 |
