"""Technical capabilities; agents support operations instead of phases."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentCapability:
    name: str
    responsibilities: tuple[str, ...]
    operations: tuple[str, ...]


CAPABILITIES = (
    AgentCapability("backend", ("Java", "EJB", "services", "regras"), ("ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE")),
    AgentCapability("database", ("Oracle", "SQL", "entidades", "queries"), ("ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE")),
    AgentCapability("frontend", ("JSF", "PrimeFaces", "paginas", "backing beans"), ("ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE")),
    AgentCapability("qa", ("build", "testes", "regressao", "evidencias"), ("PLAN", "VALIDATE")),
    AgentCapability("architecture", ("impacto", "padroes", "desenho tecnico"), ("ANALYZE", "PLAN", "VALIDATE")),
    AgentCapability("aghuse_assistant", ("skills", "plugins", "contratos", "runtime do assistant", "testes do assistant"), ("MANUTENCAO",)),
)


def select(operation: str, requested: list[str] | None = None) -> tuple[AgentCapability, ...]:
    allowed = operation.upper()
    selected = [item for item in CAPABILITIES if allowed in item.operations]
    if requested:
        selected = [item for item in selected if item.name in requested]
    return tuple(selected)
