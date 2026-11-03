"""Build the checkpoint-A review page (script, clips, look) for the demo video: python3 video/review/build_review.py OUT_DIR

Writes OUT_DIR/index.html and copies the preview clips (video/media/preview/*) into OUT_DIR/clips/.
"""
import html
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1])
(OUT / "clips").mkdir(parents=True, exist_ok=True)
for f in (ROOT / "video/media/preview").glob("*"):
    shutil.copy2(f, OUT / "clips" / f.name)
e = html.escape

REFS = [
    ("postvisit.ai", "Built with Opus 4.6 hackathon", "https://www.youtube.com/watch?v=V29UCOii2jE", "2:59", "286×", "10,877 views vs a channel median of 38",
     "I've done thousands of procedures in this room, but I know that the real struggle happens the moment that you leave the room.",
     "A gap sentence early, echoed by the closing line. One person's story carries the demo. A \"here's the secret sauce\" turn before the tech."),
    ("KICKY AI", "Hugging Face #build-small-hackathon", "https://www.youtube.com/watch?v=knL8shghyBU", "5:29", "114×", "3,866 views vs a channel median of 34",
     "Players and teams get access to cameras, tracking stats and analysis. But I started wondering, what about players like me?",
     "Explain the architecture as layers, each named by the question it answers. Say one honest limit. Thank the sponsors. (Skip its visuals: tiny UI, almost no cuts.)"),
    ("upliance", "Smart cooking assistant demo", "https://www.youtube.com/watch?v=NJypvjsUhlI", "1:28", "631×", "175,492 views vs a channel median of 278 (likely ads)",
     "Today we will be cooking chilli garlic noodles.",
     "Tight close-ups of hands and food. A new shot for every spoken line (22 cuts a minute). A plain brand card at the start and the end."),
]

MOTION_REFS = [
    ("Ali Abdaal", "I Tried Fully Automating My Video Editing With AI", "https://www.youtube.com/watch?v=C0jOKDJtK9s", "46:33", "361k views",
     "Each idea becomes a small diagram built one card at a time on a paper canvas: white cards, dashed arrows, ✓/✗ status lines, two tinted panels for a comparison. The speaker stays in a corner.",
     "Cards and dashed arrows for the architecture and the memory, tinted panels for the result, numbered chapter squares, model names as pills, a footage picture-in-picture. Its graphics are made with HeyGen HyperFrames."),
    ("Duncan Rogoff", "I taught Claude how to edit videos and it's INSANE", "https://www.youtube.com/watch?v=REAOFI534lk", "9:05", "69k views",
     "Type is the graphic: a bold sans line with one italic serif word in red, big numerals full-bleed, tiny mono eyebrows on label cards, full-colour cards as transitions.",
     "One italic serif accent word per card, big numerals (×14, 5:13, 5 → 1), an eyebrow on each coach card, one full-bleed colour card for the turn."),
]

# (time, beat, narration, on screen, clip ids)
BEATS = [
    ("0:00", "Hook", "This cooking coach has told our cook to crack the eggs fourteen times. The eggs are already in the pan. … This one remembers.", "No memory / Memory · “Crack the eggs.” ×14 · “Keep going.”", ["N6", "M2"]),
    ("0:10", "The gap", "Real cooks don't follow a recipe line by line. We prep, we wander, we come back. A coach that forgets can't keep up.", "nothing", ["M1", "N2", "M2"]),
    ("0:21", "Repeats", "Without memory, a coach repeats itself. — Crack the eggs. Crack the eggs. Crack the eggs.", "“Crack the eggs.” ×1 ×2 ×3", ["N1", "N2", "N3"]),
    ("0:32", "Forgets", "It forgets what you did. The eggs were cracked at five minutes. At nine, it asks again.", "step 1 ✓ 5:13 → “Crack the eggs.” 8:54", ["N4", "N5"]),
    ("0:43", "Can't tell done", "And it can't tell what's finished. The eggs are on the plate, and it says: heat the pan and add the onions.", "“Add the onions.”", ["N6", "N7"]),
    ("0:54", "Turn", "So we built a coach that remembers.", "card: What if it remembered?", []),
    ("0:59", "Cook freely", "Start wherever you like. Our cook gets the plate ready first, then chops the onion, and the coach goes along: fine, do it in parallel.", "“Plate first? Fine.” · “Keep going.”", ["M1", "M2"]),
    ("1:12", "Remembers", "Every action it sees is written down against a recipe step, so it always knows what has started and what is left.", "step row fills: 0:13 · 1:50 · 4:36 · 5:13", []),
    ("1:23", "Only when needed", "It only speaks up when something is needed. The onions will need a hot pan, so it reminds you to oil the skillet. A couple of minutes later, you do.", "“Oil the pan first.” → step 2 ✓ 4:36", ["M4", "M5"]),
    ("1:36", "Another dish", "On a bacon and egg sandwich, it suggests shredding the cheese while the eggs cook, and reminds you to season the eggs before you build the sandwich.", "“Shred cheese meanwhile.” · “Season the eggs first.” · step 5 ✓", ["B1", "B2", "B3"]),
    ("1:50", "How it works", "Meta's V-JEPA 2 world model watches the video and answers: what is the cook about to do? Muse Glimmer, the coach, reads the memory and answers: what matters now? And Liquid AI's d1 turns that into one next move, every second.", "V-JEPA 2 · Muse Glimmer · d1 — What's next? / What matters? / One move.", []),
    ("2:12", "The memory", "The secret is the memory. Each action — take egg, cut onion, spray oil — is mapped back to its recipe step, with the moment it was first seen.", "action chips fly into step slots", []),
    ("2:24", "Result", "After the eggs were whisked, the coach without memory asked to crack them five more times. With memory: once. It still misses what the camera can't see, and that's what we're working on next.", "5 → 1", []),
    ("2:37", "Close", "Cook your way. Your coach remembers.", "Cook your way. · name card · credits", []),
]

# id, video, in–out, what the cook does, coach said (time), line on screen
CLIPS = {
    "No memory · Scrambled Eggs": [
        ("N1", "1:04–1:12", "Puts the onion on the board, takes the knife", "“Put the onion down and start Step 1: … crack the eggs into it” (1:08)", "Crack the eggs."),
        ("N2", "3:01–3:08", "Logs the onion on the phone", "“Put the phone away … crack the eggs into a medium bowl” (3:05)", "Crack the eggs."),
        ("N3", "3:28–3:35", "Picks up the oil spray to log it", "“Put the phone down … crack the eggs into it” (3:32)", "Crack the eggs."),
        ("N4", "5:12–5:20", "Cracks the eggs", "no call here: this shows the cracking", "✓ step 1"),
        ("N5", "8:52–9:00", "Gets a plate; the bowl of whisked eggs sits by the stove", "“Stop the distraction loop and finish Step 1 first: crack the eggs” (8:54)", "Crack the eggs."),
        ("N6", "13:22–13:30", "Eggs cooking in the pan", "“Stop mixing and start the egg base now: crack the eggs” (13:28)", "Crack the eggs."),
        ("N7", "13:40–13:48", "Plates the eggs", "“Get the pan actually cooking. Spray oil … add the chopped red onions” (13:59)", "Add the onions."),
    ],
    "Memory · Scrambled Eggs": [
        ("M1", "0:24–0:32", "Takes ingredients from the fridge, the plate's cottage cheese among them", "“Shifted attention to the cottage cheese plate, which is fine to do in parallel” (0:39)", "Plate first? Fine."),
        ("M2", "1:52–2:00", "Cuts the onion", "“Keep supporting the parallel work … without forcing step 3 forward” (1:45)", "Keep going."),
        ("M4", "2:03–2:11", "Still on the onion", "“Step 2 … is still not seen yet and is a prerequisite for proper sautéing … confirm the skillet is oiled” (2:07)", "Oil the pan first."),
        ("M5", "4:32–4:40", "Sprays the pan", "no call here: the reminder worked", "✓ step 2"),
    ],
    "Memory · Bacon & Egg Sandwich": [
        ("B1", "6:12–6:20", "Eggs cooking", "“The eggs are already cooking … In parallel start Step 4 shredding the cheddar” (6:17)", "Shred cheese meanwhile."),
        ("B2", "6:58–7:06", "Starts on the baguette", "“Step 5 seasoning is still not seen and Step 6 is listed as needing it, so the eggs should be seasoned” (7:01)", "Season the eggs first."),
        ("B3", "9:19–9:27", "Seasons the eggs", "no call here: the reminder worked", "✓ step 5"),
    ],
}


def clip_card(cid, span, cook, coach, line):
    tone = "nomem" if cid.startswith("N") else "mem"
    return f"""<article class="clip" id="clip-{cid}">
  <div class="clip-media"><video src="clips/{cid}.mp4" poster="clips/{cid}.jpg" controls muted loop playsinline preload="none"></video>
    <span class="clip-id">{cid}</span><span class="clip-time">{e(span)}</span></div>
  <div class="clip-body">
    <p class="cook">{e(cook)}</p>
    <p class="said">{e(coach)}</p>
    <p class="line {tone}">On screen: <b>{e(line)}</b></p>
  </div>
</article>"""


refs = "\n".join(f"""<article class="ref">
  <div class="ref-top"><span class="score">{e(score)}</span><span class="ref-len">{e(length)}</span></div>
  <h3><a href="{url}" target="_blank" rel="noopener">{e(name)}</a></h3>
  <p class="ref-sub">{e(sub)} · {e(views)}</p>
  <blockquote>{e(hook)}</blockquote>
  <p class="take"><span>We take</span> {e(take)}</p>
</article>""" for name, sub, url, length, score, views, hook, take in REFS)

motion_refs = "\n".join(f"""<article class="ref">
  <div class="ref-top"><span class="ref-len">{e(length)} · {e(views)}</span></div>
  <h3><a href="{url}" target="_blank" rel="noopener">{e(name)}</a></h3>
  <p class="ref-sub">{e(sub)}</p>
  <p>{e(works)}</p>
  <p class="take"><span>We take</span> {e(take)}</p>
</article>""" for name, sub, url, length, views, works, take in MOTION_REFS)

beats = "\n".join(f"""<tr><td class="t">{t}</td><td class="b">{e(b)}</td><td class="n">{e(n)}</td><td class="o">{e(o)}</td>
<td class="c">{''.join(f'<a href="#clip-{c}" class="chip {"nomem" if c.startswith("N") else "mem"}">{c}</a>' for c in cs) or '<span class="none">graphic</span>'}</td></tr>"""
                  for t, b, n, o, cs in BEATS)

clips = "\n".join(f"""<section class="clip-group"><h3>{e(group)}</h3><div class="clip-grid">{''.join(clip_card(*c) for c in items)}</div></section>"""
                  for group, items in CLIPS.items())

page = f"""<title>Coach Demo Review</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=Instrument+Serif:ital@1&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: a review sheet. Narrow reading column for the brief, a wide table for the beat map, a grid of clip cards. */
:root {{
  --bg: #f4f6f3; --surface: #ffffff; --fg: #1c1d1b; --muted: #676b66; --line: #dde2db;
  --nomem: #d93f44; --mem: #2a8f63; --nomem-soft: #fbe9e9; --mem-soft: #e3f2ea;
  /* the video's own look, fixed in both themes */
  --v-paper: #f2f5f1; --v-ink: #1c1c1e; --v-night: #111214; --v-nomem: #e5484d; --v-mem: #2f9e6e; --v-muted: #8a8a8e;
  --display: "Figtree", ui-sans-serif, system-ui, sans-serif; --body: "Figtree", ui-sans-serif, system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #121412; --surface: #1b1e1b; --fg: #e8ebe6; --muted: #9aa097; --line: #2c312b;
  --nomem: #f06a6e; --mem: #4cc28c; --nomem-soft: #3a1f20; --mem-soft: #173327; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #121412; --surface: #1b1e1b; --fg: #e8ebe6; --muted: #9aa097; --line: #2c312b;
  --nomem: #f06a6e; --mem: #4cc28c; --nomem-soft: #3a1f20; --mem-soft: #173327; color-scheme: dark }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 16px; line-height: 1.55;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 40px 80px; }}
.wrap {{ max-width: 1160px; margin: 0 auto; display: grid; gap: 56px; }}
h1, h2, h3 {{ font-family: var(--display); text-wrap: balance; margin: 0; }}
h1 {{ font-size: clamp(2rem, 5vw, 3.1rem); font-weight: 700; letter-spacing: -0.02em; line-height: 1.05; }}
h2 {{ font-size: 1.55rem; font-weight: 700; letter-spacing: -0.01em; }}
h3 {{ font-size: 1.1rem; font-weight: 600; }}
p {{ margin: 0; }}
a {{ color: inherit; }}
.eyebrow {{ font-family: var(--mono); font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
header {{ display: grid; gap: 16px; max-width: 760px; }}
.lede {{ font-size: 1.12rem; color: var(--muted); max-width: 62ch; }}
.todo {{ display: grid; gap: 8px; margin: 8px 0 0; padding: 0; list-style: none; }}
.todo li {{ display: flex; gap: 10px; align-items: baseline; }}
.todo li::before {{ content: ""; flex: none; width: 10px; height: 10px; border: 2px solid var(--mem); border-radius: 50%; transform: translateY(1px); }}
section > .head {{ display: grid; gap: 6px; margin-bottom: 20px; max-width: 760px; }}
section > .head p {{ color: var(--muted); }}
.refs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
.ref {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 20px; display: grid; gap: 10px; align-content: start; min-width: 0; }}
.ref-top {{ display: flex; justify-content: space-between; align-items: baseline; }}
.score {{ font-size: 2rem; font-weight: 700; color: var(--mem); font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }}
.ref-len, .ref-sub {{ color: var(--muted); font-size: .9rem; font-variant-numeric: tabular-nums; }}
blockquote {{ margin: 0; padding-left: 12px; border-left: 3px solid var(--line); font-style: italic; }}
.take span {{ font-weight: 600; }}
.pattern {{ margin-top: 16px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }}
.pattern div {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; font-size: .92rem; min-width: 0; }}
.pattern b {{ display: block; font-family: var(--mono); font-size: .75rem; color: var(--muted); font-weight: 500; }}
.table-scroll {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 14px; }}
table {{ border-collapse: collapse; width: 100%; min-width: 860px; font-size: .94rem; }}
th, td {{ text-align: left; vertical-align: top; padding: 12px 14px; border-bottom: 1px solid var(--line); }}
th {{ font-family: var(--mono); font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); font-weight: 500; }}
tr:last-child td {{ border-bottom: 0; }}
td.t {{ font-family: var(--mono); font-variant-numeric: tabular-nums; color: var(--muted); white-space: nowrap; }}
td.b {{ font-weight: 600; white-space: nowrap; }}
td.n {{ max-width: 46ch; }}
td.o {{ color: var(--muted); max-width: 30ch; }}
td.c {{ white-space: nowrap; }}
.chip {{ display: inline-block; font-family: var(--mono); font-size: .78rem; padding: 2px 8px; border-radius: 999px; margin: 0 4px 4px 0; text-decoration: none; }}
.chip.nomem {{ background: var(--nomem-soft); color: var(--nomem); }}
.chip.mem {{ background: var(--mem-soft); color: var(--mem); }}
.none {{ color: var(--muted); font-size: .85rem; }}
.facts {{ margin-top: 14px; color: var(--muted); font-size: .92rem; max-width: 80ch; }}
.clip-group {{ display: grid; gap: 12px; margin-bottom: 28px; }}
.clip-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }}
.clip {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; display: grid; grid-template-rows: auto 1fr; min-width: 0; }}
.clip-media {{ position: relative; aspect-ratio: 16 / 9; background: #000; }}
.clip-media video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.clip-id, .clip-time {{ position: absolute; top: 8px; font-family: var(--mono); font-size: .75rem; padding: 2px 8px; border-radius: 6px; background: rgba(0,0,0,.6); color: #fff; pointer-events: none; }}
.clip-id {{ left: 8px; font-weight: 500; }}
.clip-time {{ right: 8px; font-variant-numeric: tabular-nums; }}
.clip-body {{ padding: 14px 16px 16px; display: grid; gap: 8px; align-content: start; }}
.cook {{ font-weight: 600; }}
.said {{ color: var(--muted); font-size: .9rem; }}
.line {{ font-size: .9rem; }}
.line.nomem b {{ color: var(--nomem); }}
.line.mem b {{ color: var(--mem); }}
.looks {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }}
.frame {{ position: relative; aspect-ratio: 16 / 9; border-radius: 12px; overflow: hidden; background: var(--v-night); max-width: 100%; container-type: inline-size; }}
.frame img.full {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
.coach {{ position: absolute; left: 5%; top: 8%; display: grid; gap: .5cqw; background: rgba(255,255,255,.96); color: var(--v-ink);
  font-family: var(--display); font-weight: 600; font-size: 2.6cqw; line-height: 1.1; padding: 1.1cqw 1.8cqw 1.3cqw; border-radius: 1.3cqw; box-shadow: 0 .6cqw 2cqw rgba(0,0,0,.25); }}
.coach small {{ font-family: var(--mono); font-weight: 500; font-size: 1.05cqw; letter-spacing: .12em; color: var(--v-mem); }}
.coach.nomem small {{ color: var(--v-nomem); }}
.accent {{ font-family: "Instrument Serif", Georgia, serif; font-style: italic; font-weight: 400; }}
.turn {{ position: absolute; inset: 0; background: var(--v-mem); color: #fff; display: grid; place-items: center; font-family: var(--display); font-weight: 700; font-size: 5.6cqw; letter-spacing: -0.02em; }}
.turn .accent {{ font-size: 1.12em; letter-spacing: 0; }}
.arch {{ position: absolute; inset: 0; background: var(--v-paper); }}
.chapter {{ position: absolute; left: 6%; top: 9%; display: flex; align-items: center; gap: 1.4cqw; font-family: var(--display); font-weight: 700; font-size: 3.4cqw; color: var(--v-ink); letter-spacing: -0.01em; }}
.chapter b {{ width: 4.4cqw; height: 4.4cqw; border-radius: 1cqw; background: var(--v-mem); color: #fff; display: grid; place-items: center; font-size: 2.4cqw; }}
.chapter .accent {{ color: var(--v-mem); font-size: 1.12em; }}
.flow {{ position: absolute; left: 6%; right: 26%; top: 42%; display: flex; align-items: center; gap: 1cqw; }}
.node {{ flex: 1 1 0; min-width: 0; background: #fff; border-radius: 1.1cqw; box-shadow: 0 .4cqw 1.4cqw rgba(28,28,30,.12); padding: 1cqw; display: grid; gap: .6cqw; }}
.node em {{ font-style: normal; justify-self: start; font-family: var(--mono); font-size: .95cqw; letter-spacing: .06em; padding: .2cqw .7cqw; border-radius: 999px; background: #e7efe9; color: var(--v-mem); }}
.node.lit {{ outline: .25cqw solid var(--v-mem); }}
.node span {{ font-family: var(--display); font-weight: 600; font-size: 1.5cqw; color: var(--v-ink); }}
.node.dim {{ opacity: .45; }}
.dash {{ flex: 0 0 2.4cqw; border-top: .25cqw dashed var(--v-muted); }}
.pip {{ position: absolute; right: 4%; bottom: 7%; width: 18%; aspect-ratio: 1; border-radius: 1.4cqw; overflow: hidden; box-shadow: 0 .6cqw 2cqw rgba(0,0,0,.25); }}
.pip img {{ width: 100%; height: 100%; object-fit: cover; }}
.count {{ position: absolute; font-family: var(--display); font-weight: 700; color: var(--v-nomem); font-size: 7cqw; line-height: 1; font-variant-numeric: tabular-nums; text-shadow: 0 .3cqw 1.5cqw rgba(0,0,0,.5); }}
.steps {{ position: absolute; left: 50%; bottom: 6%; transform: translateX(-50%); display: flex; gap: 1.2cqw; }}
.steps span {{ width: 3.6cqw; height: 3.6cqw; border-radius: 50%; border: .3cqw solid rgba(255,255,255,.75); background: rgba(17,18,20,.35); color: #fff;
  font-family: var(--mono); font-size: 1.5cqw; display: grid; place-items: center; }}
.steps span.on {{ background: var(--v-mem); border-color: var(--v-mem); }}
.split {{ position: absolute; inset: 6% 3% 12%; display: grid; grid-template-columns: 1fr 1fr; gap: 2%; }}
.split figure {{ margin: 0; position: relative; border-radius: 1cqw; overflow: hidden; }}
.split img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.split figcaption {{ position: absolute; left: 0; right: 0; bottom: -9cqw; text-align: center; color: #fff; font-family: var(--display); font-weight: 600; font-size: 2.2cqw; }}
.split .coach {{ font-size: 2cqw; top: 6%; }}
.frame-cap {{ margin-top: 8px; color: var(--muted); font-size: .9rem; }}
.swatches {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }}
.sw {{ display: flex; align-items: center; gap: 8px; font-family: var(--mono); font-size: .8rem; color: var(--muted); }}
.sw i {{ width: 22px; height: 22px; border-radius: 6px; border: 1px solid var(--line); }}
.rules {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-top: 18px; }}
.rules div {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; min-width: 0; }}
.rules b {{ display: block; margin-bottom: 4px; }}
.decide {{ display: grid; gap: 12px; }}
.decide div {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; display: grid; gap: 4px; max-width: 760px; }}
.decide p {{ color: var(--muted); }}
footer {{ color: var(--muted); font-size: .85rem; max-width: 760px; }}
:focus-visible {{ outline: 2px solid var(--mem); outline-offset: 2px; }}
</style>

<div class="wrap">
<header>
  <p class="eyebrow">Meta hackathon · demo video · checkpoint A</p>
  <h1>Coach demo: script and clips</h1>
  <p class="lede">A 2:45 video that contrasts a cooking coach without memory against ours, using real HD-EPIC footage, a TTS narrator and very little text on screen. Before any graphics are built, please check:</p>
  <ul class="todo">
    <li>The clips: is each one the moment you want, and does the short line on screen say what that coach really said?</li>
    <li>The script, beat by beat: tone, claims, length.</li>
    <li>The look: the four mock frames, the colours and the 5-word limit.</li>
    <li>The four decisions at the end.</li>
  </ul>
</header>

<section>
  <div class="head"><p class="eyebrow">Step 1 · hook library</p><h2>Three demo videos that beat their channel's usual views</h2>
    <p>Outlier score = views ÷ the median views of the channel's last 30 uploads. Our script borrows one thing from each.</p></div>
  <div class="refs">{refs}</div>
  <div class="head" style="margin-top:28px"><p class="eyebrow">Your motion references</p><h3>How the graphics will look and move</h3></div>
  <div class="refs">{motion_refs}</div>
  <div class="pattern">
    <div><b>0:00</b>Contrast hook from real footage, before any title</div>
    <div><b>0:10</b>Gap sentence, echoed by the closing line</div>
    <div><b>0:54</b>“So we built…”, said once</div>
    <div><b>0:59</b>One cook's story, a new shot per line</div>
    <div><b>1:50</b>The secret sauce: three models, each named by its question</div>
    <div><b>2:24</b>One number, one honest limit, thanks</div>
  </div>
</section>

<section>
  <div class="head"><p class="eyebrow">Step 2 · script and beat map</p><h2>Fourteen beats, about 2:45</h2>
    <p>The narration explains; the screen shows at most five words. Times are estimates until the TTS files exist. Chips link to the clips below.</p></div>
  <div class="table-scroll"><table>
    <thead><tr><th>Time</th><th>Beat</th><th>Narration</th><th>On screen</th><th>Clips</th></tr></thead>
    <tbody>{beats}</tbody></table></div>
  <p class="facts">Every claim is checked against the runs and the HD-EPIC narrations. Without memory, 14 of 31 answers ask to crack the eggs; 5 of those come after the eggs were whisked at 7:41. With memory, 1 does. The eggs are cracked at 5:13, whisked by 7:41, poured at 11:47 and plated at 13:41.</p>
</section>

<section>
  <div class="head"><p class="eyebrow">Shortlist · 14 clips</p><h2>The moments that carry the contrast</h2>
    <p>Previews are cropped to the lower band of the fisheye view, as the video will be. “Coach says” is quoted from that run's answer, with the time it reached the screen.</p></div>
  {clips}
  <p class="facts">Left out on purpose: from 3:39 to 7:46 the memory coach kept saying “step 1 not seen yet”, although the eggs were cracked at 5:13. The camera missed it. The script mentions this once, as the limit.</p>
</section>

<section>
  <div class="head"><p class="eyebrow">Look</p><h2>Clean frames: footage first, one bubble, a row of steps</h2>
    <p>Mock-ups from real frames. Final frames are built in step 3; these show the treatment only.</p></div>
  <div class="looks">
    <div><div class="frame">
      <div class="split">
        <figure><img src="clips/N6.jpg" alt="Eggs cooking in the pan"><span class="coach nomem"><small>NO MEMORY · 13:28</small>Crack the eggs.</span><figcaption>No memory</figcaption></figure>
        <figure><img src="clips/M2.jpg" alt="Cook cutting a red onion"><span class="coach"><small>MEMORY · 1:45</small>Keep going.</span><figcaption>Memory</figcaption></figure>
      </div>
      <span class="count" style="left:36%;top:30%">×14</span>
    </div><p class="frame-cap">Beat 0, the hook. Same kitchen, two coaches. The eyebrow says which coach and when.</p></div>
    <div><div class="frame">
      <img class="full" src="clips/M4.jpg" alt="Cook cutting the onion">
      <span class="coach"><small>MEMORY · 2:07</small>Oil the pan first.</span>
      <div class="steps"><span>1</span><span>2</span><span class="on">3</span><span>4</span><span>5</span><span>6</span><span class="on">7</span></div>
    </div><p class="frame-cap">Beat 8. One coach card; the step row shows what the memory has seen (plate and onion so far).</p></div>
    <div><div class="frame"><div class="turn"><span>What if it <span class="accent">remembered</span>?</span></div></div>
      <p class="frame-cap">Beat 5, the turn. Duncan's full-colour card, one italic serif word.</p></div>
    <div><div class="frame"><div class="arch">
      <div class="chapter"><b>3</b><span>How it <span class="accent">works</span></span></div>
      <div class="flow">
        <div class="node dim"><em>VIDEO</em><span>Kitchen</span></div><i class="dash"></i>
        <div class="node lit"><em>V-JEPA 2</em><span>What's next?</span></div><i class="dash"></i>
        <div class="node dim"><em>MEMORY</em><span>Steps seen</span></div><i class="dash"></i>
        <div class="node dim"><em>GLIMMER</em><span>What matters?</span></div><i class="dash"></i>
        <div class="node dim"><em>D1</em><span>One move.</span></div>
      </div>
      <div class="pip"><img src="clips/M2.jpg" alt=""></div>
    </div></div><p class="frame-cap">Beat 10. Ali's cards and dashed arrows, built one card at a time while each is named; the kitchen stays in the corner.</p></div>
  </div>
  <div class="swatches">
    <span class="sw"><i style="background:var(--v-nomem)"></i>no memory #E5484D</span>
    <span class="sw"><i style="background:var(--v-mem)"></i>memory #2F9E6E</span>
    <span class="sw"><i style="background:var(--v-paper)"></i>paper #F2F5F1</span>
    <span class="sw"><i style="background:var(--v-ink)"></i>ink #1C1C1E</span>
    <span class="sw"><i style="background:var(--v-night)"></i>night #111214</span>
  </div>
  <div class="rules">
    <div><b>Five words, at most</b>No transcripts or paragraphs. A number or an icon beats a sentence.</div>
    <div><b>One meaning per colour</b>Red is the coach without memory, green the one with memory. Nothing else is coloured.</div>
    <div><b>A shot per spoken line</b>Hard cuts on sentence boundaries, about 12–15 a minute; a 10-frame dip into the section cards.</div>
    <div><b>Sound carries it</b>A narrator, a flatter second voice for the coach's own lines, a quiet music bed that drops out at the turn.</div>
  </div>
</section>

<section>
  <div class="head"><p class="eyebrow">Decide</p><h2>Four choices before step 3</h2></div>
  <div class="decide">
    <div><h3>Name on the end card</h3><p>“Personal Cooking Coach”, the repo's name, unless you have another.</p></div>
    <div><h3>Music</h3><p>A royalty-free bed you pick (for example from the YouTube Audio Library), or no music.</p></div>
    <div><h3>Narrator voice</h3><p>Kokoro, a free local TTS with several English voices (I'll send three samples), or macOS's Samantha.</p></div>
    <div><h3>Motion tool: HyperFrames instead of Remotion</h3><p>HeyGen's HyperFrames (open source, the tool behind Ali Abdaal's graphics) renders plain HTML pages to MP4. Each graphic you review as a web page is the same file that becomes video, so nothing is rebuilt between review and render. I suggest switching to it.</p></div>
  </div>
</section>

<footer>Footage: HD-EPIC (University of Bristol), CC BY-NC 4.0, shown for a non-commercial research demo. Reference videos are linked, not copied.</footer>
</div>
"""
(OUT / "index.html").write_text(page, encoding="utf-8")
print(f"wrote {OUT / 'index.html'} and {len(list((OUT / 'clips').iterdir()))} clip files")
