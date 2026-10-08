"""Single provider boundary for structured operation responses."""
from __future__ import annotations
import os
from typing import Callable
from .responses import ResponseContractError, parse_response

class StructuredProvider:
    def __init__(self, generate: Callable[[str], str] | None = None): self.generate = generate or self._default
    def _default(self, prompt: str) -> str:
        import sys
        sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3] / 'scripts'))
        from chat_providers import stream_chat_response
        chunks = stream_chat_response(prompt, model=os.getenv("AGHUSE_MODEL", "gpt-5.6-terra"), reasoning=os.getenv("AGHUSE_REASONING", "medium"))
        return "".join(str(event.get("delta", "")) for event in chunks if event.get("event") == "message.delta")
    def execute(self, run, schema: dict) -> dict:
        prompt = f"Return only JSON matching this schema for operation {run.operation}: {schema}. Project: {run.project}. Objective: {run.objective}"
        last_error = None
        for attempts in (1, 2):
            try: return parse_response(self.generate(prompt if attempts == 1 else prompt + f" Previous contract error: {last_error}. Return corrected JSON only."), run.operation, run.run_id, run.project, attempts)
            except ResponseContractError as exc: last_error = str(exc)
        raise ResponseContractError(f"structured response rejected after 2 attempts: {last_error}")
