# Clip shortlist (for review before anything goes into the video)

Source footage: HD-EPIC (University of Bristol, CC BY-NC 4.0), square 1408×1408 at 30 fps.
- **P08 Scrambled Eggs:** `data/raw/hd-epic/P08-20240614-085000.mp4`, 18:08.
- **P02 Bacon & Egg Sandwich:** `data/raw/hd-epic/P02-20240210-113925.mp4`, 13:35.

Coach runs:
- **No memory:** stage 18, `results/coach_timeline_P08-…json`. A coach that sees only recent actions, called on step changes or every 60 s.
- **Memory:** stage 40, `results/coach_adaptive_remind_parallel_hdtags_<video>.json`. Checklist memory with parallel-aware reminders.

Times are video times. "Said at" is when the answer reached the screen (`ready`). What the learner is doing comes from the HD-EPIC narrations.

**Facts the script uses (checked against the narrations)**
- The learner cuts the onion 1:09–2:35, sprays the pan 4:36, cracks two eggs 5:13–5:29, whisks them 7:25–7:41, pours them in 11:47, plates 13:41 and seasons 14:12.
- **No-memory coach:** 31 answers, 14 of them ask to crack the eggs. Five of those come after the eggs were already whisked (7:41): 8:54, 9:56, 10:45, 13:28, 13:43.
- **Memory coach:** 17 answers, 5 ask to crack the eggs. One comes after 7:41 (at 7:46).

## No memory (Scrambled Eggs)

| ID | Beat | Clip in–out | What the learner does | Coach says (said at) | Short line on screen |
|---|---|---|---|---|---|
| N1 | Repeats | 1:04–1:12 | puts the onion on the board and takes the knife | "Put the onion down and start Step 1: … crack the eggs into it" (1:08) | "Crack the eggs." |
| N2 | Repeats | 3:01–3:08 | logs the onion on the phone | "Put the phone away … crack the eggs into a medium bowl" (3:05) | "Crack the eggs." |
| N3 | Repeats | 3:28–3:35 | picks up the oil spray to log it | "Put the phone down … crack the eggs into it" (3:32) | "Crack the eggs." |
| N4 | Forgets | 5:12–5:20 | **cracks the eggs** (shown first) | — | ✓ step 1 |
| N5 | Forgets | 8:52–9:00 | gets a plate; **the bowl of whisked eggs sits by the stove** (whisked 7:25–7:41) | "Stop the distraction loop and finish Step 1 first: crack the eggs" (8:54) | "Crack the eggs." ×2 |
| N6 | Can't tell done | 13:22–13:30 | **eggs cooking in the pan** | "Stop mixing and start the egg base now: crack the eggs" (13:28) | "Crack the eggs." |
| N7 | Can't tell done | 13:40–13:48 | **plates the eggs** | "Get the pan actually cooking. Spray oil … add the chopped red onions" (13:43, on screen 13:59) | "Add the onions." |

## Memory (Scrambled Eggs, then Bacon & Egg)

| ID | Beat | Clip in–out | What the learner does | Coach says (said at) | Short line on screen |
|---|---|---|---|---|---|
| M1 | Learn your way | 0:24–0:32 | takes the ingredients out of the fridge, the cottage cheese for the plate among them (step 7) | "Shifted attention to the cottage cheese plate, which is fine to do in parallel. Keep supporting that plate prep" (0:39) | "Plate first? Fine." |
| M2 | Learn your way | 1:52–2:00 | cuts the onion (step 3) | "Keep supporting the parallel work … step 7 plate prep and step 3 onion prep, without forcing" (1:45) | "Keep going." |
| M3 | Remembers | 0:11 → 5:29 | step row fills: plate 0:13, onion 1:50, pan 4:36, eggs 5:13 | (memory overlay, not advice) | row of step icons |
| M4 | (v1–v2 only) | 2:03–2:11 | still on the onion | "Step 2 (spray olive oil … medium heat) is still not seen yet and is a prerequisite for proper sautéing … confirm the skillet is oiled" (2:07) | "Oil the pan first." |
| M5 | (v1–v2 only) | 4:32–4:40 | **sprays the pan** (the reminder worked) | — | ✓ step 2 |
| E1 | Only when it's needed (v3) | 4:50.9–4:57.3 | at the phone; the eggs are not cracked yet | "Gently guide the cook back to cracking and whisking the eggs now" (4:53) | "Back to the eggs." |
| E2 | Only when it's needed (v3) | 5:09.1–5:17.3 | **opens the carton (5:12.1), takes an egg (5:13.1), cracks it (5:13.7)**: d1's top 3 at that moment are open package, break egg, take egg | — | ticks on d1's three rows; world model right from 5:14 (break egg, put shell) |
| B1 | Parallel (Bacon & Egg) | 6:45–6:51 (v3; v1–v2 used 6:12–6:23) | **cuts the baguette**: the world model's "cut bread" and d1's "cut bread (step 6)" are right | "The eggs are already cooking … In parallel start Step 4 shredding the cheddar" (6:17, still the latest answer) | "Shred cheese meanwhile." |
| B2 | Reminds before it's late | 6:58–7:06 | starts on the baguette (step 6) | "Step 5 seasoning is still not seen and Step 6 is listed as needing it, so the eggs should be seasoned before final assembly" (7:01) | "Season the eggs first." |
| B3 | Reminds before it's late | 9:20–9:25.7 (v3) | **salt into the hand (9:19.5), a pinch taken (9:24.4)**: the world model's "pour salt" and d1's "take salt (step 5)" are right | "season the eggs with salt and paprika while they are still warm" (8:55) | ticks on the right rows |

Since v3 the memory shots are picked with `video/pipeline/find_moments.py`, which scores every second of the two
memory runs against HD-EPIC's narrations: the world model is right when its top 3 holds the action narrated about a
second later, d1 when the learner then does one of its top 3 within 8 s (the narration's main action). Scrambled Eggs
has few such moments outside 5:09–5:26 (cracking the eggs); the plate and onion shots (M1, M2) stay for the story.

## Not used, on purpose
- **Memory coach 3:39–7:46.** It kept saying "step 1 not seen yet" after the eggs were cracked at 5:13; the camera missed the cracking. That is the honest limit, said once in the script, not shown as a win.
- **Bacon & Egg 12:04 and 13:36.** "steps 1–4 are already done, so do not redo them" is right, but the same answer says step 5 is still open, although the learner seasoned at 9:19–10:11.
