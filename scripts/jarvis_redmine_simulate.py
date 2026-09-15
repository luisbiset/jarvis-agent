#!/usr/bin/env python3
"""Consulta uma tarefa Redmine e simula seu fluxo sem alterar nada."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fetch(base_url: str, issue_id: int) -> dict:
    key = os.environ.get("REDMINE_API_KEY")
    if not key:
        raise RuntimeError("REDMINE_API_KEY não está disponível no ambiente")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/issues/{issue_id}.json",
        headers={"X-Redmine-API-Key": key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Redmine retornou HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"não foi possível consultar o Redmine: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--base-url", default=os.environ.get("REDMINE_URL"))
    args = parser.parse_args()
    if not args.base_url:
        raise SystemExit("REDMINE_URL não está configurada")
    try:
        issue = fetch(args.base_url, args.task_id).get("issue", {})
        subject = str(issue.get("subject", ""))
        task_type = "FRONTEND" if any(word in subject.casefold() for word in ("relatório", "layout", "tela", "html")) else "BACKEND"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/jarvis_simulate.py"), "--task-id", str(args.task_id), "--task-type", task_type, "--estimated-files", "3", "--tests-required"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        simulation = json.loads(result.stdout)
        simulation["redmine"] = {
            "issue_id": args.task_id,
            "project": issue.get("project", {}).get("name"),
            "tracker": issue.get("tracker", {}).get("name"),
            "status": issue.get("status", {}).get("name"),
            "priority": issue.get("priority", {}).get("name"),
            "subject": subject,
        }
        print(json.dumps(simulation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
