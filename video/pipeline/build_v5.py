"""Film v5's beats: everything build.py does, with the beats that changed replaced.

    python3 video/pipeline/build_v5.py     # after tts.py; DEMO_VERSION=v5 is set here if it isn't

The comparison is the Gemini Live API on the same footage and recipe (results/gemini_live_*.json, video/script.md).
Unchanged beats (5, 6, 7, 8) come straight from build.py; video/design_guidelines_v5.md has the new components.
"""
import json
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


def beat_1(p):
    """The catch, in one sentence: you have to keep asking."""
    t = round(p.sent(2)[0] - 0.05, 3)
    p.footage("G1a", "P08", 120.0, 0, p.dur)      # chopping, no phone: it would read as "asking" the phone
    p.shade(t, p.dur)
    p.coach("live", f"{LIVE} API · SAME VIDEO, SAME RECIPE", "Keep asking.", t, p.dur)
    p.key(1.4, "G1 · the onion"); p.key(p.dur - 1.0, "keep asking")


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
    a, z = c2 + 0.12, p.word(2, "minutes")
    counter = [(c1, "×1")] + [(a + (k - 2) * (z - a) / 16, f"×{k}") for k in range(2, 19)]
    p.coach("live-red", f"{LIVE} · 8:30–11:40", "Pour the eggs.", c1, p.dur, counter=counter)
    p.key(1.0, "G5 · plate"); p.key(c1 + 0.8, "G6 · onions, ×1"); p.key(p.dur - 0.5, "G7 · ×18")


def beat_9(p):
    """The sandwich: the cheese and the seasoning; Gemini's eight answers; ours at 8:55; then the salt."""
    c1 = round(p.word(0, "and", 1) - 0.1, 3)
    c2 = round(p.sent(0)[1] + 0.15, 3)
    c3 = p.cut(2)
    c4 = round(p.dur - 4.4, 3)
    p.panel_shot("B1", "P02", 405.0, 0, c1)
    p.panel_shot("B2", "P02", 421.6, c1, c2)
    p.footage("G8", "P02", 486.0, c2, c3)
    p.panel_shot("B4", "P02", 536.0, c3, c4)
    p.panel_shot("B3", "P02", 560.5, c4, p.dur)
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
              ("Actions seen, with times", "A record per step", p.word(2, "takes"), p.word(2, "keeps"), s3 - 0.1),
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


MEMORY = [  # step, name, status class, status, first, last, needed before, reminded: our answer at 4:53, checked in beat_11
    (1, "Eggs", "", "not seen yet", "", "", "step 4", ""), (2, "Oil", "done", "done", "3:17", "4:33", "step 3", "×5"),
    (3, "Onions", "done", "done", "0:06", "4:28", "step 4", ""), (4, "Pour", "", "not seen yet", "", "", "step 5", ""),
    (5, "Stir", "", "not seen yet", "", "", "step 6", ""), (6, "Off heat", "", "not seen yet", "", "", "", ""),
    (7, "Plate", "part", "in progress", "0:06", "4:28", "", "")]


def check_memory():
    """The table must be what the run said at 4:53, errors included."""
    run = json.loads((b.VIDEO.parent / "results" / "coach_adaptive_remind_parallel_hdtags_P08-20240614-085000.json").read_text())
    call = next(c for c in run["calls"] if abs(c["ready"] - 293.46) < 1)
    for s in ("is done, first sign 3:17 last 4:33", "is done, first sign 0:06 last 4:28", "is in progress, first sign 0:06 last 4:28",
              "is not seen yet; needed before step 4", "is not seen yet; needed before step 5", "is not seen yet; needed before step 6", "DONE: 2,3", "IN PROGRESS: 7"):
        assert s in call["text"], s
    assert sum(c.get("remind") == 1 for c in run["calls"] if c["ready"] <= call["ready"]) == 5
    assert run["needs"]["2"] == [1] and run["needs"]["3"] == [0, 2]      # oil before step 3; eggs and onions before step 4


def beat_11(p):
    """What the memory records: the real table at 4:53, each column lit as it is named, then the eggs."""
    check_memory()
    p.add("", 0, p.dur, "full paper")
    eid, es, _ = p.add(p.label("OUR SYSTEM · MEMORY AT 4:53"), 0.2, p.dur, "eyebrow", "left:150px;top:128px;color:#2f9e6e;font-size:26px;")
    p.anim_in(eid, es)
    heads = ["Step", "Status", "First seen", "Last seen", "Needed before", "Reminded"]
    cells = "".join(f'<div class="head">{p.label(h)}</div>' for h in heads)
    for n, name, cls, status, first, last, need, told in MEMORY:
        cells += (f"<div>{n} {p.label(name)}</div><div><i class=\"{cls}\"></i>{p.label(status)}</div><div>{first}</div><div>{last}</div>"
                  f"<div>{p.label(need)}</div><div>{told}</div>")
    tid, ts, _ = p.add(cells, 0.3, p.dur, "memtable")
    p.anim_in(tid, ts)
    X0, Y0, HEAD, ROW = 150, 196, 62, 88
    widths = [300, 340, 220, 220, 300, 240]
    left = lambda k: X0 + sum(widths[:k])
    h_all = HEAD + 7 * ROW
    t_stat, t_first, t_need, t_told, t_eggs = p.word(1, "done"), p.word(1, "first"), p.word(1, "which"), p.word(1, "how"), p.sent(2)[0]
    for k0, k1, a, z in ((1, 2, t_stat, t_first), (2, 4, t_first, t_need), (4, 5, t_need, t_told), (5, 6, t_told, t_eggs)):
        cid, cs, _ = p.add("", a, z, "memcol", f"left:{left(k0)}px;top:{Y0}px;width:{left(k1) - left(k0)}px;height:{h_all}px;")
        p.js.append(f'tl.fromTo("#{cid}", {{opacity: 0}}, {{opacity: 1, duration: 0.2, ease: "none"}}, {cs});')
        p.cue(cs, "tick")
    dim, ds, _ = p.add("", t_eggs, p.dur, "memdim", f"left:{X0}px;top:{Y0 + HEAD + ROW}px;width:1620px;height:{6 * ROW}px;")
    p.js.append(f'tl.fromTo("#{dim}", {{opacity: 0}}, {{opacity: 0.6, duration: 0.25, ease: "none"}}, {ds});')
    rid, rs, _ = p.add("", t_eggs, p.dur, "memrow", f"left:{X0}px;top:{Y0 + HEAD}px;width:1620px;height:{ROW}px;")
    p.js.append(f'tl.fromTo("#{rid}", {{opacity: 0}}, {{opacity: 1, duration: 0.25, ease: "none"}}, {rs});')
    p.cue(rs, "check")
    p.key(1.2, "the memory at 4:53"); p.key(t_stat + 0.6, "status"); p.key(t_first + 0.6, "first and last seen"); p.key(t_need + 0.5, "needed before")
    p.key(t_told + 0.6, "reminded"); p.key(p.dur - 0.6, "the eggs: not seen, needed before step 4")


def beat_12(p):
    """The result: one number about us, and the limit."""
    p.add("", 0, p.dur, "full paper")
    eid, es, _ = p.add(p.label("STEPS BROUGHT UP BEFORE THEY STARTED · NOBODY ASKED"), 0.2, p.dur, "eyebrow", "left:0;width:1920px;top:232px;text-align:center;color:#8a8a8e;font-size:24px;")
    p.anim_in(eid, es)
    pid, ps, _ = p.add(f'<div class="big">{p.say("6 of 11")}</div>', p.word(0, "six"), p.dur, "panel mem solo", "left:480px;top:300px;")
    p.anim_in(pid, ps)
    p.cue(ps, "pop")
    p.key(p.word(0, "six") + 0.8, "6 of 11"); p.key(p.dur - 1.0, "held under the limit")


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


b.BUILDERS.update({0: beat_0, 1: beat_1, 2: beat_2, 3: beat_3, 4: beat_4, 9: beat_9, 10: beat_10, 11: beat_11, 12: beat_12, 13: beat_13})

if __name__ == "__main__":
    b.main()
