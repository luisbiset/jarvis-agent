"""Small framework-free HTTP API for canonical operation Runs."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .runs import RunService
from .projects import list_projects
from ..operations import catalog


class RunApiHandler(BaseHTTPRequestHandler):
    service = RunService()

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(size) or b"{}")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/")
        if path == "/api/operations":
            return self._send(200, {"operations": catalog()})
        if path == "/api/projects":
            return self._send(200, {"projects": list_projects()})
        if path == "/api/runs":
            return self._send(200, {"runs": self.service.list()})
        if path.startswith("/api/runs/"):
            item = self.service.get(path.rsplit("/", 1)[-1])
            return self._send(200 if item else 404, item or {"error": "run not found"})
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/")
        try:
            if path == "/api/runs":
                return self._send(201, self.service.create(self._body()))
            if path.startswith("/api/runs/") and path.endswith("/execute"):
                run_id = path.split("/")[-2]
                try:
                    return self._send(200, self.service.execute(run_id))
                except KeyError:
                    return self._send(404, {"error": f"run not found: {run_id}"})
            if path.startswith("/api/runs/") and path.endswith("/cancel"):
                run_id = path.split("/")[-2]
                try:
                    return self._send(200, self.service.cancel(run_id))
                except KeyError:
                    return self._send(404, {"error": f"run not found: {run_id}"})
            self._send(404, {"error": "not found"})
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
            self._send(400, {"error": str(error)})

    def log_message(self, *_args) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8766) -> None:
    ThreadingHTTPServer((host, port), RunApiHandler).serve_forever()
