"""Local server for the 3D kitchen duel (+ optional live Muse voice).

Serves this folder over http (game.html's ES modules cannot load from
file://) and exposes POST /api/coach, which calls generate_coach_reply()
from conversation.py and returns {text, live}. Coach A keeps templates.
Replies are cached per (seed, session) so scrubbing never re-bills.

  python3 serve.py [--port 8000]

Needs MODEL_API_KEY for live voice; without it every call returns the
offline template tagged live=false.
"""
from __future__ import annotations

import functools
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

try:
    from conversation import generate_coach_reply
except Exception:  # pragma: no cover - conversation.py missing
    def generate_coach_reply(system_prompt, fallback_line, model="muse-spark-1.3"):
        return fallback_line, False

CACHE: dict = {}


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, obj: dict, code: int = 200) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/coach":
            return self._json({"error": "not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, OSError):
            return self._json({"error": "bad request"}, 400)
        key = (data.get("seed"), data.get("session"))
        if key in CACHE:
            return self._json(CACHE[key])
        text, live = generate_coach_reply(
            data.get("system_prompt", ""), data.get("fallback", ""))
        out = {"text": text, "live": live}
        CACHE[key] = out
        return self._json(out)


def main() -> None:
    port = 8000
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"serving on http://127.0.0.1:{port}/  (game at /game.html)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
