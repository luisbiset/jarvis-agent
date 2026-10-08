"""Pré-processador local de prompts do AGHUse Assistant.

Transforma mensagens curtas em uma instrução estruturada para o roteamento.
Não chama modelos, não faz rede e não persiste o texto recebido.
"""
from __future__ import annotations

import re


def improve_prompt(message: str) -> dict[str, str | bool]:
    original = message.strip()
    if not original:
        return {"message": "", "enhanced": "", "changed": False}

    # Mantém a intenção original intacta e apenas adiciona contratos úteis ao
    # roteador. O texto é deliberadamente genérico para não inventar requisitos.
    enhanced = (
        "Objetivo principal:\n"
        f"{original}\n\n"
        "Instruções de execução:\n"
        "- Identifique o contexto e as dependências relevantes antes de agir.\n"
        "- Preserve alterações existentes e não invente requisitos ausentes.\n"
        "- Declare suposições e dúvidas bloqueantes.\n"
        "- Entregue o resultado solicitado com evidências e validações proporcionais.\n"
        "- Não execute ações externas, commit, push, deploy ou alterações irreversíveis sem autorização explícita."
    )
    return {"message": original, "enhanced": enhanced, "changed": enhanced != original}


def prompt_for_routing(message: str) -> str:
    return str(improve_prompt(message)["enhanced"])
