from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]


class DashboardHttpTest(unittest.TestCase):
    def test_local_http_contracts_are_available_and_safe(self):
        spec = importlib.util.spec_from_file_location("jarvis_dashboard_http", ROOT / "scripts" / "jarvis_dashboard.py")
        module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            db = base / "telemetry.db"
            module.ROOT = base
            module.Handler.db = db
            module.CHAT_STORE = base / "chat.jsonl"
            module.AUDIT_STORE = base / "audit.jsonl"
            module.SETTINGS_STORE = base / "settings.jsonl"
            module.INTEGRATIONS_STORE = base / "integrations.json"
            module.PROJECTS_CONFIG = base / "projects.json"
            module.ACTIVE_PROJECT_STORE = base / "active-project.json"
            module.PROJECTS_CONFIG.write_text(json.dumps({"projects": [{"project_id": "demo", "name": "Demo", "repository_root": ".", "default_branch": "main", "rag_scope": ["demo"], "allowed_agents": [], "allowed_integrations": [], "policy_ref": "default"}]}), encoding="utf-8")
            module.INTEGRATIONS_STORE.write_text(json.dumps({"integrations": []}), encoding="utf-8")
            server = module.ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                address = f"http://127.0.0.1:{server.server_address[1]}"
                for endpoint in ("/api/commands", "/api/settings", "/api/integrations", "/api/projects", "/api/search?q=jarvis"):
                    with urlopen(address + endpoint, timeout=3) as response:
                        self.assertEqual(response.status, 200)
                        body = json.loads(response.read().decode("utf-8"))
                        self.assertIsInstance(body, dict)
                with urlopen(address + "/api/projects/demo", timeout=3) as response:
                    self.assertEqual(json.loads(response.read().decode("utf-8"))["project_id"], "demo")
                select_request = Request(address + "/api/projects/demo/select", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
                with urlopen(select_request, timeout=3) as response:
                    self.assertEqual(json.loads(response.read().decode("utf-8"))["active_project_id"], "demo")
                with urlopen(address + "/api/dashboard?project_id=demo", timeout=3) as response:
                    self.assertEqual(json.loads(response.read().decode("utf-8"))["project_id"], "demo")
                session_request = Request(address + "/api/chat/sessions", data=json.dumps({"project_id": "demo"}).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with urlopen(session_request, timeout=3) as response:
                    session = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(session["project_id"], "demo")
                missing_project = Request(address + "/api/chat/sessions", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(HTTPError) as error:
                    urlopen(missing_project, timeout=3)
                self.assertEqual(error.exception.code, 400)
                request = Request(address + "/api/settings/drafts", data=json.dumps({"limits": {"max_credits": 2}}).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with urlopen(request, timeout=3) as response:
                    draft = json.loads(response.read().decode("utf-8"))
                self.assertEqual(draft["status"], "DRAFT")
                integration = {"id": "local-test", "type": "LOCAL_ADAPTER", "capabilities": ["health.read"], "authorization": {"mode": "DENY_BY_DEFAULT", "write_confirmation": True}, "timeout_ms": 1000}
                integration_request = Request(address + "/api/integrations", data=json.dumps(integration).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with urlopen(integration_request, timeout=3) as response:
                    registered = json.loads(response.read().decode("utf-8"))
                self.assertFalse(registered["enabled"])
                module.REDMINE_MCP = base / "server.mjs"
                module.REDMINE_MCP.write_text("", encoding="utf-8")
                os.environ["REDMINE_API_KEY"] = "test-key"
                module._redmine_mcp_call = lambda method, params=None: {"server": "redmine-sesab"} if method == "ping" else {"content": [{"type": "text", "text": "issue"}]}
                redmine = {"id": "redmine", "type": "MCP", "enabled": True, "endpoint_ref": "redmine", "capabilities": ["redmine.read.get_issue"], "authorization": {"mode": "READ_ONLY", "write_confirmation": True}, "timeout_ms": 1000, "audit": True}
                redmine_request = Request(address + "/api/integrations", data=json.dumps(redmine).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with urlopen(redmine_request, timeout=3) as response:
                    self.assertEqual(json.loads(response.read().decode("utf-8"))["id"], "redmine")
                with urlopen(address + "/api/integrations/redmine/health", timeout=3) as response:
                    self.assertEqual(json.loads(response.read().decode("utf-8"))["status"], "HEALTHY")
                redmine_call = Request(address + "/api/integrations/redmine/calls", data=json.dumps({"capability": "redmine.read.get_issue", "confirm": True, "arguments": {"issue_id": 1}}).encode(), headers={"Content-Type": "application/json"}, method="POST")
                try:
                    urlopen(redmine_call, timeout=3)
                    self.fail("chamada MCP deveria retornar 501 no teste fake")
                except HTTPError as error:
                    self.assertEqual(error.code, 501)
                    self.assertEqual(json.loads(error.read().decode("utf-8"))["status"], "OK")
                events = base / ".jarvis" / "runs" / "run-sse" / "events.jsonl"
                events.parent.mkdir(parents=True)
                events.write_text(json.dumps({"event": "STATE_TRANSITION", "run_id": "run-sse", "state": "PAUSED", "secret": "must-not-appear"}) + "\n", encoding="utf-8")
                with urlopen(address + "/api/runs/run-sse/events", timeout=3) as response:
                    stream = response.read().decode("utf-8")
                self.assertIn("STATE_TRANSITION", stream)
                self.assertNotIn("must-not-appear", stream)
                denied = Request(address + "/api/runs/missing/actions", data=json.dumps({"action": "PAUSE"}).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(Exception): urlopen(denied, timeout=3)
            finally:
                server.shutdown(); thread.join(timeout=3); server.server_close()


if __name__ == "__main__":
    unittest.main()
