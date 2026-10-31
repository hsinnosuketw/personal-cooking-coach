# Critique 1 — 3D kitchen duel (player + QA, first play)

Page: game.html served by serve.py on 8011 (so /api/coach works). Played headless in
Chromium: auto-run, pause, Step+1, scrub to 1/3/9/21/40, X-ray on/off, seed 7→12,
speed 1x→2x, drag-orbit, wheel zoom, keys, phone taps, loop wrap 40→1.
My shots live in /tmp/w3d/qa1/ (checker: desktop/, phone/); builder shots in _w3d/.
Checker runs (desktop + phone, --drag): the only reported problems are /api/coach
HTTP 501 from the checker's own static server — an environment artifact, not a page
defect. Under serve.py the whole session logged zero page errors, zero failed
requests, zero console errors/warnings. fps 48–60 throughout.

## Q1. Opening cold — yes
At once, no click needed. Within ~1s the full running world is up: two kitchens,
chefs, cards, both HUD panels, readout; the button already reads "Pause" and the
session counter advances on its own. No blank screen, loader, error box, or black
patch. Shot: /tmp/w3d/qa1/play_s1_fast.png (Session 1, straight-on opening).

## Q2. Keeps running — yes
Through pause, steps, scrubbing 1→40 and back, X-ray toggles, seed change, 2x run,
long drags, zoom, arrow/space/R keys, and the 40→1 wrap, nothing errored, froze,
crashed, flew apart, or got stuck. Playwright logs: ERRORS [], FAILED [],
CONSOLE []. The loop wraps and keeps playing. Shot: /tmp/w3d/qa1/play_loop_end.png
(wrapped to Session 2, still running).

## Q3. Parallax and solid subject — yes
Drag-orbit shows strong near/far sliding (checker: drag changed 0.37 of pixels vs
0.02 idle). Behind and side views show solid counter boxes with plain but closed
backs — no hollow shells, holes, see-through backs, or cardboard cut-outs; the
high three-quarter view and the zoomed close-up hold together with all props
intact. Shots: /tmp/w3d/qa1/play_side_view.png,
/tmp/w3d/qa1/play_orbit3.png, /tmp/w3d/qa1/play_zoomed.png. Note: vertical drags
swing behind rather than reaching true top-down, so "above" is verified to a high
angle only; that reads as a clamp, not a defect.

## Q4. Controls do what's expected — not yet
Desktop yes: Play/Pause, Step +1, Speed, Seed, session scrubber, and X-ray all act
at once and are self-evident; drag orbits, wheel zooms. No keys are advertised and
none are needed (space/arrows/R do nothing harmful). Phone not yet: taps work
(pause/step verified) and touch-drag orbits, but the belief/gate/alpha panel is
display:none at phone width and the two kitchens are cropped at the left/right
edges with the gain chart sitting on top of B's stove — a phone player cannot see
both kitchens or half the HUD at once. Shots: /tmp/w3d/qa1/phone_tap_stepped.png,
/tmp/w3d/qa1/phone/view_idle1.png.

## Q5. What should move, moves well — yes
Flames flicker, steam/smoke rise and drift, chefs stand at different stations per
session, XP popups and floor rings pulse on each advance, action cards change per
session, the camera drifts smoothly, chart lines grow. No stutter, jumps, frozen
parts, or fly-offs in ~30 screenshots. Shots: /tmp/w3d/qa1/bubble_watch0.png
(popups + rings), /tmp/w3d/qa1/play_running_2x.png.

## Q6. Goal, progress, clean restart — not yet
The duel is legible (title, A-vs-B chart with session pointer, per-session readout)
and progress is always shown. Restart is almost clean: reselecting a seed resets to
Session 1 with fresh values, and the loop wraps 40→1 by itself. But the wrap leaks
state: after wrapping, Session 2 still has the steel-blue S21+ stoves, where a
fresh Session 2 has grey stoves. Shots: /tmp/w3d/qa1/play_loop_end.png (S2, blue
stoves) vs /tmp/w3d/qa1/probe_idle.png (S2 fresh, grey stoves).

## Q7. Nameable subject, everything shown — not yet
A stranger names it at a glance: two toy kitchens racing, teal Coach A left,
orange Coach B right. But it does not show everything the brief says: the
per-coach speech bubbles with [offline template]/[live Muse] tags never appear on
screen (they exist in the DOM at y≈9–44, hidden behind the opaque top control
bar — confirmed by element geometry, identical in every shot I and the builder
took), and the charred-plate / uncertainty beats are invisible (see Q8). Shot:
any opening, e.g. /tmp/w3d/qa1/bubble_watch1.png — no bubbles anywhere.

## Q8. Brief line by line — not yet
- Two side-by-side kitchens, teal A left, orange B right: yes (probe_idle.png).
- Stove + pan each: yes. Cutting board with dice: yes (play_zoomed.png shows the
  cubes). Pot, plate with food: yes. Chef that moves between stations: yes —
  chefs stand at different stations across sessions (play_s1_paused.png vs
  play_s9.png vs play_orbit3.png); stills can't confirm a walk animation.
- Action card each session showing the action: yes, with a caveat — the card is
  there and its text changes per session (KNIFE/HEAT/TIMING/STRETCH/EASY seen),
  but it is half-hidden behind the pan (Q11-1); a flip-up motion is not confirmed
  from stills.
- 40-session loop with play/step/speed, seed select, scrubber, X-ray: yes, all
  work (play_s21.png, play_s40.png, play_seed12.png, play_s40_xray.png).
- Coach B belief bars vs truth ticks: yes — ticks appear with X-ray on
  (play_s9_xray.png); readout gains the truth suffix too.
- gate_hat dial: not yet — it is a horizontal bar labeled "gate_hat X / 8", not a
  dial (probe_idle.png, left panel).
- alpha_hat vs true: yes — "α heat x (true y)" line (probe_idle.png).
- Mini A/B/O gain chart with session pointer: yes — three lines plus a dashed
  pointer (play_s9.png, play_s40.png).
- Per-coach speech bubbles: not yet — hidden behind the top bar (see Q7).
- Readout line: yes (every shot, bottom).
- New-stove banner at 21: yes (play_s21.png).
- S1 B flare-up + charred plate, A calm: flare-up yes (flame cone + black smoke,
  play_s1_fast.png); charred plate not yet — B's plate reads the same golden dome
  as A's; A has no flame but does puff dark smoke.
- S9 crossover: yes — orange meets/crosses teal at the pointer (play_s9.png).
- S21 stove swap (steel-blue) + char returns + B uncertainty widens: swap yes
  (play_s21.png, both stoves blue); char returns not yet (plates still golden);
  uncertainty widens not yet (no bands/whiskers anywhere on the bars).
- S40 B ahead near Oracle line: yes (play_s40.png — orange above teal, just under
  the top line).
- Offline template bubbles when no backend; [live Muse]/[offline template] tags
  via /api/coach: not yet visible — the tags exist in DOM text ("[offline
  template]", "[template: averages only]") but are never on screen, with or
  without the backend (builder's _w3d/d_idle.png agrees).

## Q9. More beyond the list — yes
Free orbit plus wheel zoom with close-up detail that holds (dice, pots, pans,
plated food), five seeds × three speeds × scrub × X-ray combinations, transient
XP popups and floor rings, drifting steam/smoke, and a loop that wraps and runs
forever. Worth a player's time. Shots: /tmp/w3d/qa1/play_zoomed.png,
/tmp/w3d/qa1/play_orbit3.png.

## Q10. Looks good — yes
Warm key light shapes the counters and chefs, soft shadows sit under counters,
chefs, and pots, materials read (brushed-steel pots, wood counters, ceramic dice,
glossy pans), teal/orange identities are coherent, and the opening framing leads
the eye straight to the two kitchens. Close-up detail holds. Shot: /tmp/w3d/qa1/play_zoomed.png. (The background
slabs are the weak spot and are listed under Q11.)

## Q11. Show it to a friend as-is — not yet
No. It runs clean and looks charming, but a friend would see cards clipping
through cookware, a background of blank slabs, and (on phone) a cropped duel with
missing HUD — and nothing of the promised coach speech. Details in the verdict.

## Verdict: NOT READY
Shortfalls below, worst-first. The one a player notices most first is #1: it sits
on the subject itself in the very first frame.

1. (noticed first) Action cards sink into the cookware; B's flame cone pierces its
   card. Shot: /tmp/w3d/qa1/play_zoomed.png (also probe_idle.png,
   play_s1_fast.png). Now: "HEAT 8s"/"STRETCH 8s" are half-eaten by the pans and
   the flame renders straight through B's card. Change: move the card anchors
   clear of the stove footprint (or billboard the cards in front) and keep the
   flame behind/depth-tested against the card.
2. Speech bubbles + [offline template]/[live Muse] tags never visible. Shot: any
   (e.g. /tmp/w3d/qa1/bubble_watch1.png); DOM geometry puts the bubble text at
   y≈9–44, behind the opaque top bar. Now: coach text exists only in the DOM.
   Change: anchor the bubbles to the 3D chefs above the counters with a z-index
   above the bar, or dock them in a visible strip under the top bar.
3. S1 charred plate / S21 char returns not visible. Shots:
   /tmp/w3d/qa1/play_s1_paused.png, /tmp/w3d/qa1/play_s21.png. Now: B's plate is
   the same golden dome as A's at both beats. Change: tint the food/plate
   near-black at S1 for B (and at S21+), clearing as skill rises.
4. B uncertainty widening at S21 not visible. Shot: /tmp/w3d/qa1/play_s21.png.
   Now: belief bars carry no uncertainty marks at any session. Change: draw an
   uncertainty band/whisker on the bars that visibly widens at S21.
5. gate_hat is a bar, brief says dial. Shot: /tmp/w3d/qa1/probe_idle.png. Now: a
   horizontal "gate_hat X / 8" bar. Change: render a round dial/gauge, or amend
   the brief.
6. Loop wrap leaks stove state. Shots: /tmp/w3d/qa1/play_loop_end.png (S2 after
   wrap, blue stoves) vs /tmp/w3d/qa1/probe_idle.png (S2 fresh, grey). Change:
   reset session-driven props (stove material and friends) on wrap and seed
   change.
7. Phone layout crops the duel and hides HUD. Shots:
   /tmp/w3d/qa1/phone/view_idle1.png, /tmp/w3d/qa1/phone_tap_stepped.png. Now:
   kitchens cut at both edges, chart covers B's stove, belief/gate/alpha panel is
   display:none. Change: phone-specific framing/panels so both kitchens and the
   belief summary fit.
8. Background slabs read as untextured placeholders. Shots:
   /tmp/w3d/qa1/play_s40.png, /tmp/w3d/qa1/play_seed12.png. Now: a row of flat
   dark monoliths in a void. Change: light them as a kitchen wall or fade them
   into the backdrop.
9. (minor) XP popup covers the action card at every advance. Shot:
   /tmp/w3d/qa1/desktop/view_idle3.png. Change: float the popup above the card.
10. (minor) The camera auto-drifts with no input while running (straight-on at S1
    to a strong angle by S40). Shots: /tmp/w3d/qa1/play_s1_paused.png vs
    /tmp/w3d/qa1/play_s40.png. Change: keep drift but pause it while the pointer
    is down or add a drift toggle; as-is it slowly reframes the charts the
    player is reading.

Non-issues: checker /api/coach 501s come from the checker's static server (clean
under serve.py); machine slowness is not a factor (fps 48–60, native GL).

