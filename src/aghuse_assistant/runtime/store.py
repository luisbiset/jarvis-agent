"""Small in-memory Run store; persistence adapters can be added later."""
from __future__ import annotations

from .run import OperationRun


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, OperationRun] = {}

    def save(self, run: OperationRun) -> OperationRun:
        self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> OperationRun | None:
        return self._runs.get(run_id)

    def list(self) -> list[OperationRun]:
        return list(self._runs.values())
