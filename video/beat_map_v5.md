# Beat map (draft 7 (film v5))

One home for film v5's beat map (v4 keeps video/beats.json): DEMO_VERSION=v5 python3 video/review/build_review.py OUT_DIR writes video/beat_map_v5.md. Times are estimates until the TTS files exist. 'say' is the narrator unless a line starts with 'Coach:'. 'screen' describes everything visible. Words on screen stay at 5 or fewer per screen; eyebrows, test conditions and the How it works IN/OUT labels and memory table are evidence and don't count (design_guidelines_v5.md). The comparison is the Gemini Live API on the same footage and recipe; every Gemini line is real, from results/gemini_live_*.json. The footage is prerecorded: no line implies the learner heard a coach.

## 0:00 · The hook

**What we say**: Ever thought of having a coaching chef in your house, teaching you to cook?

**What's on screen**: The learner's head-camera view as a meal begins: ingredients come out of the fridge, then the onion goes onto the chopping board. Over the footage, centred white text: "Your own coaching chef?", with "coaching chef" in italic serif. Nothing else on screen.

**Clips**: M1, M2 · **Sound**: The music starts with the cooking: Bushwick Tarantella (Kevin MacLeod, CC BY 4.0), under the narration.

## 0:06 · The catch

**What we say**: You could try Gemini Live. We gave it our learner's video and the recipe. But you'll need to constantly ask questions to get the coaching step.

**What's on screen**: Full-screen footage: the learner cuts the onion. A small white card lands top-left, grey eyebrow GEMINI LIVE API · SAME VIDEO, SAME RECIPE, line "Keep asking." It holds while the sentence is spoken.

**Clips**: G1 · **Sound**: The music dips. Pop for the card.

## 0:15 · Chapter 1 · Gemini Live

**What we say**: So we asked, every ten seconds, and it answers well. Coach: Chop the red onion. Add a spray of olive oil. Whisk the eggs.

**What's on screen**: On a pale card, a grey numbered square "1" and the title "Gemini Live" for one second. Then three hard cuts, each with a white card whose grey eyebrow gives the time, plus a small chip "asked every 10 s" for the whole beat. 1:10, the onion under the knife: "Chop the red onion." 3:30, the oil spray in hand: "Add a spray of olive oil." 5:20, an egg cracking into the bowl: "Whisk the eggs."

**Clips**: G1, G2, G3 · **Sound**: Pop on each card. The lines use Gemini's own recorded voice if the paid-tier rerun says the same words, the coach voice otherwise.

## 0:25 · Not one mention

**What we say**: But for four minutes, while the onion gets done, twenty-six answers, and not one mentions the eggs, the first step in the recipe.

**What's on screen**: The onion being chopped, full screen. Grey eyebrow GEMINI LIVE · 1:00–5:10. A big counter rolls to "26 answers" while it is spoken, then a second line lands beneath it: "Eggs: 0".

**Clips**: G4 · **Sound**: A soft tick as the counter rolls.

## 0:32 · Again and again

**What we say**: And when a step has to wait, it just says it again. Pour the eggs. Eighteen times in three minutes.

**What's on screen**: Three hard cuts: 9:00 the plate on the scale, 9:36 the onions being stirred, 10:06 oil going onto the cottage cheese. The same card stays top-left, eyebrow GEMINI LIVE · 8:30–11:40, "Pour the eggs." The counter beside it rolls from "×1" to a red "×18". It is the only red in the film.

**Clips**: G5, G6, G7 · **Sound**: A soft tick on each count.

## 0:42 · The turn

**What we say**: So we designed an entire system around the chef.

**What's on screen**: The whole frame becomes solid memory green. Centred white text: "We designed a system.", with "system" in italic serif. A slow push-in.

**Clips**: graphic only · **Sound**: The music drops out for this beat.

## 0:45 · Chapter 2 · With our system

**What we say**: Start wherever you like. Our learner gets the plate ready first, and the chef goes along: fine, do it in parallel. Then the onion: keep going.

**What's on screen**: A green numbered square "2" and the title "With our system" for one second. Then the demo page's video: the learner on the left, the page's panel on the right (world model, coach, d1). The learner turns from the sink to the cottage-cheese plate; at 0:39 the coach's answer reaches the panel and a green card lands top-left, eyebrow OUR SYSTEM · 0:39, "Plate first? Fine." The coach's reply lifts out of the panel and grows to the centre, its line "fine to do in parallel" marked in green, holds for 2 s, then drops back. Hard cut to the onion being chopped (1:54); card "Keep going.", eyebrow OUR SYSTEM · 1:45, while the panel still shows that answer. When the world model's "peel onion" turns out right, the picture freezes for a second so its tick stays 2 s.

**Clips**: M1, M2 · **Sound**: The music returns; pop on each card.

## 0:57 · It keeps track

**What we say**: It keeps track: every action it sees is written down against a recipe step, so it always knows what has started and what is left.

**What's on screen**: A row of seven round step icons appears along the bottom, all grey outlines. Four two-second shots follow (the plate, the onion, the pan, the eggs), and with each one its icon fills green and shows the moment it was first seen: 0:13, 1:50, 4:36, 5:13.

**Clips**: graphic only · **Sound**: A light tick on each fill.

## 1:06 · Only when it's needed

**What we say**: It only speaks up when something is needed. The eggs still aren't cracked, so it brings them up, without being asked. Then Liquid AI's d1 decision model lines up the next moves. Open the carton. Take an egg. Crack it. Those are the next three things our learner does.

**What's on screen**: The demo page's video, footage left, model panel right. The learner is at the phone; at 4:53 the coach's answer reaches the panel and a green card lands top-left, eyebrow OUR SYSTEM · 4:53, "Back to the eggs." The coach's reply lifts out of the panel and grows to the centre, its line "back to cracking and whisking the eggs" marked in green, holds for 2.5 s, then drops back. Under the card, the step row (2, 3 and 7 on, as the memory has them). Hard cut to 5:10: d1's top three in the panel are open package, break egg and take egg; the learner opens the carton, takes an egg and cracks it, and each of d1's rows gets a green tick as its move happens, on the words "open", "take", "crack"; the picture freezes half a second on each tick. A small LIQUID AI d1 label sits by the panel's decision-model header. The world model's rows get a tick whenever its prediction comes true (break egg, put shell). Step 1 fills as the memory marks it, at 5:16.

**Clips**: E1, E2 · **Sound**: Pop for the card, a whoosh as the reply lifts and drops, a soft tick on each green tick and on the fill.

## 1:26 · Another dish

**What we say**: On a bacon and egg sandwich, it suggests shredding the cheese while the eggs cook, and reminds you to season the eggs before you build the sandwich. Gemini Live mentions seasoning twice, then eight answers say: build the sandwich. Ours still says: season first.

**What's on screen**: The demo page's video of the Bacon & Egg run, footage left, model panel right. 6:45: the learner readies the baguette and cuts it (6:49) while the coach's 6:17 answer is on the panel; green card "Shred cheese meanwhile." (eyebrow OUR SYSTEM · 6:17) and the reply lifts to the centre, its line "shredding the cheddar cheese while the eggs and bacon continue cooking" marked. The world model's "cut bread" and d1's "cut bread (step 6)" get green ticks as the cutting happens. Hard cut to 7:01, the next answer arrives; card "Season the eggs first." Hard cut to 8:06: the learner has the baguette and butter out. A white card, grey eyebrow GEMINI LIVE · 8:00–9:10, "Build the sandwich.", with a counter rolling to "×8". Hard cut to the demo page at 8:55: green card, eyebrow OUR SYSTEM · 8:55, "Season first." The reply lifts to the centre, its line "season the eggs" marked in green. Hard cut to 9:19: salt goes into the learner's hand; the world model's "pour salt" and d1's "take salt" get their ticks.

**Clips**: B1, B2, G8, B4, B3 · **Sound**: Pops for the cards, a whoosh for the reply, soft ticks on the green ticks.

## 1:50 · Chapter 3 · How it works

**What we say**: Here's the whole system. Meta's V-JEPA 2 world model takes in the last few seconds of video, and gives back the three likeliest next actions. The memory takes in those actions, and keeps a record for every recipe step. Muse Glimmer, the coach, takes in the recipe, the memory and the recent actions, and says where you are, what's next, and which step not to forget. And Liquid AI's d1 takes in the coach's advice, the predictions and the checklist, and picks one next move, every second.

**What's on screen**: A numbered square "3" and "How it works". On pale green paper, white cards appear one at a time, joined by dashed arrows: Video, V-JEPA 2, Memory, Muse Glimmer, Liquid AI d1, Next move. The card being named lights up green. Under the row, one strip for that card, with mono labels: IN and OUT. V-JEPA 2: IN "Last few seconds of video", OUT "Top 3 next actions". Memory: IN "Actions seen, with times", OUT "A record per step". Muse Glimmer: IN "Recipe, memory, recent actions", OUT "Where you are, what's next, what not to forget". Liquid AI d1: IN "Advice, predictions, checklist", OUT "One next move, every second". The kitchen keeps playing in a small rounded square, bottom-right.

**Clips**: M2 · **Sound**: A soft tick as each card lands.

## 2:23 · What the memory records

**What we say**: Here is the memory, at four fifty-three. For each step it records: done, in progress, or not seen yet; first and last seen; which step needs it; and how many times it has reminded you. The eggs: not seen yet, and needed before step four. That's why it spoke up.

**What's on screen**: On paper, the real memory at 4:53, seven rows, one per recipe step, with columns that light up as they are named. Status (a filled, half or empty icon), First seen, Last seen, Needed before, Reminded. 1 Eggs: not seen yet, needed before 4. 2 Oil: done, 3:17, 4:33, needed before 3, reminded ×5. 3 Onions: done, 0:06, 4:28, needed before 4. 4 Pour: not seen yet, needed before 5. 5 Stir: not seen yet, needed before 6. 6 Off heat: not seen yet. 7 Plate: in progress, 0:06, 4:28. On "The eggs", row 1 fills green and the others dim.

**Clips**: graphic only · **Sound**: A tick as each column lights.

## 2:40 · The result

**What we say**: On the sandwich, ours brings up the bacon, the eggs, the cheese and the seasoning before they start. On its own, Gemini Live brings up none. It still misses what the camera can't see, and that's what we're working on next.

**What's on screen**: On paper, a small table under the eyebrow BROUGHT UP BEFORE THE LEARNER STARTED · NOBODY ASKING. Four rows: Bacon, Eggs, Cheese, Seasoning. Two columns, Our system and Gemini Live. A green tick lands in the Our system column as each step is named. Then, on "none", a grey dash lands in each row of the Gemini Live column. It holds while the limit is said.

**Clips**: graphic only · **Sound**: The music lifts slightly.

## 2:52 · The close

**What we say**: Your own coaching chef, designed as a whole system.

**What's on screen**: The finished plate being seasoned, dimmed. White text: "Your own coaching chef.", with "coaching chef" in italic serif, echoing the opening. Then a paper card with the project name and the credits: built with Meta V-JEPA 2, Muse Glimmer and Liquid AI d1; footage HD-EPIC, University of Bristol, CC BY-NC 4.0; music "Bushwick Tarantella" by Kevin MacLeod (incompetech.com), CC BY 4.0. A small line is added to the credits: "Gemini Live API (gemini-3.8-live), tested <date>. Same footage and recipe, one frame every 2 s, asked every 10 s. Not the Gemini app."

**Clips**: graphic only · **Sound**: The music resolves and ends.
