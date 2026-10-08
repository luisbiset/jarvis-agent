"""Providers de chat do Workspace com contrato de eventos comum."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator

try:
    from .codex_api import CodexApiError, stream_response
except ImportError:  # execução direta pelo servidor
    from codex_api import CodexApiError, stream_response


def provider_name() -> str:
    value = os.environ.get("CODEX_PROVIDER", "api").strip().lower()
    if value not in {"api", "cli"}:
        raise CodexApiError("PROVIDER_INVALID", "O provider configurado no backend é inválido.", provider=value)
    return value


def _cli_command() -> str | None:
    configured = os.environ.get("CODEX_CLI_PATH")
    if configured:
        return configured
    return shutil.which("codex.cmd") or shutil.which("codex")

CONTAMINATION_MARKERS = ("pré-métricas:", "pre-métricas:", "[aghuse] acionado", "[aghuse] modo rag", "[aghuse] modo fallback", "[aghuse] finalizado", "métricas:", "agents.md orienta", "autorize explicitamente continuar sem rag")

def is_contaminated_response(text: str) -> bool:
    normalized = " ".join(str(text).casefold().split())
    return any(marker in normalized for marker in CONTAMINATION_MARKERS) or bool(re.search(r"\[[a-z0-9_-]+\]\s+acionado", normalized))

def _text_fragments(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        fragments: list[str] = []
        for item in value:
            fragments.extend(_text_fragments(item))
        return fragments
    if isinstance(value, dict):
        fragments: list[str] = []
        for key in ("text", "output_text", "value", "content", "message"):
            if key in value:
                fragments.extend(_text_fragments(value[key]))
        return fragments
    return []


def _cli_event(item: dict[str, Any], resolved: dict[str, Any]) -> dict[str, Any] | None:
    event_type = str(item.get("type", ""))
    if event_type in {"message.delta", "response.output_text.delta"}:
        delta = item.get("delta") or item.get("text")
        return {"event": "message.delta", "delta": str(delta)} if delta else None
    if event_type in {"message.completed", "response.completed", "turn.completed"}:
        return {"event": "provider.completed", "usage": item.get("usage"), **resolved}
    if event_type in {"error", "message.error"}:
        raise CodexApiError("MODEL_ERROR", "O Codex CLI não conseguiu gerar a resposta.", **resolved)
    if event_type == "item.completed":
        completed_item = item.get("item")
        if isinstance(completed_item, dict):
            item_type = str(completed_item.get("type", ""))
            if item_type == "agent_message":
                text = "".join(_text_fragments(completed_item.get("text") or completed_item.get("content") or completed_item.get("output_text")))
                if text:
                    return {"event": "message.delta", "delta": str(text)}
            if item_type == "error":
                # O CLI usa este evento para avisos não fatais, como roles
                # globais incompatíveis. O agent_message posterior é válido.
                return None
    # Alguns formatos do CLI aninham a mensagem textual em item.message.
    message = item.get("message")
    if isinstance(message, dict):
        text = "".join(_text_fragments(message.get("delta") or message.get("text") or message.get("content")))
        if text:
            return {"event": "message.delta", "delta": str(text)}
    return None


def stream_cli_response(
    prompt: str,
    *,
    model: str,
    reasoning: str,
    context_budget: str | None = None,
    cwd: Path | None = None,
    executable: str | None = None,
    runner: Callable[..., Any] = subprocess.Popen,
    timeout: float = 90,
) -> Iterator[dict[str, Any]]:
    command_path = executable or _cli_command()
    if not command_path:
        raise CodexApiError("CLI_UNAVAILABLE", "O Codex CLI não está instalado no backend.")
    if not model:
        raise CodexApiError("MODEL_MISSING", "A policy não retornou um modelo válido.")
    resolved = {"provider": "cli", "model_requested": model, "model_effective": model, "registry_version": "cli-policy"}
    command = [command_path, "exec", "--ephemeral", "--sandbox", "read-only", "--json", "--ignore-user-config", "--ignore-rules"]
    # O CLI não deve descobrir AGENTS.md do repositório e tratar as regras
    # internas do AGHUse Assistant como resposta ao usuário. O contexto seguro já é
    # montado no prompt pelo backend.
    cli_cwd = os.environ.get("CODEX_CLI_WORKDIR") or tempfile.gettempdir()
    command.extend(["--cd", cli_cwd, "--skip-git-repo-check"])
    command.extend(["--model", model, prompt])
    try:
        process = runner(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        if 'process' in locals():
            process.kill()
        raise CodexApiError("MODEL_TIMEOUT", "O Codex CLI excedeu o tempo limite.", **resolved) from exc
    except OSError as exc:
        raise CodexApiError("CLI_UNAVAILABLE", "Não foi possível iniciar o Codex CLI.", **resolved) from exc
    if process.returncode != 0:
        safe_error = str(stderr or "").lower()
        code = "CLI_AUTH_REQUIRED" if any(token in safe_error for token in ("login", "authenticate", "auth")) else "MODEL_ERROR"
        raise CodexApiError(code, "O Codex CLI não conseguiu gerar a resposta.", **resolved)
    events = []
    completed = False
    for line in str(stdout or "").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = _cli_event(item, resolved)
        if event:
            events.append(event)
            completed = completed or event.get("event") == "provider.completed"
    response_text = "".join(str(event.get("delta") or "") for event in events if event.get("event") == "message.delta")
    if not response_text.strip():
        raise CodexApiError("MODEL_ERROR", "O Codex CLI não retornou conteúdo.", **resolved)
    if is_contaminated_response(response_text):
        raise CodexApiError("CLI_CONTAMINATED_RESPONSE", "O Codex retornou uma resposta inválida para esta operação.", **resolved)
    yield {"event": "provider.started", "provider": "cli", **resolved}
    for event in events:
        yield event
    if not completed:
        yield {"event": "provider.completed", "usage": None, **resolved}


def stream_chat_response(prompt: str, *, model: str, reasoning: str,
                         context_budget: str | None = None, cwd: Path | None = None) -> Iterator[dict[str, Any]]:
    selected = provider_name()
    if selected == "cli":
        yield from stream_cli_response(prompt, model=model, reasoning=reasoning,
                                       context_budget=context_budget, cwd=cwd)
    else:
        try:
            for event in stream_response(prompt, model=model, reasoning=reasoning, context_budget=context_budget):
                yield {"provider": "api", **event}
        except CodexApiError as exc:
            metadata = {"provider": "api", **exc.metadata}
            raise CodexApiError(exc.code, str(exc), **metadata) from exc
