"""Loopback-only, mobile-friendly review dashboard for the local mock workflow."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from mock_github import PROJECT, ROOT, STATE, prepare, read_state, review, save_state
from generate_calendar import generate


class Handler(BaseHTTPRequestHandler):
    def send_file(self, path: Path, content_type: str):
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def json_response(self, value, code=200):
        data = json.dumps(value).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])
        if path == "/":
            return self.send_file(ROOT / "dashboard/index.html", "text/html; charset=utf-8")
        if path == "/api/state":
            state = read_state()
            m = json.loads((PROJECT / "manifest.json").read_text(encoding="utf-8"))
            state["caption"] = m["x_caption"]
            calendar = ROOT / "output/calendar.json"
            if not calendar.is_file():
                generate(calendar)
            state["calendar"] = json.loads(calendar.read_text(encoding="utf-8"))["entries"][:14]
            return self.json_response(state)
        if path == "/video":
            return self.send_file(ROOT / "output/001-saharan-dust/saharan-dust.mp4", "video/mp4")
        if path == "/thumbnail":
            return self.send_file(PROJECT / "assets/thumbnail.png", "image/png")
        if path.startswith("/mock-gallery/science/"):
            rel = path.removeprefix("/mock-gallery/science/") or "index.html"
            base = (ROOT / "output/mock-gallery/science").resolve()
            target = (base / rel).resolve()
            if target != base and base not in target.parents:
                return self.send_error(403)
            ext = target.suffix.lower()
            if target.is_dir():
                target = target / "index.html"
                ext = ".html"
            typ = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json", ".geojson": "application/geo+json", ".png": "image/png", ".mp4": "video/mp4", ".md": "text/markdown; charset=utf-8"}.get(ext, "application/octet-stream")
            return self.send_file(target, typ)
        self.send_error(404)

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size > 10000:
            return self.json_response({"error": "Request too large"}, 413)
        try:
            body = json.loads(self.rfile.read(size) or b"{}")
            if self.path == "/api/prepare":
                p = prepare()
                return self.json_response({"message": f"Mock PR #{p['number']} is ready for review"})
            if self.path in ("/api/approve", "/api/reject"):
                p = review(self.path.removeprefix("/api/"))
                return self.json_response({"message": f"Mock PR #{p['number']}: {p['status']}"})
            if self.path == "/api/feedback":
                message = str(body.get("text", "")).strip()
                if not message or len(message) > 2000:
                    raise ValueError("Feedback must be 1–2000 characters")
                state = read_state()
                state["feedback"].append({"project_id": PROJECT.name, "text": message})
                save_state(state)
                return self.json_response({"message": "Feedback saved locally"})
            self.send_error(404)
        except (ValueError, KeyError) as exc:
            self.json_response({"error": str(exc)}, 400)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Local review dashboard: http://127.0.0.1:{args.port}/", flush=True)
    server.serve_forever()
