import json
import sys
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from aghuse_assistant.api.http import RunApiHandler


class CanonicalRunApiTest(unittest.TestCase):
    def request(self, base, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(base + path, data=data, headers={"Content-Type": "application/json"}, method="POST" if data else "GET")
        try:
            response = urlopen(request)
            return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_canonical_run_api(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), RunApiHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}"
            payload = json.dumps({"project": "aghuse", "operation": "ANALYZE", "objective": "investigar"}).encode()
            request = Request(base + "/api/runs", data=payload, headers={"Content-Type": "application/json"}, method="POST")
            run = json.loads(urlopen(request).read())
            self.assertEqual(run["operation"], "ANALYZE")
            runs = json.loads(urlopen(base + "/api/runs").read())
            self.assertEqual(runs["runs"][0]["run_id"], run["run_id"])
            projects = json.loads(urlopen(base + "/api/projects").read())
            self.assertEqual(projects["projects"][0]["project_id"], "aghuse")
            status, _ = self.request(base, "/api/runs", {"project": "unknown", "operation": "ANALYZE", "objective": "x"})
            self.assertEqual(status, 400)
            status, _ = self.request(base, "/api/runs", {"project": "aghuse", "operation": "INVALID", "objective": "x"})
            self.assertEqual(status, 400)
            status, _ = self.request(base, "/api/runs/missing/cancel", {})
            self.assertEqual(status, 404)
            status, _ = self.request(base, "/api/runs", {"project": "aghuse"})
            self.assertEqual(status, 400)
            status, _ = self.request(base, "/api/runs/missing/execute", {})
            self.assertEqual(status, 404)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
