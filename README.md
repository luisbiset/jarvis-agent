# AGHUse Assistant

Arquitetura canônica para análise, planejamento, implementação e validação de projetos AGHUse.

## Estrutura

```text
src/aghuse_assistant/
├── api/          API de operações e runs
├── agents/       seleção por competência
├── mcp/          registro passivo de ferramentas
├── operations/   ANALYZE, PLAN, IMPLEMENT e VALIDATE
├── policy/       permissões por operação
├── rag/          recuperação opcional
└── runtime/      Run, Context, Dispatcher e Store

config/agents/    perfis backend, database, frontend, qa e architecture
config/contracts/ contratos e políticas
frontend/         dashboard
plugins/          plugin canônico e integrações externas
tests/            testes e fixtures
```

## Execução

```bash
python -m aghuse_assistant.app /analisar "objetivo"
python -m aghuse_assistant.app /planejar "objetivo"
python -m aghuse_assistant.app /implementar "objetivo" --confirm
python -m aghuse_assistant.app /validar "objetivo"
python scripts/validate.py
```

O RAG é opcional e fica em `.aghuse-assistant/rag/`. A implementação é a única operação autorizada a alterar arquivos.
