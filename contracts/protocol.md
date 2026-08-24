# Protocolo operacional Jarvis V2

Este documento é a fonte única da política de fluxo. Invariantes técnicas possuem IDs em `policy-registry.json` e permanecem repetidas somente onde a defesa em profundidade é necessária.

## Classificação antes do roteamento

| Complexidade | Budget | Paralelismo | Fluxo típico |
|---|---:|---:|---|
| `TRIVIAL` | até 2 agentes | 1 | um especialista; auditor opcional |
| `LOCALIZED` | até 3 agentes | 2 | especialista ou developer; QA ou auditor |
| `TRANSVERSAL` | até 6 agentes | 2 | discovery; developer; QA e auditor |
| `CRITICAL` | até 8 agentes | 2 | fluxo transversal; reviewer; gate reforçado |

Exceder o budget exige justificativa registrada. `risk_class` é independente da complexidade e controla evidência mínima: `LOW` não exige reviewer; `MEDIUM` exige QA ou auditor; `HIGH` exige QA, auditor e reviewer; `CRITICAL` acrescenta explicabilidade e aprovação específica por ação.

`operational_mode` define a autonomia: `COPILOT` investiga e propõe; `ASSISTED_AUTOPILOT` pode editar e validar no repositório autorizado; `READ_ONLY_AUDIT` proíbe writes. A classe de reasoning começa em `FAST` para descoberta determinística, usa `NORMAL` para implementação localizada e sobe a `DEEP` somente por ambiguidade, transversalidade, incidente difícil ou revisão de alto risco.

## Estados e gates

```text
NEW -> DISCOVERY -> PLAN_READY -> PLAN_APPROVED -> IMPLEMENTING
    -> VALIDATING -> REVIEW_READY -> HUMAN_GATE -> HOMOLOGATION_READY -> DONE
```

Falha de validação retorna a `IMPLEMENTING`; pedido de mudança no gate também. Qualquer estágio pode ir a `BLOCKED`. Tarefas triviais ou localizadas cujo pedido já autoriza e delimita a implementação podem ir de `NEW` diretamente a `PLAN_APPROVED`. Nenhum developer começa antes de `PLAN_APPROVED` quando o plano formal é obrigatório.

## Handoff e evidência

Todo handoff segue `handoff.schema.json`. Requisitos conhecidos recebem IDs; cada arquivo aponta para requisito, finalidade e owner. Validações não executadas são registradas, não omitidas. Evidência observada permanece separada da interpretação. Assunções, provenance e `stop_reason` sobrevivem a todos os resumos.

Um arquivo compartilhado possui um único owner por estágio. Contratos são sequenciados produtor -> consumidor. Context packs carregam referências e hashes, não cópias integrais. O cache de descoberta compartilha fatos, nunca conclusões obrigatórias; QA e reviewers mantêm independência de julgamento.

## Fronteiras de validação

- Auditor do diff: escopo, baseline, hunks, arquivos inesperados, EOL/encoding, segredos e scripts indevidos.
- QA técnico: critérios de aceite, testes, build e roteiro técnico; não corrige o código avaliado.
- SESAB Reviewer: segurança sistêmica, arquitetura, contratos, transações e regressão; higiene Git é uma pré-condição resumida.
- QA de homologação: execução em tela autorizada e evidências funcionais; não substitui code review.

## Stop conditions e responsabilidade humana

Parar antes de escrever quando houver requisito funcionalmente ambíguo, contrato compartilhado fora do escopo, teste contraditório, validação não reproduzível, divergência relevante ou contexto insuficiente. Use `NEEDS_EXPLANATION` quando uma solução aparentemente correta não puder ser explicada por causa, ponto da correção, comportamento preservado, evidência e rollback.

Gate anterior nunca autoriza Redmine, banco, deploy, commit ou push. Cada ação externa exige pedido próprio. Produtividade é medida por lead time, retrabalho, regressão, critérios cobertos e custo por tarefa aprovada — não por linhas digitadas manualmente.
