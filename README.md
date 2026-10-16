# AGHUse Assistant

Arquitetura canônica para análise, planejamento, implementação e validação de projetos AGHUse.

## Estrutura

```text
src/aghuse_assistant/
├── analysis/     interpretação, plano, evidências, cobertura e impacto
├── planning/     plano técnico a partir de análise completa
├── implementation/ execução autorizada e rollback
├── validation/   checks independentes e regressões
├── maintenance/  manutenção isolada do próprio Assistant
├── agents/       seleção por competência
├── mcp/          registro passivo de ferramentas
├── operations/   ANALYZE, PLAN, IMPLEMENT e VALIDATE
├── policy/       permissões por operação
├── orchestrator/ estado, policy, contexto e execução
├── teams/        Análise, Planejamento, Dev, QA e Manutenção
└── gateway/      Git, Oracle, Redmine e Build/Test

config/agents/    perfis backend, database, frontend, qa e architecture
config/contracts/ contratos e políticas
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

O Codex é o agente principal. O orchestrator é determinístico e controla contexto, permissões, checkpoints e execução. A implementação é a única operação autorizada a alterar arquivos.
