"""Serve the demo page (site/) over http, read-only, with video seeking.

  python3 -m coach.render.serve [--port 8080] [--host 127.0.0.1]

Python's built-in server ignores Range requests, so browsers can't seek the
MP4s (Safari won't play them at all). This one answers single byte ranges.
Only files inside site/ are served, without directory listings. For a
public link, keep the host at 127.0.0.1 and put a tunnel in front:

  cloudflared tunnel --url http://127.0.0.1:8080
"""
from __future__ import annotations

import argparse
import functools
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..config import SITE as DEMO
CHUNK = 1 << 20


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def list_directory(self, path):
        self.send_error(404)
        return None

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        if self.path.split("?")[0].endswith((".js", ".html", "/")):  # coach.js is rebuilt often; stop browsers reusing an old copy
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", "").strip())
        if not m or not os.path.isfile(path) or not (m.group(1) or m.group(2)):
            return super().do_GET()
        size = os.path.getsize(path)
        if m.group(1):
            start, end = int(m.group(1)), min(int(m.group(2) or size - 1), size - 1)
        else:  # "bytes=-N": the last N bytes
            start, end = max(0, size - int(m.group(2))), size - 1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            try:
                while left:
                    buf = f.read(min(CHUNK, left))
                    self.wfile.write(buf)
                    left -= len(buf)
            except (BrokenPipeError, ConnectionResetError):  # the browser seeks elsewhere and drops this one
                pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), functools.partial(Handler, directory=str(DEMO)))
    print(f"serving {DEMO} on http://{args.host}:{args.port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
