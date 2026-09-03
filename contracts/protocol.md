# Protocolo operacional Jarvis V3

Este documento é a fonte única da política de fluxo. Invariantes técnicas possuem IDs em `policy-registry.json` e permanecem repetidas somente onde a defesa em profundidade é necessária.

## Classificação antes do roteamento

Toda tarefa solicitada, inclusive consulta, explicação, diagnóstico somente leitura ou ação externa, deve ser classificada antes do trabalho substantivo. A classificação não obriga o uso de subagentes: tarefas simples devem permanecer econômicas.

| Complexidade | Budget | Paralelismo | Fluxo típico |
|---|---:|---:|---|
| `TRIVIAL` | até 1 agente | 1 | fast path ou um especialista |
| `LOCALIZED` | até 2 agentes | 1 | especialista ou developer; validação direcionada |
| `TRANSVERSAL` | até 4 agentes | 2 | discovery; especialistas estritamente necessários; fechamento |
| `CRITICAL` | até 6 agentes | 2 | fluxo transversal; reviewer; gate reforçado |

Exceder o budget exige justificativa registrada. `risk_class` é independente da complexidade e controla evidência mínima: `LOW` não exige reviewer; `MEDIUM` exige QA ou auditor; `HIGH` exige QA, auditor e reviewer; `CRITICAL` acrescenta explicabilidade e aprovação específica por ação.

`operational_mode` define a autonomia: `COPILOT` investiga e propõe; `ASSISTED_AUTOPILOT` pode editar e validar no repositório autorizado; `READ_ONLY_AUDIT` proíbe writes. Modelo, reasoning e contexto não são fixados pelos agentes: `contracts/reasoning-policy.json` calcula `INSTANT`, `MEDIUM` ou `HIGH` e seleciona conjuntamente o modelo, o effort e o context budget usados em cada nova chamada.

## Adaptive Reasoning

O policy engine soma pesos determinísticos para arquitetura, criticidade de produção, segurança, migration, quantidade de módulos/arquivos, testes, ambiguidade e complexidade. Scores de 0–3 usam `INSTANT`, 4–8 usam `MEDIUM` e 9 ou mais usam `HIGH`. Pesos, thresholds, budgets e versão pertencem à configuração central, não aos perfis dos agentes.

Somente uma tentativa `MEDIUM` pode escalar automaticamente para `HIGH`, no máximo uma vez, após `TEST_FAILURE` comprovado por teste executado e falho na tentativa finalizada. Os demais gatilhos permanecem desabilitados até possuírem evidência estruturada. `HIGH` nunca escala novamente. Cada cadeia lógica possui no máximo três tentativas; a tarefa possui no máximo três retries globais, três execuções filhas e child depth três. O parent deve existir no mesmo run e primeiras chamadas de agentes distintos não são retries. A escalada produz contexto compacto com referências, sem reiniciar a investigação nem persistir conteúdo sensível.

O reasoning do agente principal já iniciado não muda no meio da mesma chamada. A decisão adaptativa governa novas chamadas de subagentes e retries. `invocation-start` rejeita qualquer `reasoning_effort` divergente do valor retornado pela policy.

## Adaptive Model Routing e controle de custo

A policy determinística usa `gpt-5.6-luna` com `low/SMALL` para tarefas simples, `gpt-5.6-terra` com `medium/MEDIUM` para trabalho normal e `gpt-5.6-sol` com `high/LARGE` para tarefas críticas. O runtime rejeita override divergente, evitando que agents escolham modelos mais caros livremente. Uma escalada autorizada troca reasoning, modelo e contexto em conjunto. Os nomes pertencem à configuração versionada e podem ser recalibrados sem alterar perfis.

Toda tarefa possui budget agregado de chamadas de modelo e duração, além dos limites de agentes, retries, children e profundidade. Os limites padrão de chamadas são 1/3/5/6 para `TRIVIAL`/`LOCALIZED`/`TRANSVERSAL`/`CRITICAL`, sob hard ceiling global. Retry exige `progress_event` verificável (`NEW_TEST_RESULT`, `NEW_RELEVANT_SYMBOL`, `HYPOTHESIS_DISCARDED`, `PLAN_CHANGED` ou `MODEL_ESCALATED`); repetição sem informação ou estratégia nova é recusada. Child agents consomem o mesmo budget global.

Tarefas `TRIVIAL`, `LOW` e `INSTANT`, com no máximo um arquivo e um módulo e sem sinais de arquitetura, produção crítica, banco ou segurança, recebem `FAST_PATH`. Limites de contexto e custo começam em `OBSERVE_ONLY`: produzem telemetria e alertas, mas não podem ser apresentados como bloqueio preventivo enquanto o executor não mediar leituras e inferências.

## Estados e gates

```text
NEW -> DISCOVERY -> PLAN_READY -> PLAN_APPROVED -> IMPLEMENTING
    -> VALIDATING -> REVIEW_READY -> HUMAN_GATE -> HOMOLOGATION_READY -> DONE
```

Falha de validação retorna a `IMPLEMENTING`; pedido de mudança no gate também. Qualquer estágio pode ir a `BLOCKED`. Tarefas triviais ou localizadas cujo pedido já autoriza e delimita a implementação podem ir de `NEW` diretamente a `PLAN_APPROVED`. Nenhum developer começa antes de `PLAN_APPROVED` quando o plano formal é obrigatório.

## Telemetria operacional V3

Aplicar `FLOW-003`: quando `scripts/jarvis_runtime.py` estiver disponível, toda tarefa começa com `init`, sinais objetivos e agentes planejados. Cada chamada real usa um par `invocation-start`/`invocation-finish`; chamadas repetidas permanecem tentativas distintas em `execution_attempts`. O início registra modelo, reasoning inicial/efetivo, policy, parent, depth e tentativa. O fim calcula duração e recebe do executor tokens, créditos, tools, arquivos, testes, findings, sucesso e termination reason.

Findings relevantes são registrados individualmente com severidade e `finding_actioned`. Retornos de validação, review, gate humano, teste ou build para implementação informam origem e categoria do retrabalho. Toda decisão do gate usa `APPROVED`, `CHANGES_REQUESTED` ou `REJECTED`; pedidos de mudança e rejeições exigem reason code padronizado. Ao concluir, registrar o resultado do roteamento e eventuais agentes desnecessários ou ausentes.

O histórico canônico fica em `.jarvis/telemetry/jarvis.db`; `state.json` permanece o snapshot corrente e `events.jsonl` a trilha append-only. Cada tentativa registra `model_requested`, `model_effective`, `context_budget` e `progress_event`, além de reasoning e uso. Persistir apenas metadados permitidos por `SEC-001`. Tokens e créditos dependem dos valores expostos pelo executor e nunca devem ser estimados como se fossem medidos; quando indisponíveis, o fechamento deve dizer `não informados`, ainda que o armazenamento interno use zero como valor neutro.

## Handoff e evidência

Todo handoff segue `handoff.schema.json`. Requisitos conhecidos recebem IDs; cada arquivo aponta para requisito, finalidade e owner. Validações não executadas são registradas, não omitidas. Evidência observada permanece separada da interpretação. Assunções, provenance e `stop_reason` sobrevivem a todos os resumos.

`FLOW-004` adiciona um `TechnicalHandoff` separado ao final de mudanças relevantes. A classificação reutiliza complexidade, risco e `task_type` já calculados pelo runtime. Símbolos não encontrados devem aparecer como `UNKNOWN/NOT_CONFIRMED`; tarefas triviais não disparam geração cara. O Teach-Back reutiliza o artefato, respeita o budget e nunca persiste a resposta livre do desenvolvedor.

Um arquivo compartilhado possui um único owner por estágio. Contratos são sequenciados produtor -> consumidor. Context packs carregam referências e hashes, não cópias integrais. O cache de descoberta compartilha fatos, nunca conclusões obrigatórias; QA e reviewers mantêm independência de julgamento.

## Fronteiras de validação

- Auditor do diff: escopo, baseline, hunks, arquivos inesperados, EOL/encoding, segredos e scripts indevidos.
- QA técnico: critérios de aceite, testes, build e roteiro técnico; não corrige o código avaliado.
- SESAB Reviewer: segurança sistêmica, arquitetura, contratos, transações e regressão; higiene Git é uma pré-condição resumida.
- QA de homologação: execução em tela autorizada e evidências funcionais; não substitui code review.

## Stop conditions e responsabilidade humana

Parar antes de escrever quando houver requisito funcionalmente ambíguo, contrato compartilhado fora do escopo, teste contraditório, validação não reproduzível, divergência relevante ou contexto insuficiente. Use `NEEDS_EXPLANATION` quando uma solução aparentemente correta não puder ser explicada por causa, ponto da correção, comportamento preservado, evidência e rollback.

Gate anterior nunca autoriza Redmine, banco, deploy, commit ou push. Cada ação externa exige pedido próprio. Produtividade é medida por lead time, retrabalho, regressão, critérios cobertos e custo por tarefa aprovada — não por linhas digitadas manualmente.
