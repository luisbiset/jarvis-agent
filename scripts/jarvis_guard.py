#!/usr/bin/env python3
"""Auditor local de segurança e prontidão Git; não altera o repositório."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(r"(?i)(-----BEGIN .*PRIVATE KEY-----|(?:password|passwd|secret|api[_-]?key|token)\s*[=:]\s*[^\s$<{]{4,})")
PRIVATE_URL = re.compile(r"(?i)https?://[^\s]*(?:intra|datacenter|saude|prodeb|hcpa)[^\s]*")
CLINICAL = re.compile(r"(?i)\b(?:prontu[aá]rio|paciente|patient|cpf|cns)\b\s*[:=]\s*[0-9]{4,}")
SKIP = {".git", ".jarvis", "target", "node_modules", ".idea", ".vscode", "__pycache__"}
PUBLIC_URLS = ("redmine.saude.ba.gov.br", "developers.openai.com", "github.com")


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, text=True, capture_output=True, check=True)
    return [root / line for line in result.stdout.splitlines() if line and not any(part in SKIP for part in Path(line).parts)]


def audit(root: Path) -> dict:
    findings = []
    for path in tracked_files(root):
        if not path.is_file():
            continue
        if path.name == "jarvis_guard.py" or (path.suffix == ".py" and path.name.startswith("test_")):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        meaningful_lines = "\n".join(line for line in text.splitlines() if "re.compile" not in line and "Pattern(" not in line and "secret-scan: allow-test-fixture" not in line and not path.name.endswith(".env.example") and not any(token in line for token in ("requiredEnv(", "requiredText(", "process.env.", "redact(", "apiKey:", "const password =")))
        for pattern, kind in ((SECRET, "credential"), (PRIVATE_URL, "private_url"), (CLINICAL, "clinical_data")):
            if path.as_posix().endswith("rag/security.py") and kind == "credential":
                continue
            candidates = pattern.findall(meaningful_lines)
            if kind == "private_url":
                candidates = [item for item in candidates if not any(host in item for host in PUBLIC_URLS)]
            if candidates:
                findings.append({"path": path.relative_to(root).as_posix(), "kind": kind})
    return {"safe": not findings, "findings": findings}


def git_summary(root: Path) -> dict:
    def run(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
    status = run("status", "--short")
    return {
        "branch": run("branch", "--show-current"),
        "head": run("log", "-1", "--oneline"),
        "changed_files": [line[3:] if len(line) > 3 else line for line in status.splitlines()],
        "has_uncommitted_changes": bool(status),
        "note": "Resumo somente leitura; não executa commit nem push.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "git-summary"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = audit(args.root.resolve()) if args.command == "audit" else git_summary(args.root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if args.command == "git-summary" or result["safe"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
