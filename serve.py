"""Local server for the 3D kitchen duel (+ optional live Muse voice).

Serves this folder over http (game.html's ES modules cannot load from
file://) and exposes POST /api/coach, which calls generate_coach_reply()
from conversation.py and returns {text, live}. Coach A keeps templates.
Replies are cached per (seed, session, prompt) so scrubbing never re-bills.

  python3 serve.py [--port 8000] [--host 127.0.0.1] [--token SECRET]

Text files go out with an explicit UTF-8 charset, so the .md/.py files
linked from index.html read correctly instead of as mojibake.

--host 0.0.0.0 shares the pages on your local network. Live Muse calls
then stay limited to this machine (or to visitors sending --token in an
X-Coach-Token header); everyone else gets cached or template lines, so the
network never gets an open model proxy billed to your key.

Needs MODEL_API_KEY for live voice; without it every call returns the
offline template tagged live=false.
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import socket
import sys
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from conversation import generate_coach_reply
except Exception:  # pragma: no cover - conversation.py missing
    def generate_coach_reply(system_prompt, fallback_line, model="muse-spark-1.3"):
        return fallback_line, False

CACHE: dict = {}
TOKEN: str | None = None
MAX_PROMPT_CHARS = 2000
# Docs and code are shown as plain text so browsers display them inline.
TEXT_AS_PLAIN = {".md", ".py", ".txt", ".csv"}
# Only the two pages and the files they link to are served. Everything else
# in this folder -- the .git history, agent trajectories, learner logs, any
# .env -- is a 404 and folders are never listed, because --host can share
# this server with the whole local network.
PUBLIC = {"index.html", "game.html", "sim-core.js", "EXPERIMENT.md", "EXPERIMENT-zh-TW.md",
          "benchmark.py", "conversation.py"}


def may_call_live(client_ip: str, token: str | None, sent: str | None) -> bool:
    """Live model calls only for this machine or a caller holding the token."""
    if client_ip in ("127.0.0.1", "::1"):
        return True
    return bool(token) and sent == token


def content_type(path: str, base: str) -> str:
    """Add charset=utf-8 to text types; serve docs and code as text/plain."""
    if os.path.splitext(path)[1].lower() in TEXT_AS_PLAIN:
        return "text/plain; charset=utf-8"
    if base.startswith("text/") or base in ("application/javascript", "application/json"):
        return base + "; charset=utf-8"
    return base


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def guess_type(self, path):
        return content_type(path, super().guess_type(path))

    def send_head(self):
        name = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).lstrip("/") or "index.html"
        if name not in PUBLIC:
            self.send_error(404)
            return None
        return super().send_head()

    def _json(self, obj: dict, code: int = 200) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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
        prompt = str(data.get("system_prompt", ""))[:MAX_PROMPT_CHARS]
        fallback = str(data.get("fallback", ""))
        key = (data.get("seed"), data.get("session"), prompt, fallback)
        if key in CACHE:
            return self._json(CACHE[key])
        if not may_call_live(self.client_address[0], TOKEN, self.headers.get("X-Coach-Token")):
            return self._json({"text": fallback, "live": False})
        text, live = generate_coach_reply(prompt, fallback)
        out = {"text": text, "live": live}
        CACHE[key] = out
        return self._json(out)


def lan_address() -> str:
    """Best-effort LAN IP for the share link (connect() on UDP sends nothing)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # TEST-NET-1: only picks the outgoing interface
            return s.getsockname()[0]
    except OSError:
        return "<your-LAN-IP>"


def main() -> None:
    global TOKEN
    ap = argparse.ArgumentParser(description="Serve the World-Model Coach pages.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1",
                    help="127.0.0.1 = this machine only; 0.0.0.0 = share on your local network")
    ap.add_argument("--token", help="lets network visitors sending X-Coach-Token make live Muse calls")
    args = ap.parse_args()
    TOKEN = args.token
    server = ThreadingHTTPServer((args.host, args.port), functools.partial(Handler, directory=HERE))
    shown = lan_address() if args.host == "0.0.0.0" else args.host
    print(f"serving on http://{shown}:{args.port}/  (game at /game.html, demo at /index.html)")
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print("shared on your network: visitors get cached or template coach lines; "
              "live Muse calls stay on this machine" + (" or need the token" if TOKEN else ""))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
