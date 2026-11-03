# Design guidelines

Contact sheets: one frame every 3 s of each reference video, in `video/research/frames/` (local only).

## What makes the three references work
| | postvisit.ai (A) | KICKY AI (B) | upliance (C) |
|---|---|---|---|
| **Works because** | Real places and a real person first, then the product full-screen. Every UI shot zooms to the one detail being talked about (a tooltip, one chart). Two clean section cards, each with one accent phrase. Light, airy palette (white + mint). | The story is relatable, and the architecture is explained as two layers, each named by its question. | Tight close-ups of hands, food and screen, warm natural light, a new shot for every spoken line (22 cuts/min). Brand-colour cards at the start and end, nothing else. |
| **Text** | Kinetic captions, 1–2 words at a time; a feature grid at the end (too much text for us) | Small UI text, unreadable at 480p (avoid) | One small subtitle line |
| **Cut rate** | 9.7 / min | 0.4 / min (avoid) | 21.9 / min |

## Our rules (mimic A's calm palette and section cards, C's one-shot-per-line rhythm, B's layered explanation)

### 1. Text density: clean view
- **≤ 5 words on screen at a time** (credits excepted). No paragraphs, no advice transcripts.
- The coach's advice appears as **one short bubble**: a faithful short version of what that run actually said (`clips.md`, "Short line on screen"). The narration carries the explanation.
- Prefer **icons, numbers and states** to words. Steps are icons, the repeat count is "×14", the result is "5 → 1".
- No burned-in captions; an `.srt` is delivered for YouTube.

### 2. Frame and footage (1920×1080, 30 fps)
- **Single clip**: crop the square fisheye footage to its lower band (x 0–1408, y 520–1312, exactly 16:9) and scale it to 1920×1080, full-bleed. The hands and counter sit in this band.
- **Contrast (hook)**: two square crops (1000×1000 from x 204, y 408), each 880×880, side by side with a 40 px gap on a dark background. Under each, a label: "No memory" / "Memory".
- Safe area: 96 px from every edge. Bubbles go top-left; the step row goes bottom-centre.
- Footage stays at natural colour; a slight darken (−15%) only while a card or the architecture graphic sits on top.

### 3. Colour
| Token | Hex | Use |
|---|---|---|
| ink | `#1C1C1E` | text on light cards |
| paper | `#F6F4EF` | section cards, the architecture background |
| muted | `#8A8A8E` | labels, "not seen yet" step icons |
| no-memory | `#E5484D` | the no-memory coach: bubble outline, "×14" |
| memory | `#2F9E6E` | the memory coach: bubble outline, filled step icons, "remembered" |
| night | `#111214` | background behind the split screen |

**Two accent colours only, each with one meaning.** Model names appear in ink; no brand colours except the logos on the credits card.

### 4. Type
- **Inter** (Google Fonts), weights 500 / 600 / 700.
- Section card headline: 88 px / 700. Bubble: 44 px / 600. Labels: 32 px / 500. Big numbers: 180 px / 700. Credits: 28 px / 500.
- Sentence case; one accent word per card in the accent colour (postvisit's pattern).

### 5. Components
- **Coach bubble**: a white pill (96% opacity, 24 px radius, soft shadow) with a 6 px left border in the coach's colour and the small chef icon (`site/icons/chef.png`).
- **Step row**: 7 (or 6) circular icons, 64 px, one simple outline glyph per step (egg, oil spray, onion, pour, stir, off-heat, plate).
  - Grey outline: not seen yet.
  - Filled in the memory colour: started (the memory's first sign, our definition of "done once").
- **Counter**: "×N" next to the bubble; ticks up with each repeat.
- **Section card**: paper background, one centred line, one accent word.
- **Architecture**: three rounded nodes in a row (V-JEPA 2 · Muse Glimmer · d1) between a video thumbnail and a "next move" chip. Each node lights up while it is named, with its question (≤5 words) under it: "What's next?" / "What matters?" / "One move."

### 6. Motion
- **In**: 220 ms, scale 0.94 → 1 + fade, ease-out `cubic-bezier(0.2, 0.8, 0.2, 1)`. **Out**: 160 ms fade.
- **Step icon fill**: 300 ms, with a single ring pulse.
- **Counter**: 120 ms number roll, with a soft tick.
- **Cuts**: a hard cut on each narration sentence inside a beat (upliance's rhythm, ~12–15 cuts/min overall). Between sections, a 10-frame dip through a card.
- No zooms on the fisheye footage (it already moves with the head); slow pushes only on cards and the architecture.

### 7. Sound
- **Narration**: TTS, −16 LUFS integrated, peaks below −1 dBTP.
- **Coach lines**: a second TTS voice, slightly lower, panned centre.
- **Music**: a quiet, warm bed (acoustic / lo-fi, royalty-free), −30 LUFS, ducked another 6 dB under speech. It stops for one beat at the turn ("So we built a coach that remembers.").
- **SFX**: a soft pop when a bubble appears; a light tick when a step icon fills. Nothing else.
