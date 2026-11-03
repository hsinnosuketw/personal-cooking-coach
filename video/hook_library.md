# Hook library

Three short demo videos in our niche (an AI coach that watches you, built for a hackathon or a cooking assistant) that beat their channel's usual views by a wide margin. Outlier score = the video's views ÷ the median views of the channel's last 30 uploads (yt-dlp, 2026-11-03). Downloads and frames are in `video/research/` (local only, not published).

| # | Video | Length | Views | Channel median | Outlier |
|---|---|---|---|---|---|
| A | [postvisit.ai: built with Opus 4.6 hackathon](https://www.youtube.com/watch?v=V29UCOii2jE), Michał Nedoszytko | 2:59 | 10,877 | 38 | **286×** |
| B | [KICKY AI demo, #build-small-hackathon (Hugging Face)](https://www.youtube.com/watch?v=knL8shghyBU), dcrey7 | 5:29 | 3,866 | 34 | **114×** |
| C | [Cook with India's first smart cooking assistant](https://www.youtube.com/watch?v=NJypvjsUhlI), upliance ai | 1:28 | 175,492 | 278 | **631×** (likely helped by ads) |

Runners-up checked:
- Easely, Meta Hackathon 2021: 15.7×, but a live, unedited demo with a weak opening.
- Nosh robo-chef: 159×, a 59 s product ad.
- Descript product-demo ad: 194×.

## A. postvisit.ai: credibility, gap, "so I built", one person's story, secret sauce, tagline
**Hook (0:00–0:42)**
> "Hi, my name is Michał. I'm a cardiologist… I've done thousands of procedures in this room, but I know that **the real struggle happens the moment that you leave the room.**"
- The opening says who he is, then names the gap the product fills. The gap line comes back as the closing line.

**Structure**
- 0:00 who I am (on location)
- 0:33 the gap
- 0:42 "so one day I heard about this hackathon…" (a short travel montage)
- 1:03 "And here it is": logo
- 1:09 a named user's story ("Alex is 40…") walks through the product
- 1:51 a turn: "Okay, but what if we have no file at hand? Well, **here's the secret sauce**"
- 2:43 a feature grid
- 2:55 a tagline that echoes the gap: "made to bridge the gap that begins the moment you leave the office"

**Pacing**: 9.7 cuts/min. Voice-over all the way, under a music bed.

**Text on screen**
- One or two words of kinetic caption at a time.
- Two section cards, each one question or claim with one accent-coloured phrase ("But how to do it if you have **no EHR connection**?").

**What we take**
- The gap sentence, stated early and echoed at the end.
- One person's story to carry the demo.
- A "here's the secret sauce" turn before the tech.

## B. KICKY AI: relatable contrast, "so I built", questions it answers, two layers, honest limits
**Hook (0:00–0:45)**
> "At the highest level, players and teams get access to cameras, tracking stats and analysis… **But I started wondering, what about players like me?** … I don't have a professional coach analyzing my every shot."
- It contrasts what experts have with what "I" have, then: "**So I built Kicky AI, a football shooting coach that turns normal phone clips into feedback that you can actually use.**"

**Structure**
- 0:00 contrast
- 0:45 "So I built…" plus the four questions it answers ("was it a goal? how fast? was my form good? what should I improve next?")
- 1:05 the architecture as **two layers, each named by the question it answers** ("what happened in the clip?" / "how can I improve?")
- 2:11 a live run
- 4:40 honest limits ("not fully real-time yet")
- 5:02 the tagline restates the contrast, then thanks the sponsors (Hugging Face, Modal, NVIDIA…)

**Pacing**: 0.4 cuts/min (a webcam, then one screen recording).

**What we take**
- The story and the layer explanation: name each model by the question it answers.
- The honest limit, and the thank-you to the sponsors.

**What we avoid**: its visuals. Tiny UI, minutes without a cut.

## C. upliance: title card, one step per shot, close-ups, end card
**Hook (0:00–0:06)**
- A close-up of the device's screen showing the dish.
- A brand-colour title card: "How to cook with the delishUp".

**Structure**
- One continuous recipe, one instruction per shot, in order: choose the recipe → ingredients → weigh → step-by-step → add vegetables → sauces → noodles → "sit back and relax" → plate.
- A logo end card.

**Pacing**: 21.9 cuts/min. Every line of voice-over gets its own shot.

**Text on screen**: a single small subtitle line at the bottom.

**What we take**
- Cooking shown as tight close-ups of hands and food.
- A new shot for each spoken line.
- A plain brand-colour card at the start and at the end.

## The pattern our script follows
1. **Contrast hook in ≤10 s, from real footage (A + B).** Show the failure in action, then the fix, before any title.
2. **Gap sentence (A).** "Real cooks don't follow a recipe line by line…", echoed by the closing tagline.
3. **"So we built…" (A + B)**, said once, plainly.
4. **One cook's story carries the demo (A),** with a new shot per line (C).
5. **"Here's the secret: memory" turn (A),** then the three models, each named by the question it answers (B).
6. **One honest limit, one measured number, then thanks to the sponsors (B).**
