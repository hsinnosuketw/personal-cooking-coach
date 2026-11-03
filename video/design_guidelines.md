# Design guidelines

Contact sheets: one frame every 3 s of each reference video, in `video/research/frames/` (local only).

## What makes the three references work
| | postvisit.ai (A) | KICKY AI (B) | upliance (C) |
|---|---|---|---|
| **Works because** | Real places and a real person first, then the product full-screen. Every UI shot zooms to the one detail being talked about (a tooltip, one chart). Two clean section cards, each with one accent phrase. Light, airy palette (white + mint). | The story is relatable, and the architecture is explained as two layers, each named by its question. | Tight close-ups of hands, food and screen, warm natural light, a new shot for every spoken line (22 cuts/min). Brand-colour cards at the start and end, nothing else. |
| **Text** | Kinetic captions, 1–2 words at a time; a feature grid at the end (too much text for us) | Small UI text, unreadable at 480p (avoid) | One small subtitle line |
| **Cut rate** | 9.7 / min | 0.4 / min (avoid) | 21.9 / min |

## Motion references you added (Ali Abdaal, Duncan Rogoff)
| | Ali Abdaal | Duncan Rogoff |
|---|---|---|
| **Works because** | Every idea becomes a small diagram built one card at a time on a calm paper canvas: cards joined by dashed arrows, ✓/✗ status lines, two tinted panels for a comparison. The speaker stays in a corner, so the graphic never feels detached. | Type is the graphic: a bold sans line with one italic serif word in red, big numerals full-bleed, full-colour cards as transitions. Tiny mono eyebrows label each card. |
| **We take** | Cards + dashed arrows for the architecture and the memory; tinted panels for no memory vs memory; numbered chapter squares; model names as pills; a footage picture-in-picture on full-screen graphics | One italic serif accent word per card; big numerals ("×14", "5:13", "5 → 1"); eyebrow labels on the coach's card; one full-bleed colour card for the turn |
| **Tool** | HeyGen **HyperFrames**: HTML compositions rendered to MP4 (headless Chrome + ffmpeg) | — |

## Our rules (mimic A's calm palette and section cards, C's one-shot-per-line rhythm, B's layered explanation, Ali's card diagrams, Duncan's kinetic type)

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
| paper | `#F2F5F1` | section cards, the architecture background (a kitchen-tile white with a slight green tint) |
| muted | `#8A8A8E` | labels, "not seen yet" step icons |
| no-memory | `#E5484D` | the no-memory coach: bubble outline, "×14" |
| memory | `#2F9E6E` | the memory coach: bubble outline, filled step icons, "remembered" |
| night | `#111214` | background behind the split screen |

**Two accent colours only, each with one meaning.** Model names appear in ink; no brand colours except the logos on the credits card.

### 4. Type
- **Figtree** (Google Fonts), weights 500 / 600 / 700: rounded and friendly, readable at a glance; numbers use tabular figures.
- **Instrument Serif Italic** for the one accent word per card (Duncan's pattern), in that card's accent colour.
- **JetBrains Mono** 500, uppercase, letter-spaced, for tiny eyebrows ("COACH · 8:54", "STEP 2").
- Section card headline: 88 px / 700. Bubble: 44 px / 600. Labels: 32 px / 500. Big numbers: 180 px / 700. Credits: 28 px / 500.
- Sentence case; one accent word per card, set in Instrument Serif Italic and the accent colour (postvisit's colour + Duncan's italic).

### 5. Components
- **Coach card** (Duncan's label cards): a small white card (96% opacity, 18 px radius, soft shadow).
  - A mono eyebrow on top gives source and time, in the coach's colour: "NO MEMORY · 8:54" / "MEMORY · 2:07". It is evidence, and it doesn't count toward the 5 words.
  - Below it, the short line at 44 px.
- **Step row**: 7 (or 6) circular icons, 64 px, one simple outline glyph per step (egg, oil spray, onion, pour, stir, off-heat, plate).
  - Grey outline: not seen yet.
  - Filled in the memory colour: started (the memory's first sign, our definition of "done once").
- **Counter**: "×N" next to the bubble; ticks up with each repeat.
- **Chapter marker** (Ali): a 64 px rounded square with the number, above a one-line title. Three chapters: 1 "Without *memory*", 2 "With *memory*", 3 "How it *works*".
- **Turn card** (Duncan's full-bleed colour card): the memory colour full-bleed, white text "What if it *remembered*?".
- **Comparison** (Ali's tinted panels): two panels side by side, tinted no-memory / memory, used for the hook labels and the result "5 → 1".
- **Footage picture-in-picture**: on full-screen graphics (architecture, memory mapping), a 320 px rounded square of the cooking footage in the bottom-right keeps the kitchen on screen.
- **Architecture** (Ali's cards + dashed arrows): white cards built left to right on paper and joined by dashed arrows: video thumbnail → V-JEPA 2 → memory (the step row) → Muse Glimmer → d1 → "next move" chip.
  - Each card has a label chip (model name) and, while it is named, one status line: "What's next?" / "What matters?" / "One move."
  - Model names appear once as pills, with the Meta / Liquid AI logos on the credits card only.

### 6. Motion
- **In**: 220 ms, scale 0.94 → 1 + fade, ease-out `cubic-bezier(0.2, 0.8, 0.2, 1)`. **Out**: 160 ms fade.
- **Step icon fill**: 300 ms, with a single ring pulse.
- **Counter**: 120 ms number roll, with a soft tick.
- **Cuts**: a hard cut on each narration sentence inside a beat (upliance's rhythm, ~12–15 cuts/min overall). Between sections, a 10-frame dip through a card.
- No zooms on the fisheye footage (it already moves with the head); slow pushes only on cards and the architecture.

### 7. Tool
- **HyperFrames** (Apache-2.0): each graphic is one HTML composition (`data-start` / `data-duration` per element, a GSAP timeline), previewed in the browser and rendered to MP4 deterministically. The review pages and the video come from the same files. This replaces Remotion in the plan.

## 8. Sound
- **Narration**: TTS, −16 LUFS integrated, peaks below −1 dBTP.
- **Coach lines**: a second TTS voice, slightly lower, panned centre.
- **Music**: a quiet, warm bed (acoustic / lo-fi, royalty-free), −30 LUFS, ducked another 6 dB under speech. It stops for one beat at the turn ("So we built a coach that remembers.").
- **SFX**: a soft pop when a bubble appears; a light tick when a step icon fills. Nothing else.
