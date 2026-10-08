"""Cliente mínimo e testável para respostas da API usada pelo Codex."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterator, Callable, Any

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "config" / "model-registry.json"


class CodexApiError(RuntimeError):
    def __init__(self, code: str, message: str = "Falha na API do modelo", **metadata: Any) -> None:
        super().__init__(message)
        self.code = code
        self.metadata = metadata


def load_model_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CodexApiError("MODEL_REGISTRY_INVALID", "O registry de modelos não está disponível.") from exc
    if registry.get("provider") != "openai-responses" or not isinstance(registry.get("models"), dict):
        raise CodexApiError("MODEL_REGISTRY_INVALID", "O registry de modelos é inválido.")
    return registry


def resolve_model(model_requested: str, reasoning: str, context_budget: str | None, registry_path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    registry = load_model_registry(registry_path)
    entry = registry["models"].get(model_requested)
    if not isinstance(entry, dict):
        raise CodexApiError("MODEL_NOT_FOUND", f"O modelo selecionado pela policy não está no registry: {model_requested}", model_requested=model_requested, registry_version=registry.get("schema_version"))
    if reasoning not in entry.get("reasoning", []) or (context_budget is not None and context_budget != "AUTO" and context_budget != entry.get("context_budget")):
        raise CodexApiError("MODEL_INVALID", f"O modelo da policy é incompatível com o reasoning/contexto solicitado: {model_requested}", model_requested=model_requested, registry_version=registry.get("schema_version"))
    effective = entry.get("provider_model")
    if not isinstance(effective, str) or not effective:
        raise CodexApiError("MODEL_INVALID", f"O modelo não possui identificador de provider: {model_requested}", model_requested=model_requested, registry_version=registry.get("schema_version"))
    return {"model_requested": model_requested, "model_effective": effective, "registry_version": registry.get("schema_version")}


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs without overwriting process configuration."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def stream_response(
    prompt: str,
    *,
    model: str,
    reasoning: str,
    context_budget: str | None = None,
    registry_path: Path = DEFAULT_REGISTRY,
    api_key: str | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
    timeout: float = 90,
) -> Iterator[dict[str, Any]]:
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise CodexApiError("API_KEY_MISSING", "A credencial da API não está configurada no backend.")
    if not model:
        raise CodexApiError("MODEL_MISSING", "A policy não retornou um modelo válido.")
    resolved = resolve_model(model, reasoning, context_budget, registry_path)
    body = {
        "model": resolved["model_effective"],
        "input": prompt,
        "stream": True,
        "store": False,
        "max_output_tokens": int(os.environ.get("CODEX_MAX_OUTPUT_TOKENS", "1200")),
        "reasoning": {"effort": reasoning} if reasoning in {"low", "medium", "high"} else {"effort": "medium"},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    try:
        yield {"event": "provider.started", **resolved}
        with opener(request, timeout=timeout) as response:
            for raw in response:
                line = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                if event_type == "response.output_text.delta" and event.get("delta"):
                    yield {"event": "message.delta", "delta": event["delta"]}
                elif event_type in {"response.completed", "response.incomplete"}:
                    response_data = event.get("response", event)
                    yield {"event": "provider.completed", "usage": response_data.get("usage")}
                elif event_type == "error":
                    raise CodexApiError("MODEL_ERROR", "A API não conseguiu gerar a resposta.", **resolved)
    except urllib.error.HTTPError as exc:
        try:
            details = json.loads(exc.read().decode("utf-8", errors="replace"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            details = {}
        api_code = str(details.get("error", {}).get("code", ""))
        api_type = str(details.get("error", {}).get("type", ""))
        model_error = api_code in {"model_not_found", "model_not_allowed"} or api_type in {"invalid_request_error", "model_not_found"} and "model" in api_code
        code = "AUTHENTICATION_FAILED" if exc.code in {401, 403} else "RATE_LIMITED" if exc.code == 429 else "MODEL_UNAVAILABLE" if exc.code >= 500 else "MODEL_NOT_FOUND" if exc.code == 404 or model_error else "MODEL_INVALID"
        message = "O modelo selecionado pela policy não está disponível no provider." if code == "MODEL_NOT_FOUND" else "A API rejeitou a solicitação."
        raise CodexApiError(code, message, **resolved) from exc
    except TimeoutError as exc:
        raise CodexApiError("MODEL_TIMEOUT", "A API excedeu o tempo limite.") from exc
    except urllib.error.URLError as exc:
        raise CodexApiError("MODEL_UNAVAILABLE", "A API do modelo está indisponível.") from exc
