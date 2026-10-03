#!/usr/bin/env python3
"""
The learning journal.

    python3 journal/serve.py
    python3 journal/serve.py --port 8765

Opens a local site at http://127.0.0.1:8765
Today is the first page. Each day has something to implement and something
to publish. Posts are markdown files in journal/posts/.
"""

import argparse
import datetime
import json
import pathlib
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
POSTS = HERE / "posts"
sys.path.insert(0, str(HERE))
import curriculum  # noqa: E402

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def progress_snapshot() -> dict:
    """Best-effort bars from progress.py --track core. Never fails the page."""
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "progress.py"), "--track", "core"],
            cwd=ROOT, capture_output=True, text=True, timeout=30)
        return {"ok": True, "text": result.stdout}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "text": str(exc)}


def read_post(day: str) -> dict:
    path = POSTS / f"{day}.md"
    if not path.exists():
        return {"date": day, "exists": False, "body": ""}
    return {"date": day, "exists": True, "body": path.read_text()}


def write_post(day: str, body: str) -> dict:
    POSTS.mkdir(exist_ok=True)
    path = POSTS / f"{day}.md"
    path.write_text(body)
    return {"date": day, "exists": True, "body": body, "saved": True}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/curriculum":
            days = curriculum.build()
            today = datetime.date.today().isoformat()
            return self._send(200, json.dumps({
                "today": today,
                "start": curriculum.START.isoformat(),
                "end": curriculum.END.isoformat(),
                "week": curriculum.week_of(),
                "days": days,
            }))

        if path == "/api/today":
            entry = curriculum.today_entry()
            today = datetime.date.today().isoformat()
            post = read_post(today)
            return self._send(200, json.dumps({
                "today": today,
                "entry": entry,
                "post": post,
            }))

        if path.startswith("/api/posts/"):
            day = path.rsplit("/", 1)[-1]
            return self._send(200, json.dumps(read_post(day)))

        if path == "/api/posts":
            POSTS.mkdir(exist_ok=True)
            listing = []
            for path in sorted(POSTS.glob("*.md")):
                text = path.read_text()
                listing.append({
                    "date": path.stem,
                    "bytes": path.stat().st_size,
                    "preview": text.strip().splitlines()[0] if text.strip() else "",
                })
            return self._send(200, json.dumps(listing))

        if path == "/api/progress":
            return self._send(200, json.dumps(progress_snapshot()))

        rel = path.lstrip("/") or "index.html"
        if ".." in rel.split("/"):
            return self._send(403, json.dumps({"error": "forbidden"}))
        file = (HERE / rel).resolve()
        if HERE not in file.parents and file != HERE:
            return self._send(403, json.dumps({"error": "forbidden"}))
        if not file.is_file():
            return self._send(404, json.dumps({"error": "not found"}))
        return self._send(200, file.read_bytes(),
                          MIME.get(file.suffix, "application/octet-stream"))

    def do_PUT(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/posts/"):
            return self._send(405, json.dumps({"error": "method not allowed"}))
        day = parsed.path.rsplit("/", 1)[-1]
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body)
            text = payload.get("body", "")
        except json.JSONDecodeError:
            text = body
        return self._send(200, json.dumps(write_post(day, text)))


def main(argv) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)
    POSTS.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"journal — {curriculum.START.isoformat()} to {curriculum.END.isoformat()}",
          flush=True)
    print(f"open http://{args.host}:{args.port}/", flush=True)
    print("posts land in journal/posts/YYYY-MM-DD.md", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
