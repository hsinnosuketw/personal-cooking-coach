"""Checks for serve.py. Run: python3 test_serve.py"""
import functools
import json
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import serve


def test_content_type_adds_charset():
    assert serve.content_type("EXPERIMENT.md", "text/markdown") == "text/plain; charset=utf-8"
    assert serve.content_type("benchmark.py", "text/x-python") == "text/plain; charset=utf-8"
    assert serve.content_type("index.html", "text/html") == "text/html; charset=utf-8"
    assert serve.content_type("sim-core.js", "text/javascript") == "text/javascript; charset=utf-8"
    assert serve.content_type("results.png", "image/png") == "image/png"


def test_live_calls_limited_to_local_or_token():
    assert serve.may_call_live("127.0.0.1", None, None)
    assert serve.may_call_live("::1", None, None)
    assert not serve.may_call_live("192.168.0.5", None, None)
    assert not serve.may_call_live("192.168.0.5", "s3cret", "wrong")
    assert serve.may_call_live("192.168.0.5", "s3cret", "s3cret")


def test_server_charset_and_per_session_replies():
    os.environ.pop("MODEL_API_KEY", None)  # offline: replies are the fallback lines
    server = ThreadingHTTPServer(("127.0.0.1", 0),
                                 functools.partial(serve.Handler, directory=serve.HERE))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(base + "/EXPERIMENT-zh-TW.md", timeout=10) as r:
            assert r.headers["Content-Type"] == "text/plain; charset=utf-8"
            assert any("一" <= ch <= "鿿" for ch in r.read().decode("utf-8"))

        def coach(session, fallback):
            body = json.dumps({"seed": 7, "session": session,
                               "system_prompt": f"plan for {session}", "fallback": fallback}).encode()
            req = urllib.request.Request(base + "/api/coach", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())

        one, five = coach(1, "stretch line"), coach(5, "heat line")
        assert one == {"text": "stretch line", "live": False}
        assert five == {"text": "heat line", "live": False}, "sessions must not share a cached reply"
    finally:
        server.shutdown()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(tests)} tests passed")
