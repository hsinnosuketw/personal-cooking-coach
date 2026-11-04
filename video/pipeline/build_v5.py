"""Film v5's beats: everything build.py does, with the beats that changed replaced.

    python3 video/pipeline/build_v5.py     # after tts.py; DEMO_VERSION=v5 is set here if it isn't

The comparison is the Gemini Live API on the same footage and recipe (results/gemini_live_*.json, video/script.md).
Unchanged beats (5, 6, 7, 8) come straight from build.py; video/design_guidelines_v5.md has the new components.
"""
import os

os.environ.setdefault("DEMO_VERSION", "v5")
import build as b  # noqa: E402

IN_DUR = b.IN_DUR
TEST_LINE = "Gemini Live API (gemini-3.8-live), tested 4 Nov 2026. Same footage and recipe, one frame every 2 s, asked every 10 s. Not the Gemini app."
LIVE = "GEMINI LIVE"


def beat_0(p):
    """Hook: M1 (fridge) then M2 (onion), cut on "teaching"; the question over both."""
    c = round(p.word(0, "teaching") - b.CUT_LEAD, 3)
    p.footage("M1", *b.tsv("M1"), 0, c)
    p.footage("M2", *b.tsv("M2"), c, p.dur)
    eid, s, _ = p.add(f'<span class="line">{p.say("Your own *coaching chef*?")}</span>', 0.35, p.dur, "full hookline")
    p.js.append(f'tl.fromTo("#{eid} .line", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {s});')
    p.js.append(f'tl.fromTo("#{eid}", {{backgroundColor: "rgba(17,18,20,0)"}}, {{backgroundColor: "rgba(17,18,20,0.28)", duration: {IN_DUR}, ease: "none"}}, {s});')
    p.key(1.5, "M1 · fridge"); p.key(c + 0.8, "M2 · onion")


RECIPE = ["Crack and whisk the eggs", "Oil and heat the pan", "Sauté onions and chillies", "Pour in the eggs", "Fold and stir",
          "Off the heat, season", "Plate with cottage cheese"]     # P08_R03's seven steps, short: the film's first sight of the recipe


def beat_1(p):
    """The recipe on screen over the learner cooking, then the catch in one sentence: you have to keep asking."""
    t = round(p.sent(2)[0] - 0.05, 3)
    p.footage("G1a", "P08", 120.0, 0, p.dur)      # chopping, no phone: it would read as "asking" the phone
    a, z = p.sent(0)[0], round(p.sent(1)[0] - 0.1, 3)
    assert z - p.sent(0)[1] >= 2.0, "the recipe stays 2 s after its sentence"
    sid, ss, _ = p.add("", a, z, "full shade dim")
    p.js.append(f'tl.fromTo("#{sid}", {{opacity: 0}}, {{opacity: 1, duration: {IN_DUR}, ease: "none"}}, {ss});')
    rows = "".join(f"<div>{k + 1}. {p.label(r)}</div>" for k, r in enumerate(RECIPE))
    lid, ls, _ = p.add(f"<small>{p.label('SCRAMBLED EGGS · THE RECIPE')}</small>{rows}", a, z, "recipelist")
    p.js.append(f'tl.fromTo("#{lid} div", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: {IN_DUR}, stagger: 0.06, ease: EASE}}, {ls});')
    p.anim_out(lid, z)
    p.anim_out(sid, z)
    p.shade(t, p.dur)
    cid, cs, _ = p.add(p.label(f"{LIVE} API · SAME VIDEO, SAME RECIPE"), p.sent(1)[0], p.dur, "testchip")
    p.anim_in(cid, cs)
    eid, s, _ = p.add(f'<span class="line">{p.say("Keep *asking*.")}</span>', t, p.dur, "full hookline")      # the narrator's, not a coach card: Gemini never said it
    p.js.append(f'tl.fromTo("#{eid} .line", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {s});')
    p.js.append(f'tl.fromTo("#{eid}", {{backgroundColor: "rgba(17,18,20,0)"}}, {{backgroundColor: "rgba(17,18,20,0.28)", duration: {IN_DUR}, ease: "none"}}, {s});')
    p.cue(s, "pop")
    p.key(round(z - 0.5, 2), "the recipe's seven steps"); p.key(p.sent(1)[0] + 0.6, "G1 · the learner keeps cooking"); p.key(p.dur - 1.0, "keep asking")


def beat_2(p):
    """Chapter 1, then three real answers on the footage they came with, asked every 10 s."""
    ch = 1.1
    p.chapter_card(1, "Gemini *Live*", "live", 0, ch)
    c1, c2, c3 = p.cut(1), p.cut(2), p.cut(3)
    p.footage("G1", "P08", 68.0, ch, c2)
    p.footage("G2", "P08", 211.0, c2, c3)
    p.footage("G3", "P08", 319.5, c3, p.dur)
    p.shade(c1, p.dur)
    for brow, line, s, e in ((f"{LIVE} · 1:10", "Chop the red onion.", c1, c2), (f"{LIVE} · 3:30", "Add a spray of olive oil.", c2, c3),
                             (f"{LIVE} · 5:20", "Whisk the eggs.", c3, p.dur)):
        p.coach("live", brow, line, s, e)
    cid, cs, _ = p.add(p.say("asked every 10 s"), ch, p.dur, "testchip")
    p.anim_in(cid, cs)
    p.key(0.6, "chapter 1"); p.key(c1 + 0.8, "G1 · chop"); p.key(c2 + 0.8, "G2 · oil"); p.key(c3 + 0.9, "G3 · whisk")


def beat_3(p):
    """Four minutes of answers, and the recipe's first step never comes up."""
    t, t2 = p.word(0, "twenty-six"), p.word(0, "not")
    p.footage("G4", "P08", 137.0, 0, p.dur)
    p.shade(t, p.dur)
    p.coach("live", f"{LIVE} · 1:00–5:10", "26 answers", t, p.dur, counter=[(t2, "Eggs: 0")])
    p.key(1.0, "G4 · chopping"); p.key(p.dur - 0.8, "26 answers, eggs 0")


def beat_4(p):
    """When a step has to wait: the same answer, ×18. The film's only red."""
    c1, c2 = p.cut(1), p.cut(2)
    p.footage("G5", "P08", 540.0, 0, c1)
    p.footage("G6", "P08", 576.0, c1, c2)
    p.footage("G7", "P08", 606.0, c2, p.dur)
    p.shade(c1, p.dur)
    a, z = c1 + 0.35, p.word(2, "minutes") + 0.3      # from "Pour the eggs" on: 5 frames a number, landing on "minutes"
    counter = [(c1, "×1")] + [(a + (k - 2) * (z - a) / 16, f"×{k}") for k in range(2, 19)]
    p.coach("live-red", f"{LIVE} · 8:30–11:40", "Pour the eggs.", c1, p.dur, counter=counter, roll=0)
    p.key(1.0, "G5 · plate"); p.key(c1 + 0.8, "G6 · onions, ×1"); p.key(p.dur - 0.5, "G7 · ×18")


def beat_9(p):
    """The sandwich: the cheese and the seasoning; Gemini's eight answers; ours at 8:55; then the salt."""
    c1 = round(p.word(0, "and", 1) - 0.1, 3)
    c2 = round(p.sent(0)[1] + 0.15, 3)
    c3 = p.cut(2)
    c4 = round(p.dur - 3.0, 3)
    assert c4 - c3 >= 3.4, c4 - c3      # the 8:55 reply lifts for 2.6 s and drops back in 0.4 s
    p.panel_shot("B1", "P02", 405.0, 0, c1)
    p.panel_shot("B2", "P02", 421.6, c1, c2)
    p.footage("G8", "P02", 486.0, c2, c3)
    p.panel_shot("B4", "P02", 536.0, c3, c4)
    p.panel_shot("B3", "P02", 561.9, c4, p.dur)
    p.coach("mem", "OUR SYSTEM · 6:17", "Shred cheese meanwhile.", 0.3, c1)
    p.coach("mem", "OUR SYSTEM · 7:01", "Season the eggs first.", c1, c2)
    p.shade(c2, c3)
    t8 = p.word(1, "eight")
    a, z = t8, p.word(1, "sandwich")
    p.coach("live", f"{LIVE} · 8:00–9:10", "Build the sandwich.", t8, c3, counter=[(a, "×1")] + [(a + (k - 1) * (z - a) / 7, f"×{k}") for k in range(2, 9)])
    p.coach("mem", "OUR SYSTEM · 8:55", "Season first.", c3, c4)
    p.zoom("P02", 0, 405.0, 0.8, 3.0, "shredding the cheddar cheese while the eggs and bacon continue cooking", "B1")
    p.zoom("P02", c3, 536.0, round(c3 + 0.3, 3), round(c3 + 2.9, 3), "season the eggs", "B4")
    p.key(1.8, "B1 · cheese marked"); p.key(c1 + 1.0, "B2 · season first"); p.key(c3 - 0.5, "G8 · build the sandwich, ×8")
    p.key(c3 + 2.2, "B4 · 8:55 reply marked"); p.key(p.dur - 0.3, "B3 · salt ticked")


def beat_10(p):
    """How it works: each card lights in turn, with what it takes in and gives back under the row."""
    p.add("", 0, p.dur, "full paper")
    p.footage("pipM2", "P08", 120.0, 0, p.dur, kind="pip")
    p.chapter_card(3, "How it *works*", "mem", 0, 1.0, paper=False)
    hid, hs, _ = p.add(f'<div class="chapter tone-mem small"><b>{p.say("3")}</b><span>{p.say("How it *works*")}</span></div>', 1.0, p.dur, "", "left:96px;top:96px;")
    p.anim_in(hid, hs)
    W, H, A, Y = 260, 172, 36, 270
    chip_w = 236
    x = (1920 - (5 * W + chip_w + 5 * A)) // 2
    xs = []
    for k in range(6):
        xs.append(x)
        x += (W if k < 5 else chip_w) + A
    s1, s2, s3, s4 = (p.sent(i)[0] for i in (1, 2, 3, 4))
    t_vj, t_mem, t_gl, t_d1 = p.word(1, "Vee-Jeppa"), p.word(2, "memory"), p.word(3, "Glimmer"), p.word(4, "D")
    t_next = p.word(4, "next")
    dots = '<div class="dots">' + "".join(f'<i class="{"f" if k in (1, 2, 3, 7) else ""}"></i>' for k in range(1, 8)) + "</div>"
    nodes = [("Video", '<img src="../assets/img/kitchen.jpg" alt="">', s1, None, None), ("V-JEPA 2", b.GLYPH["eye"], t_vj, t_vj, s2 - 0.1),
             ("Memory", dots, t_mem, t_mem, s3 - 0.1), ("Muse Glimmer", b.GLYPH["bubble"], t_gl, t_gl, s4 - 0.1), ("Liquid AI d1", b.GLYPH["arrow"], t_d1, t_d1, p.dur)]
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
    strips = [("Last few seconds of video", "Top 3 next actions", p.word(1, "takes"), p.word(1, "gives"), s2 - 0.1),
              ("Actions seen, with times", "Status, when seen, what needs it", p.word(2, "takes"), p.word(2, "records"), s3 - 0.1),
              ("Recipe, memory, recent actions", "Where you are, what\'s next, what not to forget", p.word(3, "takes"), p.word(3, "says"), s4 - 0.1),
              ("Advice, predictions, checklist", "One next move, every second", p.word(4, "takes"), p.word(4, "picks"), p.dur)]
    for a, c, t_in, t_out, end in strips:
        sid, ss, _ = p.add(f'<small>IN</small><span>{p.say(a)}</span><small class="o">OUT</small><span class="o">{p.say(c)}</span>', t_in, end, "iostrip")
        p.anim_in(sid, ss)
        p.js.append(f'tl.set("#{sid} .o", {{opacity: 0}}, {ss}); tl.fromTo("#{sid} .o", {{opacity: 0, y: 8}}, {{opacity: 1, y: 0, duration: {IN_DUR}, ease: EASE, immediateRender: false}}, {p.frame(t_out)});')
    cid_, cs, _ = p.add(p.label("Next move"), t_next, p.dur, "chip", f"left:{xs[5]}px;top:{Y + H // 2 - 32}px;")
    did, ds, _ = p.add("", t_next, p.dur, "dash", f"left:{xs[5] - A + 6}px;top:{Y + H // 2}px;width:{A - 14}px;")
    p.anim_in(cid_, cs)
    p.js.append(f'tl.fromTo("#{did}", {{opacity: 0}}, {{opacity: 1, duration: {IN_DUR}, ease: "none"}}, {ds});')
    p.key(0.5, "chapter 3"); p.key(s2 - 0.6, "V-JEPA 2 in and out"); p.key(s3 - 0.5, "memory in and out")
    p.key(s4 - 0.5, "Muse Glimmer in and out"); p.key(p.dur - 0.5, "d1 in and out")


def beat_12(p):
    """One video, its six steps, and who reminds you of them ahead of time. No times, no counts."""
    p.add("", 0, p.dur, "full paper")
    p.footage("pipS", "P02", 405.0, 0, p.dur, kind="pip")
    eid, es, _ = p.add(p.label("ONE VIDEO · BACON AND EGG SANDWICH"), 0.2, p.dur, "eyebrow", "left:164px;top:112px;color:#2f9e6e;font-size:26px;")
    p.anim_in(eid, es)
    X_LIVE, X_OURS, Y0, HEAD, ROW = 560, 1040, 170, 72, 88
    t_steps = p.sent(1)[0]
    for x, cls, text in ((164, "live", "Reminded ahead?"), (X_LIVE, "live", "Gemini Live · not asked"), (X_OURS, "ours", "Our system")):
        hid, hs, _ = p.add(p.label(text), t_steps, p.dur, f"reshead {cls}", f"left:{x}px;top:{Y0 + 30}px;")
        p.anim_in(hid, hs)
    rows = [("Cook the bacon", p.word(1, "bacon")), ("Mix the eggs", p.word(1, "mix")), ("Cook the eggs", p.word(1, "cook", 1)),
            ("Shred the cheese", p.word(1, "shred")), ("Season the eggs", p.word(1, "season")), ("Build the sandwich", p.word(1, "build"))]
    y = lambda k: Y0 + HEAD + k * ROW + (ROW - 56) // 2
    for k, (text, t) in enumerate(rows):
        rid, rs, _ = p.add(p.label(text), t - 0.1, p.dur, "resrow", f"top:{Y0 + HEAD + k * ROW}px;")
        p.anim_in(rid, rs)
        p.cue(rs, "tick")
    t_none, t_ours = p.word(2, "none"), p.sent(3)[0]
    for k in range(6):
        did, ds, _ = p.add("—", t_none + k * 0.07, p.dur, "resdash", f"left:{X_LIVE}px;top:{y(k)}px;")
        p.anim_in(did, ds)
    for k in range(5):
        mid, ms, _ = p.add(b.CHECK_SVG, t_ours + 0.1 + k * 0.22, p.dur, "restick", f"left:{X_OURS}px;top:{y(k)}px;")
        p.anim_in(mid, ms)
        p.cue(ms, "tick")
    did, ds, _ = p.add("—", t_ours + 0.1 + 5 * 0.22, p.dur, "resdash", f"left:{X_OURS}px;top:{y(5)}px;")
    p.anim_in(did, ds)
    p.key(p.word(1, "season") + 0.3, "the six steps landing"); p.key(t_none + 0.9, "Gemini Live, not asked: none"); p.key(p.dur - 0.5, "ours: all but the last")


def beat_13(p):
    """The close: as in v4, with the test conditions on the end card."""
    t_end = round(p.sent(0)[1] + 0.5, 3)
    p.footage("C1", "P08", 852.0, 0, t_end)
    p.shade(0, t_end, dim=True)
    eid, s, _ = p.add(f'<span class="line">{p.say("Your own *coaching chef*.")}</span>', 0.25, t_end, "full hookline mem")
    p.js.append(f'tl.fromTo("#{eid} .line", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {s});')
    inner = ('<h1>Personal Cooking <span class="accent">Coach</span></h1>'
             f'<p>{p.label("Built with Meta V-JEPA 2 · Muse Glimmer · Liquid AI d1")}<br>'
             f'{p.label("Footage: HD-EPIC, University of Bristol · CC BY-NC 4.0")}<br>'
             f'{p.label("Music: “Bushwick Tarantella” by Kevin MacLeod (incompetech.com) · CC BY 4.0")}</p>'
             f'<p class="testline">{p.label(TEST_LINE)}</p>')
    cid_, cs, _ = p.add(inner, t_end, p.dur, "full paper endcard")
    p.js.append(f'tl.fromTo("#{cid_}", {{opacity: 0}}, {{opacity: 1, duration: 0.3, ease: "none"}}, {cs});')
    p.js.append(f'tl.fromTo("#{cid_} h1", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: {IN_DUR}, ease: EASE}}, {round(cs + 0.15, 3)});')
    p.key(2.0, "your own coaching chef"); p.key(p.dur - 1.0, "end card")


b.BUILDERS.update({0: beat_0, 1: beat_1, 2: beat_2, 3: beat_3, 4: beat_4, 9: beat_9, 10: beat_10, 12: beat_12, 13: beat_13})
del b.BUILDERS[11]                                      # the memory table: the result now says all the film needs

if __name__ == "__main__":
    b.main()
