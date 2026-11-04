# Design guidelines, film v5

`design_guidelines.md` still applies. This file lists only what changes for v5.

## 1. Text density
The five-word rule stays for what the viewer reads while watching. Two exceptions, because these screens explain rather than show: the recipe list in beat 1, the How it works IN and OUT strip, and the result table. Each IN or OUT line stays at 5 words or fewer where it can (Glimmer's OUT takes 7).

## 3. Colour
| Token | Hex | Use |
|---|---|---|
| live | `#8A8A8E` (muted) | Gemini Live: card eyebrow, its counter, chapter square. Grey, because it isn't wrong |
| no-memory | `#E5484D` | **only** the "×18" in beat 4, for the repetition. No other red in the film |
| memory | `#2F9E6E` | our system, unchanged |

## 5. Components
- **Coach card, Gemini**: same card, grey eyebrow, "GEMINI LIVE · 1:10". The line is a faithful short version of the real answer. Anything Gemini did not say, such as "Keep asking." in beat 1, is narrator text and never goes on this card.
- **Recipe list (beat 1)**: white handwriting (Caveat 700, 72 px, SIL OFL, in `assets/fonts`) over the dimmed footage, numbered 1 to 7, under a mono eyebrow. It stays 2 s after its sentence.
- **Test chip**: a small mono chip, "asked every 10 s", for all of beat 2. Our setting, so it stays visible.
- **Counters**: "26 answers" then "Eggs: 0" (beat 3), "×1" to "×18" (beat 4), "×8" (beat 9).
- **IN/OUT strip (beat 10)**: under the card row and left of the kitchen square. Mono labels IN and OUT at 24 px, text at 40 px, changing with the lit card. It replaces the question under each card.
- **Result (beat 12)**: six rows landing as each step is named, two columns (Gemini Live · not asked, Our system), a small square of the video bottom-right. Grey dashes, green ticks, and an honest dash on the step ours did not raise. No times, no counts.
- **Chapters**: 1 "Gemini *Live*", 2 "With our *system*", 3 "How it *works*".

## 8. Sound
Pop and tick as before. The red "×18" gets the same tick, nothing louder. Gemini's lines use its own recorded voice if the paid-tier rerun says the same words, otherwise the coach voice.
