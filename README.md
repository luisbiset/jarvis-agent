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
├── operations/   ANALYZE, PLAN, IMPLEMENT, VALIDATE e MANUTENCAO
├── policy/       permissões por operação
├── orchestrator/ estado, policy, contexto e execução
├── teams/        Análise, Planejamento, Dev, QA e Manutenção
└── gateway/      fronteira única para ferramentas registradas

config/agents/    perfis backend, database, frontend, qa e architecture
config/contracts/ contratos e políticas
plugins/          plugin canônico e integrações externas
tests/            testes e fixtures
```

## Execução

```bash
aghuse-assistant /analisar "objetivo"
aghuse-assistant /analisar "objetivo" --plan
aghuse-assistant /planejar "objetivo"
aghuse-assistant /implementar "objetivo" --confirm
aghuse-assistant /validar "objetivo"
python scripts/validate.py
```

O pacote expõe somente o comando `aghuse-assistant`; não há API HTTP nem entry point de servidor. O Codex é o agente principal. O orchestrator é determinístico e controla contexto, permissões, checkpoints e execução.

Use `--plan` com `/analisar` para encadear o planejamento na mesma execução. O artefato de análise permanece apenas em memória; o planejamento só é criado quando a análise está `COMPLETE`. A busca local é somente leitura, limitada ao workspace, e retorna evidências com caminho, linha, classificação, trecho e termos correspondentes.

`/implementar` exige um plano aprovado, confirmação explícita e ferramenta mutável de escopo `workspace` com rollback. `/validar` não corrige arquivos. `/manutencao` é assistant-only e requer `--project-id aghuse-assistant` e confirmação explícita.
