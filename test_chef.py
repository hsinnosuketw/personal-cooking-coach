"""Checks for the cooking game and its learning loop. Run: python3 test_chef.py"""
import functools
import json
import pathlib
import random
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from chef import agent, bots, physics, store
from chef.learn import LearnedWorldModel, transitions

HERE = pathlib.Path(__file__).parent
ACTIONS = [(5, False, False), (7, True, False), (9, False, False), (9, False, True), (3, False, False)] * 12


def test_browser_rules_match_python_engine():
    """play.html logs the dataset, so its JS rules must equal chef/physics.py exactly."""
    html = (HERE / "play.html").read_text(encoding="utf-8")
    rules = html[html.index("// ---------- Game rules"):html.index("// ---------- Scene")]
    start = {"color": 0.05, "moisture": 1.0, "heat": 5, "salted": False, "salted_wet": False,
             "cut_cv": 0.3, "scorch": 0}
    js = rules + f"""
let s = {json.dumps(start)}, t = 0; const out = [];
for (const [h, salt, water] of {json.dumps(ACTIONS)}) {{ s = tick(s, h, salt, water); t += DT; out.push([s, score(s, t).total]); }}
console.log(JSON.stringify(out));"""
    got = json.loads(subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True,
                                    text=True, check=True).stdout)
    s, t = dict(start, heat=5.0), 0.0
    for (h, salt, water), (js_state, js_total) in zip(ACTIONS, got):
        s, t = physics.tick(s, h, salt, water), t + physics.DT
        for k in ("color", "moisture", "scorch", "salted", "salted_wet"):
            assert js_state[k] == s[k], (t, k, js_state[k], s[k])
        assert js_total == physics.score(s, t)["total"]


def test_scorch_makes_blasting_the_heat_a_bad_strategy():
    def cook(heat, cut):
        s, t = dict(physics.new_state(random.Random(0)), cut_cv=cut), 0
        while s["color"] < 0.29 and t < physics.TIME_LIMIT:
            s, t = physics.tick(s, heat, t == 0, False), t + physics.DT
        return physics.score(s, t)["total"]
    assert cook(5, 0.05) > cook(9, 0.05), "heat 9 is faster but scorches"
    assert cook(4, 0.35) > cook(5, 0.35), "a ragged dice wants a lower heat"


def test_store_rejects_bad_rounds_and_recomputes_the_score():
    ep = bots.play("careful", seed=3)
    claimed = dict(ep, final=dict(ep["final"], score={"total": 9999}))
    clean = store.validate(json.dumps(claimed).encode())
    assert clean["final"]["score"] == ep["final"]["score"] and clean["source"] == "human"
    for broken in ({"transitions": []}, dict(ep, transitions=[{"t": 0, "s": {}, "a": {}, "s2": {}}]),
                   dict(ep, final={"t": 0, "state": dict(ep["final"]["state"], heat=42)})):
        try:
            store.validate(json.dumps(broken).encode())
        except (ValueError, KeyError, TypeError):
            continue
        raise AssertionError(f"accepted a bad round: {list(broken)}")


def test_world_model_learned_from_play_lets_the_ai_chef_cook():
    eps = [bots.play(style, seed=i) for i, style in enumerate(list(bots.STYLES) * 10)]
    model = LearnedWorldModel().fit(*transitions(eps))
    run = agent.play(model, seed=7)
    final = run["final"]
    assert 0.2 < final["state"]["color"] <= physics.MAX_COLOR and final["state"]["scorch"] < 0.05, final
    assert final["score"]["total"] > max(e["final"]["score"]["total"] for e in eps) - 5


def test_saving_a_round_over_http():
    folder = pathlib.Path(tempfile.mkdtemp())
    real = store.HUMAN_DIR
    store.HUMAN_DIR = folder
    import serve
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(serve.Handler, directory=serve.HERE))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        ep = bots.play("careful", seed=5)
        req = urllib.request.Request(base + "/api/episodes", data=json.dumps(dict(ep, player="tester<b>")).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            assert json.loads(r.read())["leaderboard"]["human_rounds"] == 1
        saved = json.loads(next(folder.glob("*.json")).read_text())
        assert saved["player"] == "testerb" and saved["source"] == "human"
        try:
            urllib.request.urlopen(urllib.request.Request(base + "/api/episodes", data=b"{}"), timeout=10)
            raise AssertionError("empty round accepted")
        except urllib.error.HTTPError as e:
            assert e.code == 400
        with urllib.request.urlopen(base + "/play.html", timeout=10) as r:
            assert r.status == 200
    finally:
        server.shutdown()
        store.HUMAN_DIR = real


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(tests)} tests passed")
