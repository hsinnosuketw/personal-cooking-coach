"""Write the HyperFrames pages (one composition per beat) and the footage cut list, from beats.json and timings.json.

    python3 video/pipeline/build.py            # writes video/hyperframes/compositions/beat_XX.html, index.html,
                                               # and video/media/hd/manifest.json (the cuts video/pipeline/cut_clips.py makes)

Every word shown on screen goes through `say()`, which checks it against the words in double quotes in that beat's
`screen` text (numbers and times excepted). Eyebrows and model-name pills go through `label()`: they are evidence
labels, which beats.json exempts from the five-word rule.

The panel shots (beats 6, 8, 9) also read the stage-40 runs in results/ (through panel.py): green ticks on the
panel rows that turn out right, and the coach's reply lifted to the centre. Run it with the package on the path:
    PYTHONPATH=src python3 video/pipeline/build.py
Every pop, tick and whoosh goes to hyperframes/cues.json, which assemble.py turns into the effects track.
"""
import html
import json
import re
import sys
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VIDEO.parent / "src"))
import panel  # noqa: E402  (video/pipeline/panel.py, next to this file)
HF = VIDEO / "hyperframes"
HD = VIDEO / "media" / "hd"
BEATS = {b["id"]: b for b in json.loads((VIDEO / "beats.json").read_text())["beats"]}
TIMES = json.loads((VIDEO / "audio" / "timings.json").read_text())
FPS = TIMES["fps"]
SRC = {"P08": "P08-20240614-085000", "P02": "P02-20240210-113925"}
# The demo page's video of the stage-40 memory run: the footage beside the live panel (world model, coach, d1).
PANEL_RUN = "coach_adaptive_remind_parallel_hdtags_{}"
PANEL_STEPS_TOP = 250    # in panel shots the step row sits under the coach card, clear of the page video's COACH banner
HIT_HOLD = 3.0           # a d1 move that was done keeps its tick this long, while it stays in d1's top 3
ZOOM_W, ZOOM_CY = 1440, 560   # the lifted coach reply: width and centre height on screen
CHECK_SVG = ('<svg width="18" height="18" viewBox="0 0 18 18"><path d="M3 9.5L7.2 13.5L15 4.8" fill="none" stroke="#fff" '
             'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>')
CLIPS = {}
for line in (VIDEO / "clips.tsv").read_text().split("\n"):
    if line.strip():
        cid, vid, a, b = line.split("\t")
        CLIPS[cid] = (vid, float(a), float(b))
CUT_LEAD = 0.12          # a hard cut lands this long before the sentence it belongs to
IN_DUR, OUT_DUR = 0.22, 0.16
STEP_GAP = 28
MAX_PAST_OUT = 6.0       # an aligned shot may run this far past its clips.tsv out-point


def esc(s):
    return html.escape(s, quote=True)


def mmss(sec):
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


class Page:
    """One beat: timed elements on #root plus a GSAP timeline (absolute times, seconds from the beat start)."""

    def __init__(self, bid):
        self.bid = bid
        self.beat = BEATS[bid]
        self.t = TIMES["beats"][str(bid)]
        # A hair under the last frame boundary: HyperFrames renders ceil(duration * fps) frames, and 4-decimal
        # durations such as 6.7667 (= 203.001 frames) would otherwise gain a frame.
        self.dur = round((self.t["frames"] - 0.01) / FPS, 5)
        self.els, self.js, self.media, self.n = [], [], [], 0
        self.quoted = re.findall(r'"([^"]+)"', self.beat["screen"])
        self.keyframes = []      # (time, note) for the storyboard
        self.cues = []           # (time, kind) for the effects track

    # ---- timing helpers ---------------------------------------------------------------------------------------
    def sent(self, i):
        s = self.t["sentences"][i]
        return s["start"], s["end"]

    def word(self, i, w, nth=0):
        hits = [x for x in self.t["sentences"][i]["words"] if x["w"].lower().strip(".,:?!") == w.lower()]
        return hits[nth]["start"]

    def cut(self, i):
        """Where a hard cut for sentence i goes: just before its first word."""
        return round(max(self.sent(i)[0] - CUT_LEAD, 0), 3)

    def frame(self, t):
        return round(round(t * FPS) / FPS, 4)

    # ---- text checks ------------------------------------------------------------------------------------------
    def say(self, text):
        """On-screen words: must be one of the quoted strings in this beat's screen text (or only numbers/times)."""
        plain = text.replace("*", "")
        if not re.fullmatch(r"[×\d:.,\s]+", plain):
            assert plain in self.quoted, f"beat {self.bid}: {plain!r} is not quoted in the screen text {self.quoted}"
        return re.sub(r"\*(.+?)\*", lambda m: f'<span class="accent">{esc(m.group(1))}</span>', esc(text))

    @staticmethod
    def label(text):
        return esc(text)

    # ---- elements ---------------------------------------------------------------------------------------------
    def add(self, inner, start, end, cls="", style="", tag="div", attrs=""):
        self.n += 1
        eid = f"e{self.n}"
        start, end = self.frame(start), min(self.frame(end), self.dur)
        self.els.append(f'<{tag} id="{eid}" class="clip {cls}" style="{style}" data-start="{start}" '
                        f'data-duration="{round(end - start, 4)}" data-track-index="{self.n}"{attrs}>{inner}</{tag}>')
        return eid, start, end

    def footage(self, name, video, src_start, start, end, kind="full", holds=()):
        """A cut of the source footage, made to measure for this shot (video/media/hd/bXX_name.mp4).
        kind="panel" cuts the demo page's video of the stage-40 run instead, so the model panel is in the shot.
        holds = [(source second, seconds)]: the picture freezes there that long (cut_clips.py)."""
        start, end = self.frame(start), min(self.frame(end), self.dur)
        fn = f"b{self.bid:02d}_{name}.mp4"
        src = SRC.get(video, video)
        src = PANEL_RUN.format(src) if kind == "panel" else src
        m = {"file": fn, "video": src, "start": round(src_start, 3), "duration": round(end - start + 0.2, 3), "kind": kind}
        if holds:
            m["holds"] = [[round(a - src_start, 3), round(h, 3)] for a, h in holds]
        self.media.append(m)
        if kind == "pip":
            return self.add("", start, end, "pip", "right:96px;bottom:96px;", tag="video",
                            attrs=f' src="../assets/hd/{fn}" muted playsinline')
        return self.add("", start, end, "full", tag="video", attrs=f' src="../assets/hd/{fn}" muted playsinline')

    def shade(self, start, end, dim=False):
        return self.add("", start, end, "full shade" + (" dim" if dim else ""))

    def anim_in(self, eid, t, origin=None):
        self.js.append(f'tl.fromTo("#{eid}", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {t});')

    def anim_out(self, eid, t):
        self.js.append(f'tl.fromTo("#{eid}", {{opacity: 1}}, {{opacity: 0, duration: {OUT_DUR}, ease: "none", immediateRender: false}}, {round(t - OUT_DUR, 3)});')

    def coach(self, tone, eyebrow, line, start, end, counter=None, cut_out=True):
        """The coach card at top-left; `counter` = [(time, '×N'), ...] rolls a big red number beside it."""
        inner = f'<div class="card"><small>{self.label(eyebrow)}</small><span>{self.say(line)}</span></div>'
        if counter:
            inner += '<div class="counter">' + "".join(f'<span>{self.say(c)}</span>' for _, c in counter) + "</div>"
        eid, s, e = self.add(inner, start, end, f"coach tone-{tone}")
        self.js.append(f'tl.fromTo("#{eid} .card", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {s});')
        self.cue(s, "pop")
        for k, (ct, _) in enumerate(counter or []):
            if k:
                self.cue(ct, "tick")
            sel = f"#{eid} .counter span:nth-child({k + 1})"
            self.js.append(f'tl.fromTo("{sel}", {{opacity: 0, y: 40}}, {{opacity: 1, y: 0, duration: 0.12, ease: EASE}}, {self.frame(ct)});')
            if k + 1 < len(counter):
                self.js.append(f'tl.set("{sel}", {{opacity: 0}}, {self.frame(counter[k + 1][0])});')
        if not cut_out:
            self.anim_out(eid, e)
        return eid

    def steps(self, n, start, end, filled=(), fills=(), big=False, paper=False, y_bottom=96, top_left=None):
        """A row of n step icons, bottom-centre, or from `top_left` = (x, y). `filled` = [(step, time label or '')]
        already on at `start`; `fills` = [(step, time label, when)] that fill during the shot (300 ms + one ring pulse)."""
        size = 96 if big else 64
        gap = 40 if big else STEP_GAP
        width = n * size + (n - 1) * gap
        x0 = (1920 - width) // 2
        lab_h = 34 if big else 28
        y = 1080 - y_bottom - lab_h - 10 - size
        if top_left:
            x0, y = top_left
        rowcls = ("paperrow " if paper else "") + ("big" if big else "")
        parts, pos = [], {}
        for k in range(1, n + 1):
            x = x0 + (k - 1) * (size + gap)
            pos[k] = (x, y)
            parts.append(f'<div class="step {rowcls}" style="position:absolute;left:{x}px;top:{y}px">{k}</div>')
        eid, s, e = self.add("".join(parts), start, end, "full")
        self.js.append(f'tl.fromTo("#{eid}", {{opacity: 0, y: 12}}, {{opacity: 1, y: 0, duration: {IN_DUR}, ease: EASE}}, {s});')
        on = {k: (lab, s) for k, lab in filled}
        on.update({k: (lab, w) for k, lab, w in fills})
        for k, (lab, w) in on.items():
            x, yy = pos[k]
            oid, _, _ = self.add(f"{k}", s, e, f"step on {rowcls}", f"left:{x}px;top:{yy}px;")
            w = self.frame(w)
            if w <= s + 1e-6:
                self.js.append(f'tl.set("#{oid}", {{opacity: 1}}, {s});')
            else:
                self.js.append(f'tl.fromTo("#{oid}", {{opacity: 0, scale: 0.6}}, {{opacity: 1, scale: 1, duration: 0.3, ease: EASE}}, {w});')
                self.cue(w, "tick")
                rid, _, _ = self.add("", w, min(w + 0.6, e), f"step ring {rowcls}", f"left:{x}px;top:{yy}px;")
                self.js.append(f'tl.fromTo("#{rid}", {{opacity: 0.9, scale: 1}}, {{opacity: 0, scale: 1.7, duration: 0.5, ease: "power2.out"}}, {w});')
            if lab:
                tx = x + size // 2 - 60
                lid, _, _ = self.add(self.say(lab), s, e, f"steptime {rowcls}", f"left:{tx}px;top:{yy + size + 10}px;")
                self.js.append(f'tl.fromTo("#{lid}", {{opacity: 0, y: 8}}, {{opacity: 1, y: 0, duration: 0.3, ease: EASE}}, {max(w, s)});')
        return pos

    def chapter_card(self, num, title, tone, start, end, paper=True):
        inner = f'<div class="chapter tone-{tone}"><b>{self.say(str(num))}</b><span>{self.say(title)}</span></div>'
        eid, s, e = self.add(inner, start, end, "full chaptercard" + (" paper" if paper else ""))
        self.cue(s, "whoosh")
        self.js.append(f'tl.fromTo("#{eid} .chapter", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {s});')
        return eid

    def key(self, t, note=""):
        self.keyframes.append((round(t, 2), note))

    def cue(self, t, kind):
        self.cues.append((round(t, 3), kind))

    # ---- panel shots ------------------------------------------------------------------------------------------
    def panel_shot(self, name, video, src_start, start, end, holds=()):
        """A cut of the demo page's video (footage + model panel), with green ticks on the rows that turn out right
        and a Liquid AI label on the decision model. Returns the shot's clock: source second -> beat second."""
        holds = sorted(holds)
        self.footage(name, video, src_start, start, end, kind="panel", holds=holds)
        start, end = self.frame(start), min(self.frame(end), self.dur)
        at = lambda src: start + (src - src_start) + sum(h for x, h in holds if x < src - 1e-9)
        src_end = src_start + (end - start) - sum(h for _, h in holds)
        video = SRC.get(video, video)
        self.marks(video, src_start, src_end, at, [x for x, _ in holds])
        self.model_tag(video, src_start, src_end, at)
        return at

    def model_tag(self, video, a, b, at):
        """'Liquid AI · d1' beside the panel's Decision Model header, which moves when the coach's box changes size."""
        cuts = sorted({a, b} | set(panel.calls_change(video, a, b)))
        for t0, t1 in zip(cuts, cuts[1:]):
            title_y = panel.layout(video, t0 + 1e-4)["d1_rows"][0] - 7 - 30
            self.add(self.label("Liquid AI · d1"), at(t0), at(t1), "modeltag",
                     f"left:{1112 * panel.SCALE:.1f}px;top:{(title_y - 3) * panel.SCALE:.1f}px;")

    def marks(self, video, a, b, at, extra_cuts=()):
        """World-model rows whose prediction comes true (find_moments' rule) get a green outline and tick for that
        tick's second; a d1 row gets them from the moment its move is actually done, for HIT_HOLD s of source time."""
        wm_hits, done = panel.hits(video)
        run = panel.load(video)
        cuts = {a, b} | {float(t) for t in run["_t"] if a < t < b} | set(panel.calls_change(video, a, b)) | set(extra_cuts)
        cuts |= {x for _, s in done for x in (s, s + HIT_HOLD) if a < x < b}
        cuts = sorted(c for c in cuts if a <= c <= b)
        segs = []   # [kind, row, top, t0, t1, fresh]
        for t0, t1 in zip(cuts, cuts[1:]):
            lay = panel.layout(video, t0 + 1e-4)
            i = int(next(k for k, tk in enumerate(run["ticks"]) if tk is lay["tick"]))
            rows = [("wm", k, y) for k, y in enumerate(lay["wm_rows"]) if lay["tick"]["wm"][k][0] in wm_hits[i]]
            now = {act for act, s in done if s <= t0 + 1e-4 < s + HIT_HOLD}
            rows += [("d1", k, y) for k, y in enumerate(lay["d1_rows"]) if lay["tick"]["d1"][k][0] in now]
            for kind, k, y in rows:
                last = next((g for g in reversed(segs) if g[0] == kind and g[1] == k and g[2] == y and abs(g[4] - t0) < 1e-6), None)
                if last:
                    last[4] = t1
                else:
                    fresh = kind == "d1" and any(abs(s - t0) < 1e-3 for _, s in done)
                    segs.append([kind, k, y, t0, t1, fresh])
        for kind, k, y, t0, t1, fresh in segs:
            s0, s1 = at(t0), at(t1)
            left, top = 738 * panel.SCALE, (y - 3) * panel.SCALE
            eid, s, _ = self.add(f"<i>{CHECK_SVG}</i>", s0, s1, f"hit hit-{kind}",
                                 f"left:{left:.1f}px;top:{top:.1f}px;width:{524 * panel.SCALE:.1f}px;height:{23 * panel.SCALE:.1f}px;")
            self.js.append(f'tl.fromTo("#{eid}", {{opacity: 0, scale: 0.96}}, {{opacity: 1, scale: 1, duration: 0.18, ease: EASE}}, {s});')
            if fresh:
                self.cue(s, "check")

    def zoom(self, video, start, src0, t_lift, t_drop, phrase, name):
        """The coach's reply lifts out of the panel, grows to the centre while the rest dims, its key phrase is marked
        in green, and it drops back into place. The box is redrawn crisply (panel.coach_box) from the run, so it is
        exactly what the page shows; nothing may change in it while it is lifted."""
        video = SRC.get(video, video)
        back = t_drop + 0.4
        src_lift, src_back = src0 + (t_lift - start), src0 + (back - start)
        assert not panel.calls_change(video, src_lift - 0.05, src_back), f"beat {self.bid}: the coach box changes during the zoom"
        out = HF / "assets" / "zoom"
        out.mkdir(parents=True, exist_ok=True)
        plain, box = panel.coach_box(video, src_lift, 3)
        marked, _ = panel.coach_box(video, src_lift, 3, phrase)
        fn = f"b{self.bid:02d}_{name}"
        plain.save(out / f"{fn}.png")
        marked.save(out / f"{fn}_mark.png")
        bx, by = box[0] * panel.SCALE, box[1] * panel.SCALE
        bw, bh = (box[2] - box[0] + 1) * panel.SCALE, (box[3] - box[1] + 1) * panel.SCALE
        zh = bh * ZOOM_W / bw
        left, top = (1920 - ZOOM_W) / 2, ZOOM_CY - zh / 2
        sid, _, _ = self.add("", t_lift, back, "full zoomshade")
        inner = (f'<img src="../assets/zoom/{fn}.png" alt=""><img class="mark" src="../assets/zoom/{fn}_mark.png" alt="">')
        zid, s, _ = self.add(inner, t_lift, back, "zoom", f"left:{left:.1f}px;top:{top:.1f}px;width:{ZOOM_W}px;height:{zh:.1f}px;")
        home = f"x: {bx - left:.1f}, y: {by - top:.1f}, scale: {bw / ZOOM_W:.4f}"
        self.js.append(f'tl.fromTo("#{sid}", {{opacity: 0}}, {{opacity: 1, duration: 0.3, ease: "none"}}, {s});')
        self.js.append(f'tl.fromTo("#{zid}", {{{home}}}, {{x: 0, y: 0, scale: 1, duration: 0.45, ease: EASE}}, {s});')
        self.js.append(f'tl.fromTo("#{zid} .mark", {{clipPath: "inset(0% 100% 0% 0%)"}}, {{clipPath: "inset(0% 0% 0% 0%)", duration: 0.6, ease: "power1.inOut"}}, {round(s + 0.55, 3)});')
        self.js.append(f'tl.to("#{zid}", {{{home}, duration: 0.4, ease: "power2.inOut"}}, {self.frame(t_drop)});')
        self.js.append(f'tl.to("#{sid}", {{opacity: 0, duration: 0.4, ease: "none"}}, {self.frame(t_drop)});')
        self.cue(s, "whoosh")
        self.cue(t_drop, "whoosh")
        return zid

    # ---- output -----------------------------------------------------------------------------------------------
    def html(self):
        cid = f"beat-{self.bid:02d}"
        body = "\n    ".join(self.els)
        js = "\n      ".join(self.js)
        return f"""<!doctype html>
<html lang="en" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>Beat {self.bid} · {esc(self.beat['label'])}</title>
    <link rel="stylesheet" href="../assets/fonts/fonts.css" />
    <link rel="stylesheet" href="../assets/style.css" />
    <script src="../assets/vendor/gsap.min.js"></script>
    <script src="../assets/vendor/CustomEase.min.js"></script>
    <style>
      #root {{ position: relative; width: 1920px; height: 1080px; overflow: hidden; background: var(--night);
        font-family: var(--sans); color: var(--ink); font-variant-numeric: tabular-nums; }}
    </style>
  </head>
  <body>
    <!-- Generated by video/pipeline/build.py from beats.json + audio/timings.json; edit those, not this file.
         Say: {esc(self.beat['say'])} -->
    <div id="root" data-composition-id="{cid}" data-start="0" data-duration="{self.dur}" data-width="1920" data-height="1080" data-fps="{FPS}">
    {body}
    </div>
    <script>
      gsap.registerPlugin(CustomEase);
      const EASE = CustomEase.create("hfIn", "0.2,0.8,0.2,1");
      const tl = gsap.timeline({{ paused: true }});
      {js}
      tl.set({{}}, {{}}, {self.dur});
      window.__timelines = window.__timelines || {{}};
      window.__timelines["{cid}"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


# ---------------------------------------------------------------------------------------------------------------
# The beats
# ---------------------------------------------------------------------------------------------------------------

def tsv(cid, offset=0.0):
    vid, a, _ = CLIPS[cid]
    return vid, a + offset


def beat_0(p):
    """Hook: M1 (fridge) then M2 (onion), cut on the second sentence; the question over both."""
    c = p.cut(1)
    p.footage("M1", *tsv("M1"), 0, c)
    p.footage("M2", *tsv("M2"), c, p.dur)
    eid, s, e = p.add(f'<span class="line">{p.say("Your own *coaching chef*?")}</span>', 0.35, p.dur, "full hookline")
    p.js.append(f'tl.fromTo("#{eid} .line", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {s});')
    p.js.append(f'tl.fromTo("#{eid}", {{backgroundColor: "rgba(17,18,20,0)"}}, {{backgroundColor: "rgba(17,18,20,0.28)", duration: {IN_DUR}, ease: "none"}}, {s});')
    p.key(1.5, "M1 · fridge"); p.key(c + 1.0, "M2 · onion")


def aligned(cid, said_at, offset_in_shot, length):
    """Source in-point so the footage shows `said_at` (video seconds) when the card lands `offset_in_shot` into the shot.
    It never starts before the tsv in-point and runs at most MAX_PAST_OUT seconds past the tsv out-point."""
    vid, a, b = CLIPS[cid]
    s = max(said_at - offset_in_shot, a)
    return vid, min(s, max(b + MAX_PAST_OUT - length, a))


def beat_1(p):
    """The catch: N6 (eggs in the pan), the no-memory card, and the counter rolling to ×14 over the second sentence."""
    t_card = round(p.sent(1)[0] - 0.05, 3)
    p.footage("N6", *aligned("N6", 808, t_card, p.dur), 0, p.dur)
    p.shade(t_card, p.dur)
    a, b = p.word(1, "crack"), p.sent(1)[1] - 0.1
    counter = [(t_card, "×1")] + [(a + (k - 2) * (b - a) / 12, f"×{k}") for k in range(2, 15)]
    p.coach("nomem", "OTHER CHEF · 13:28", "Crack the eggs.", t_card, p.dur, counter=counter)
    p.key(1.4, "N6 · eggs in the pan"); p.key(b + 0.6, "card + ×14")


def beat_2(p):
    """Chapter 1, then three hard cuts (N1, N2, N3), one per coach line, the counter stepping ×1, ×2, ×3."""
    ch = 1.1
    p.chapter_card(1, "Other *chefs*", "nomem", 0, ch)
    cuts = [p.cut(1), p.cut(2), p.cut(3)]
    shots = [("N1", 68, "OTHER CHEF · 1:08", ch, cuts[1]), ("N2", 185, "OTHER CHEF · 3:05", cuts[1], cuts[2]),
             ("N3", 212, "OTHER CHEF · 3:32", cuts[2], p.dur)]
    for k, (cid, said, brow, s, e) in enumerate(shots):
        card_t = cuts[k]
        p.footage(cid, *aligned(cid, said, card_t - s, e - s), s, e)
        p.shade(card_t, e)
        p.coach("nomem", brow, "Crack the eggs.", card_t, e, counter=[(card_t, f"×{k + 1}")])
    p.key(0.6, "chapter 1"); p.key(cuts[0] + 0.6, "N1 · ×1"); p.key(cuts[1] + 0.6, "N2 · ×2"); p.key(cuts[2] + 0.8, "N3 · ×3")


def beat_3(p):
    """N4 (cracking the eggs; the egg icon fills with 5:13), then N5 at 8:54 where the no-memory card asks again."""
    c = p.cut(2)
    p.footage("N4", *tsv("N4"), 0, c)
    p.footage("N5", *aligned("N5", 534, 0.0, p.dur - c), c, p.dur)
    p.shade(0, p.dur)
    p.steps(1, 0.25, p.dur, fills=[(1, "5:13", p.word(1, "cracked"))])
    p.coach("nomem", "OTHER CHEF · 8:54", "Crack the eggs.", c, p.dur)
    p.key(p.word(1, "cracked") + 1.0, "N4 · egg icon 5:13"); p.key(c + 1.0, "N5 · asks again")


def beat_4(p):
    """N7: the eggs go onto the plate; the no-memory card says to add the onions."""
    p.footage("N7", *tsv("N7"), 0, p.dur)
    t = p.word(1, "says")
    p.shade(t, p.dur)
    p.coach("nomem", "OTHER CHEF · 13:59", "Add the onions.", t, p.dur)
    p.key(1.2, "N7 · plating"); p.key(p.dur - 0.6, "card on the finished plate")


def beat_5(p):
    """The turn: full-bleed memory green, one line, a slow push-in."""
    eid, s, e = p.add(f'<span class="line">{p.say("We designed a *system*.")}</span>', 0, p.dur, "full turn")
    p.js.append(f'tl.fromTo("#{eid} .line", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, 0.1);')
    p.js.append(f'tl.fromTo("#{eid} .line", {{scale: 1}}, {{scale: 1.04, duration: {round(p.dur - 0.32, 3)}, ease: "none", immediateRender: false}}, 0.32);')
    p.key(1.2, "turn card")


def beat_6(p):
    """Chapter 2, then the demo page's video (footage + model panel): M1 (plate first) and M2 (onion), with our
    system going along. M1 is moved past its clips.tsv window so the 0:39 answer reaches the panel with its card; the
    reply lifts to the centre as the narrator gets to "fine, do it in parallel", and holds about 2 s. In M2 the world
    model's "peel onion" (tick 1:58.2) turns out right; the picture freezes 1 s so its tick stays 2 s."""
    ch = 1.1
    p.chapter_card(2, "With our *system*", "mem", 0, ch)
    c = p.cut(2)
    t_card = ch + 0.5
    m1 = 39.1 - (t_card - ch)                                  # from the sink to the cottage-cheese plate
    p.panel_shot("M1", "P08", m1, ch, c)
    p.panel_shot("M2", "P08", 117.6, c, p.dur, holds=[(118.7, 1.0)])
    p.coach("mem", "OUR SYSTEM · 0:39", "Plate first? Fine.", t_card, c)
    p.coach("mem", "OUR SYSTEM · 1:45", "Keep going.", c, p.dur)
    p.zoom("P08", ch, m1, p.word(1, "goes") + 0.33, c - 0.45, "fine to do in parallel", "M1")
    p.key(0.6, "chapter 2"); p.key(p.word(1, "fine") + 0.8, "M1 · reply lifted, parallel marked"); p.key(c + 1.6, "M2 · peel onion ticked, held")


def beat_7(p):
    """Four two-second shots; with each, its step icon fills with the moment it was first seen."""
    shots = [(7, "0:13", 13.0), (3, "1:50", 110.0), (2, "4:36", 276.0), (1, "5:13", 313.0)]
    L = p.dur / 4
    fills = []
    for k, (step, lab, src) in enumerate(shots):
        s, e = k * L, (k + 1) * L
        p.footage(f"S{step}", "P08", src, s, e)
        fills.append((step, lab, s + 0.35))
        p.key(s + L * 0.75, f"step {step} · {lab}")
    p.shade(0, p.dur)
    p.steps(7, 0, p.dur, fills=fills)


def ledger_on(video, t):
    """Steps the memory has started or finished at second t, for a step row that agrees with the panel."""
    tick, _, _ = panel.state(SRC.get(video, video), t)
    return [(k + 1, "") for k, st in enumerate(tick["ledger"]) if st != "not started"]


def beat_8(p):
    """E1: at 4:53 the coach steers the learner back to the eggs (card, then the reply lifted to the centre, held).
    E2: d1's top 3 are open package, break egg, take egg; the learner opens the carton (5:12.1), takes an egg (5:13.1)
    and cracks it (5:13.7). The picture freezes at least 0.5 s on each tick, long enough that each lands on the
    narration's "Open", "Take", "Crack". The step row shows what the memory has (2, 3, 7) and fills step 1 when the
    memory marks it, at 5:16.2."""
    c = p.cut(2)
    t_card = round(p.sent(1)[0] - 0.05, 3)
    e1 = 293.5 - t_card                                       # the 4:53 answer reaches the panel as the card lands
    p.panel_shot("E1", "P08", e1, 0, c)
    acts = [(312.08, p.word(3, "open")), (313.13, p.word(4, "take")), (313.72, p.word(5, "crack"))]   # (done, said)
    holds = [(src, max(0.5, round((nw - w) - (ns - src), 3)) if k + 1 < len(acts) else 0.5)
             for k, ((src, w), (ns, nw)) in enumerate(zip(acts, acts[1:] + acts[-1:]))]
    e2 = acts[0][0] - (acts[0][1] - c)                        # the carton opens on the word "Open"
    at = p.panel_shot("E2", "P08", e2, c, p.dur, holds=holds)
    fill = at(316.233)
    assert fill < p.dur - 0.3, f"beat 8: step 1 fills at {fill:.2f}, past the end; lengthen EXTRA_TAIL[8]"
    p.steps(7, 0, p.dur, filled=ledger_on("P08", e1), fills=[(1, "", fill)], top_left=(96, PANEL_STEPS_TOP))
    p.coach("mem", "OUR SYSTEM · 4:53", "Back to the eggs.", t_card, c)
    p.zoom("P08", 0, e1, t_card + 0.35, c - 0.5, "back to cracking and whisking the eggs", "E1")
    p.key(t_card + 1.8, "E1 · reply lifted, eggs marked"); p.key(at(313.13) + 0.3, "E2 · open and take ticked")
    p.key(at(313.72) + 0.3, "E2 · crack ticked"); p.key(fill + 0.4, "E2 · step 1 filled")


def beat_9(p):
    """Bacon & Egg on the demo page's video. B1, 6:45: the learner gets the baguette ready and cuts it while the 6:17 cheese answer is
    the latest (card, reply lifted with the cheese line marked); the world model's "cut bread" and d1's "cut bread
    (step 6)" turn out right (the cut at 6:49.1, after the reply has dropped back). B2: the 7:01 answer (season first) arrives at the cut. B3, 9:20: salt into the hand;
    the world model's "pour salt" and d1's "take salt" (done 9:24.3) get their ticks. No step row: the memory marks
    seasoning only at 9:42."""
    c1 = round(p.word(0, "and", 1) - 0.1, 3)
    c2 = round(p.sent(0)[1] + 0.15, 3)
    p.panel_shot("B1", "P02", 405.0, 0, c1)
    p.panel_shot("B2", "P02", 421.6, c1, c2)
    p.panel_shot("B3", "P02", 560.0, c2, p.dur)
    p.coach("mem", "OUR SYSTEM · 6:17", "Shred cheese meanwhile.", 0.3, c1)
    p.coach("mem", "OUR SYSTEM · 7:01", "Season the eggs first.", c1, c2)
    p.zoom("P02", 0, 405.0, 0.8, 3.0, "shredding the cheddar cheese while the eggs and bacon continue cooking", "B1")
    p.key(1.8, "B1 · reply lifted, cheese marked"); p.key(c1 - 0.8, "B1 · cut bread ticked"); p.key(c1 + 1.6, "B2 · season first")
    p.key(p.dur - 0.3, "B3 · salt ticked")


GLYPH = {
    "eye": '<svg width="64" height="34" viewBox="0 0 64 34"><path d="M3 17C14 2 50 2 61 17C50 32 14 32 3 17Z" fill="none" stroke="#8a8a8e" stroke-width="3.5"/><circle cx="32" cy="17" r="7" fill="#8a8a8e"/></svg>',
    "bubble": '<svg width="58" height="44" viewBox="0 0 58 44"><path d="M5 4H53V30H24L13 40V30H5Z" fill="none" stroke="#8a8a8e" stroke-width="3.5" stroke-linejoin="round"/></svg>',
    "arrow": '<svg width="58" height="40" viewBox="0 0 58 40"><path d="M4 20H48M34 6L50 20L34 34" fill="none" stroke="#8a8a8e" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}


def beat_10(p):
    """How it works: cards and dashed arrows on paper, each named card lit with its question; the kitchen in a corner."""
    p.add("", 0, p.dur, "full paper")
    p.footage("pipM2", "P08", 120.0, 0, p.dur, kind="pip")     # 2:00 on: the onion keeps being cut until 2:35
    # chapter marker: centred for a second, then a header top-left
    p.chapter_card(3, "How it *works*", "mem", 0, 1.0, paper=False)
    hid, hs, _ = p.add(f'<div class="chapter tone-mem small"><b>{p.say("3")}</b><span>{p.say("How it *works*")}</span></div>',
                       1.0, p.dur, "", "left:96px;top:96px;")
    p.anim_in(hid, hs)
    W, H, A, Y = 260, 172, 36, 370
    chip_w = 236
    total = 5 * W + chip_w + 5 * A
    x = (1920 - total) // 2
    xs = []
    for k in range(6):
        xs.append(x)
        x += (W if k < 5 else chip_w) + A
    s1, s2, s3 = p.sent(1)[0], p.sent(2)[0], p.sent(3)[0]
    t_vj, t_gl, t_d1 = p.word(1, "Vee-Jeppa"), p.word(2, "Glimmer"), p.word(3, "D")
    t_next = p.word(3, "next")
    nodes = [  # (label pill, inner glyph, appears, lit from, lit to)
        ("Video", '<img src="../assets/img/kitchen.jpg" alt="">', s1, None, None),
        ("V-JEPA 2", GLYPH["eye"], t_vj, t_vj, s2 - 0.1),
        ("Memory", '<div class="dots">' + "".join(f'<i class="{"f" if k in (1, 2, 3, 7) else ""}"></i>' for k in range(1, 8)) + "</div>",
         s2, None, None),
        ("Muse Glimmer", GLYPH["bubble"], t_gl, t_gl, s3 - 0.1),
        ("Liquid AI d1", GLYPH["arrow"], t_d1, t_d1, p.dur),
    ]
    for k, (lab, glyph, t_in, lit0, lit1) in enumerate(nodes):
        nid, ns, _ = p.add(f"<em>{p.label(lab)}</em>{glyph}", t_in, p.dur, "node", f"left:{xs[k]}px;top:{Y}px;width:{W}px;height:{H}px;")
        p.anim_in(nid, ns)
        if k:
            did, ds, _ = p.add("", t_in, p.dur, "dash", f"left:{xs[k] - A + 6}px;top:{Y + H // 2}px;width:{A - 14}px;")
            p.js.append(f'tl.fromTo("#{did}", {{opacity: 0}}, {{opacity: 1, duration: {IN_DUR}, ease: "none"}}, {ds});')
        if lit0 is not None:
            lit0 = p.frame(lit0)
            p.js.append(f'tl.set("#{nid}", {{borderColor: "#2f9e6e"}}, {lit0}); tl.set("#{nid} em", {{backgroundColor: "#2f9e6e", color: "#ffffff"}}, {lit0});')
            if lit1 < p.dur - 0.01:
                lit1 = p.frame(lit1)
                p.js.append(f'tl.set("#{nid}", {{borderColor: "rgba(0,0,0,0)"}}, {lit1}); tl.set("#{nid} em", {{backgroundColor: "#e9eee9", color: "#1c1c1e"}}, {lit1});')
    # the questions, one at a time, under the card being named
    qs = [(1, "What's next?", p.word(1, "answers"), s2 - 0.1), (3, "What matters?", p.word(2, "answers"), s3 - 0.1),
          (4, "One move.", t_next, p.dur)]
    for k, q, a, b in qs:
        cx = xs[k] + W // 2
        qid, qs_, _ = p.add(p.say(q), a, b, "q", f"left:{cx - 200}px;top:{Y + H + 26}px;width:400px;text-align:center;")
        p.anim_in(qid, qs_)
    cid_, cs, _ = p.add(p.label("Next move"), t_next, p.dur, "chip", f"left:{xs[5]}px;top:{Y + H // 2 - 32}px;")
    did, ds, _ = p.add("", t_next, p.dur, "dash", f"left:{xs[5] - A + 6}px;top:{Y + H // 2}px;width:{A - 14}px;")
    p.anim_in(cid_, cs)
    p.js.append(f'tl.fromTo("#{did}", {{opacity: 0}}, {{opacity: 1, duration: {IN_DUR}, ease: "none"}}, {ds});')
    p.key(0.5, "chapter 3"); p.key(p.word(1, "answers") + 1.0, "V-JEPA 2 · what's next?")
    p.key(p.word(2, "answers") + 1.0, "Muse Glimmer · what matters?"); p.key(p.dur - 0.5, "d1 · one move")


def beat_11(p):
    """The memory: action chips pop on a timeline, lift off and drop into their step slots, which show the first-seen time."""
    p.add("", 0, p.dur, "full paper")
    X0, X1, TY = 200, 1720, 330
    span = 360.0
    X = lambda sec: round(X0 + (X1 - X0) * sec / span)
    tid, ts, _ = p.add("", 0.25, p.dur, "track", f"left:{X0}px;top:{TY}px;width:{X1 - X0}px;")
    p.anim_in(tid, ts)
    for sec in (0, 120, 240, 360):
        kid, ks, _ = p.add(p.say(mmss(sec)), 0.25, p.dur, "tick", f"left:{X(sec) - 40}px;top:{TY + 22}px;width:80px;text-align:center;")
        p.anim_in(kid, ks)
    named = {313: "take egg", 110: "cut onion", 276: "spray oil"}
    for sec in (13, 24, 39, 69, 150, 185, 212, 250, 329, 445):   # other actions on the timeline, unlabelled
        bid_, bs, _ = p.add("", 0.4, p.dur, "blip", f"left:{X(sec) - 23}px;top:{TY - 9}px;")
        p.anim_in(bid_, bs)
    acts = [("take egg", 313, 1, "5:13", p.word(1, "take")), ("cut onion", 110, 3, "1:50", p.word(1, "cut")),
            ("spray oil", 276, 2, "4:36", p.word(1, "spray"))]
    fly = 0.5
    fills = [(step, lab, t + 0.35 + fly) for _, _, step, lab, t in acts]
    pos = p.steps(7, 0.25, p.dur, fills=fills, big=True, paper=True, y_bottom=300)
    for text, sec, step, lab, t in acts:
        sx, sy = pos[step]
        dx, dy = sx + 48 - X(sec), sy + 48 - TY
        aid, as_, _ = p.add(p.say(text), t, t + 0.35 + fly + 0.05, "act", f"left:{X(sec)}px;top:{TY}px;")
        p.js.append(f'tl.set("#{aid}", {{xPercent: -50, yPercent: -50}}, 0);')
        p.js.append(f'tl.fromTo("#{aid}", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {as_});')
        p.js.append(f'tl.to("#{aid}", {{y: -18, scale: 1.05, duration: 0.18, ease: "power2.out"}}, {round(as_ + 0.2, 3)});')
        p.js.append(f'tl.to("#{aid}", {{x: {dx}, y: {dy}, scale: 0.55, duration: {fly}, ease: "power2.inOut"}}, {round(as_ + 0.35, 3)});')
        p.js.append(f'tl.to("#{aid}", {{opacity: 0, duration: 0.08, ease: "none"}}, {round(as_ + 0.35 + fly - 0.05, 3)});')
    p.key(1.2, "timeline and empty steps"); p.key(acts[1][4] + 0.25, "cut onion lifts"); p.key(p.dur - 0.6, "three steps with first-seen times")


def beat_12(p):
    """The result: two tinted panels, 5 (no memory) and 1 (memory) requests to crack the eggs after 7:41."""
    p.add("", 0, p.dur, "full paper")
    eid, es, _ = p.add(p.label("ASKED TO CRACK EGGS AFTER 7:41"), 0.2, p.dur, "eyebrow", "left:0;width:1920px;top:212px;text-align:center;color:#8a8a8e;font-size:24px;")
    p.anim_in(eid, es)
    PW, G, PY = 720, 48, 290
    x0 = (1920 - 2 * PW - G) // 2
    a, b = p.word(0, "asked"), p.word(0, "five")
    nomem = [(0.35, "0")] + [(a + (k - 1) * (b - a) / 4, str(k)) for k in range(1, 6)]
    mem = [(0.35, "0"), (p.word(1, "once"), "1")]
    for k, (cls, lab, seq) in enumerate([("nomem", "Other chef", nomem), ("mem", "Our system", mem)]):
        spans = "".join(f"<span>{p.say(v)}</span>" for _, v in seq)
        pid, ps, _ = p.add(f'<div class="numstack">{spans}</div><div class="lab">{p.say(lab)}</div>', 0.3, p.dur, f"panel {cls}",
                           f"left:{x0 + k * (PW + G)}px;top:{PY}px;")
        p.anim_in(pid, ps)
        for j, (t, _) in enumerate(seq):
            sel = f"#{pid} .numstack span:nth-child({j + 1})"
            p.js.append(f'tl.fromTo("{sel}", {{opacity: 0, y: 40}}, {{opacity: 1, y: 0, duration: 0.12, ease: EASE}}, {p.frame(t)});')
            if j + 1 < len(seq):
                p.js.append(f'tl.set("{sel}", {{opacity: 0}}, {p.frame(seq[j + 1][0])});')
    p.key(b + 0.4, "5 in the no-memory panel"); p.key(p.dur - 1.0, "5 and 1, held")


def beat_13(p):
    """The close: the plate being seasoned, dimmed, under the opening line's echo; then the end card with the credits."""
    t_end = round(p.sent(0)[1] + 0.5, 3)
    p.footage("C1", "P08", 852.0, 0, t_end)
    p.shade(0, t_end, dim=True)
    eid, s, e = p.add(f'<span class="line">{p.say("Your own *coaching chef*.")}</span>', 0.25, t_end, "full hookline mem")
    p.js.append(f'tl.fromTo("#{eid} .line", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {s});')
    inner = ('<h1>Personal Cooking <span class="accent">Coach</span></h1>'
             f'<p>{p.label("Built with Meta V-JEPA 2 · Muse Glimmer · Liquid AI d1")}<br>'
             f'{p.label("Footage: HD-EPIC, University of Bristol · CC BY-NC 4.0")}<br>'
             f'{p.label("Music: “Bushwick Tarantella” by Kevin MacLeod (incompetech.com) · CC BY 4.0")}</p>')
    cid_, cs, _ = p.add(inner, t_end, p.dur, "full paper endcard")
    p.js.append(f'tl.fromTo("#{cid_}", {{opacity: 0}}, {{opacity: 1, duration: 0.3, ease: "none"}}, {cs});')
    p.js.append(f'tl.fromTo("#{cid_} h1", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {round(cs + 0.15, 3)});')
    p.key(2.0, "your own coaching chef"); p.key(p.dur - 1.0, "end card")


BUILDERS = {0: beat_0, 1: beat_1, 2: beat_2, 3: beat_3, 4: beat_4, 5: beat_5, 6: beat_6, 7: beat_7,
            8: beat_8, 9: beat_9, 10: beat_10, 11: beat_11, 12: beat_12, 13: beat_13}


def index_html(ids):
    """The whole film for the Studio preview: each beat page mounted at its start on the narration timeline."""
    total = max(TIMES["beats"][str(i)]["start"] + TIMES["beats"][str(i)]["duration"] for i in ids)
    mounts = "\n    ".join(
        f'<div id="m{i:02d}" class="clip full" data-composition-id="beat-{i:02d}" data-composition-src="compositions/beat_{i:02d}.html" '
        f'data-start="{TIMES["beats"][str(i)]["start"]}" data-duration="{TIMES["beats"][str(i)]["duration"]}" data-track-index="0"></div>'
        for i in ids)
    return f"""<!doctype html>
<html lang="en" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>Personal Cooking Coach · demo v4</title>
    <link rel="stylesheet" href="assets/fonts/fonts.css" />
    <link rel="stylesheet" href="assets/style.css" />
    <script src="assets/vendor/gsap.min.js"></script>
  </head>
  <body>
    <!-- Generated by video/pipeline/build.py. The video is rendered beat by beat (compositions/beat_XX.html);
         this page strings them together, with the narration, for the Studio preview. -->
    <div id="root" data-composition-id="film" data-start="0" data-duration="{round(total, 4)}" data-width="1920" data-height="1080" data-fps="{FPS}">
    {mounts}
    <audio id="narration" class="clip" src="assets/narration.wav" data-start="0" data-duration="{round(total, 4)}" data-track-index="1"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.set({{}}, {{}}, {round(total, 4)});
      window.__timelines = window.__timelines || {{}};
      window.__timelines["film"] = tl;
    </script>
  </body>
</html>
"""


def main():
    (HF / "compositions").mkdir(parents=True, exist_ok=True)
    HD.mkdir(parents=True, exist_ok=True)
    media, keys, cues = [], {}, {}
    for bid, fn in sorted(BUILDERS.items()):
        p = Page(bid)
        fn(p)
        (HF / "compositions" / f"beat_{bid:02d}.html").write_text(p.html(), encoding="utf-8")
        media += p.media
        keys[str(bid)] = p.keyframes
        cues[str(bid)] = sorted(p.cues)
        print(f"beat {bid:2d}  {p.dur:6.2f}s  {len(p.els):3d} elements  {len(p.media)} shots  {p.beat['label']}")
    (HD / "manifest.json").write_text(json.dumps(media, indent=1))
    (HF / "index.html").write_text(index_html(sorted(BUILDERS)), encoding="utf-8")
    (HF / "keyframes.json").write_text(json.dumps(keys, indent=1))
    (HF / "cues.json").write_text(json.dumps(cues, indent=1))


if __name__ == "__main__":
    main()
