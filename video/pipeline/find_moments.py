"""Find shots for the panel beats where the models are visibly right: the world model's top 3 holds the action the
narrators recorded about a second later, and the learner goes on to do one of d1's top-3 moves soon after.

    PYTHONPATH=src python3 video/pipeline/find_moments.py              # per-run hit rates + best windows per beat need
    PYTHONPATH=src python3 video/pipeline/find_moments.py --ticks P08 100 135   # second by second, one stretch

A tick (one per second) scores a world-model hit when one of its top-3 "verb noun" names equals a verb-noun pair of a
narration overlapping [t + 0.5, t + 2] (the probe predicts about 1 s ahead), and a d1 hit when one of d1's top-3
actions is the main action of a narration that starts within D1_HORIZON s after t (the move was actually made:
"open egg carton to get egg" is open package, not yet take egg). Names are compared in EPIC-KITCHENS
words, through HDEpicExtractor's class maps. A name matches a narration when it is one of its verb-noun pairs, or
when its verb and its noun both occur in it: the parsed pairs are noisy ("begin slicing red onion" -> turn-on knife;
"pull out small pan ... and place on stove" -> pull cupboard, put hob), so pairs alone miss real hits.
"""
import json
import sys
from pathlib import Path

from coach.data.extractors import HDEpicExtractor
from coach.data.vocab import Vocab

ROOT = Path(__file__).resolve().parents[2]
RUN = str(ROOT / "results" / "coach_adaptive_remind_parallel_hdtags_{}.json")
VIDEOS = {"P08": "P08-20240614-085000", "P02": "P02-20240210-113925"}
D1_HORIZON = 8.0
# What each panel beat needs: (beat, label, video, from s, to s). The window must sit while the right coach answer
# is the latest one on the panel (from its ready time until the next answer), so the card's eyebrow stays true.
NEEDS = [(6, "plate first (answer 0:39)", "P08", 39.1, 61.1),
         (6, "onion, keep going (answer 1:45)", "P08", 105.7, 127.0),
         (8, "oil reminder (answer 2:07)", "P08", 127.0, 213.6),
         (8, "learner oils the pan", "P08", 236.0, 293.5),
         (9, "cheese meanwhile (answer 6:17)", "P02", 377.9, 421.6),
         (9, "season first (answer 7:01)", "P02", 421.6, 440.3),
         (9, "the eggs get seasoned", "P02", 535.7, 600.0)]


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def score(vid, hd):
    run = json.loads(Path(RUN.format(VIDEOS[vid])).read_text())
    narr = hd.narr[hd.narr.video_id == VIDEOS[vid]].sort_values("start_timestamp")
    acts = []   # (start, end, matcher, narration text)
    for r in narr.itertuples():
        pairs = {f"{hd.verb_key.get(v)} {hd.noun_key.get(n)}" for v, n in list(r.pair_classes) + list(r.main_action_classes)}
        verbs, nouns = {hd.verb_key.get(v) for v in r.verb_classes}, {hd.noun_key.get(n) for n in r.noun_classes}
        match = lambda name, pairs=pairs, verbs=verbs, nouns=nouns: (
            name in pairs or (name.split(" ", 1)[0] in verbs and name.split(" ", 1)[-1] in nouns))
        main = {f"{hd.verb_key.get(v)} {hd.noun_key.get(n)}" for v, n in r.main_action_classes}
        acts.append((r.start_timestamp, r.end_timestamp, match, r.narration.strip(), main))
    rows = []
    for tk in run["ticks"]:
        t = tk["t"]
        now = [a for a in acts if a[0] <= t + 2 and a[1] >= t + 0.5]
        wm = [a for a, _ in tk["wm"]]
        wm_hit = [a for a in wm if any(x[2](a) for x in now)]
        d1_done = []
        for a, step, _ in tk["d1"]:
            when = next((x[0] for x in acts if t <= x[0] <= t + D1_HORIZON and a in x[4]), None)
            if when is not None:
                d1_done.append((a, step, round(when - t, 1)))
        rows.append({"t": t, "wm": wm, "now": [x[3] for x in now], "wm_hit": wm_hit, "d1": [(a, s) for a, s, _ in tk["d1"]],
                     "d1_done": d1_done, "narr": next((x[3] for x in acts if x[0] <= t + 1 <= x[1]), "")})
    return run, rows


def windows(rows, a, b, length=4.0):
    """Best stretches of `length` s inside [a, b): the share of ticks with a world-model hit, plus the share
    with a d1 move that is then done; both must be non-zero."""
    out = []
    ts = [r for r in rows if a <= r["t"] < b]
    for i, r in enumerate(ts):
        span = [x for x in ts[i:] if x["t"] < r["t"] + length]
        if len(span) < length - 1:
            continue
        wm = sum(bool(x["wm_hit"]) for x in span) / len(span)
        d1 = sum(bool(x["d1_done"]) for x in span) / len(span)
        if wm and d1:
            out.append((wm + d1, wm, d1, r["t"], span))
    out.sort(key=lambda o: -o[0])
    picked = []
    for o in out:   # no two overlapping picks
        if all(abs(o[3] - p[3]) >= length for p in picked):
            picked.append(o)
    return picked[:3]


def main():
    hd = HDEpicExtractor(Vocab.load())
    if "--ticks" in sys.argv:
        vid, a, b = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
        _, rows = score(vid, hd)
        for r in rows:
            if a <= r["t"] <= b:
                print(f"{mmss(r['t'])}  wm {'HIT ' if r['wm_hit'] else '    '}{', '.join(r['wm']):44.44}  "
                      f"d1 {'DONE' if r['d1_done'] else '    '} {', '.join(a for a, _ in r['d1']):36.36} "
                      f"{r['d1_done'] or ''}  | {r['narr'][:60]}")
        return
    runs = {vid: score(vid, hd) for vid in VIDEOS}
    for vid, (_, rows) in runs.items():
        scored = [r for r in rows if r["now"]]
        print(f"{vid}: world-model top-3 hit {sum(bool(r['wm_hit']) for r in scored)}/{len(scored)} narrated seconds; "
              f"d1 top-3 done within {D1_HORIZON:.0f} s at {sum(bool(r['d1_done']) for r in rows)}/{len(rows)} ticks")
    for beat, label, vid, a, b in NEEDS:
        print(f"\nbeat {beat} · {label} · {vid} {mmss(a)}-{mmss(b)}")
        for total, wm, d1, t0, span in windows(runs[vid][1], a, b):
            print(f"  {mmss(t0)}  wm {wm:.0%}  d1 {d1:.0%}")
            for x in span:
                print(f"     {mmss(x['t'])} wm={x['wm_hit'] or '-'} d1={x['d1_done'] or '-'}  | {x['narr'][:70]}")


if __name__ == "__main__":
    main()
