# Itens não implementados da Dashboard do Jarvis

Data: 2026-10-05

## Objetivo

Registrar as capacidades previstas para a dashboard que ainda não estão implementadas ou estão apenas parcialmente disponíveis.

## Resumo executivo

A dashboard já possui um Control Center básico, consulta de execuções, criação de tarefas, visão de atenção, agentes, uso de modelos e evidências. Permanecem pendentes principalmente integrações reais, ações operacionais seguras, busca global, configurações editáveis e telas detalhadas.

## Itens pendentes

| Prioridade | Item | Situação atual | O que falta |
|---|---|---|---|
| Alta | Integrações/MCP reais | Não implementado | Health check, capabilities, chamadas, autorização e auditoria persistida. |
| Alta | Configurações editáveis | Não implementado | API segura para alterar policy, RAG, modelos, limites, agentes e integrações, com validação, aprovação, auditoria e rollback. |
| Alta | Ações operacionais | Parcial | Criar tarefa funciona; pause, approve e retry ainda não estão conectados ao Runtime. |
| Alta | Busca global | Não implementado | Índice único para tarefas, evidências, erros e integrações. |
| Alta | Command Palette | Não implementado | Registro de comandos, busca global e execução com confirmação. |
| Média | Detalhe completo da tarefa | Parcial | Drill-down por estágio, passos, estado, evidências e ações seguras. |
| Média | Interface dedicada de agentes | Parcial | Histórico, saúde, tarefas, consumo e ações por agente. |
| Média | Logs avançados | Parcial | Streaming, filtros combináveis, correlação visual, pausa/retomada e exportação. |
| Média | Modelos e métricas avançados | Parcial | Filtros por período/projeto/agente, gráficos e drill-down por modelo. |
| Média | Evidence Explorer completo | Parcial | Grafo produtor/consumidor/arquivo e proveniência mais rica. |
| Média | Temas e navegação completa | Parcial | Tema claro/escuro consistente, navegação responsiva e estados de loading/erro. |
| Alta | Prompts e saídas completas | Não previsto por segurança | Exibir somente resumo seguro, hashes, referências e evidências; não persistir conteúdo sensível. |

## Dependências e ordem recomendada

1. Definir contratos de ação, autorização e auditoria.
2. Implementar busca global e registro de comandos.
3. Conectar pause, approve e retry ao Runtime, sem simulação.
4. Completar detalhe de tarefa, logs, agentes e evidências.
5. Integrar MCPs reais com health checks e controle de acesso.
6. Evoluir métricas, filtros, gráficos e temas.

## Riscos

- Ações operacionais sem autorização podem causar execução indevida.
- Configurações editáveis podem alterar budget, policy ou segurança sem rastreabilidade.
- Integrações reais exigem credenciais, escopos mínimos e tratamento de falhas.
- Logs, prompts e resultados completos não devem ser persistidos sem sanitização.

## Critério de conclusão

Considerar a dashboard completa somente quando as ações estiverem ligadas ao Runtime real, as integrações forem auditáveis, os contratos forem validados, os dados forem seguros e houver testes de integração para os fluxos principais.
