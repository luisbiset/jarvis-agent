# Itens não implementados da Dashboard do Jarvis

Data: 2026-10-05

## Objetivo

Registrar as capacidades previstas para a dashboard que ainda não estão implementadas ou estão apenas parcialmente disponíveis.

## Resumo executivo

A dashboard já possui um Control Center básico, consulta de execuções, criação de tarefas, visão de atenção, agentes, uso de modelos e evidências. Permanecem pendentes principalmente integrações reais, ações operacionais seguras, busca global, configurações editáveis e telas detalhadas.

## Itens pendentes

| Prioridade | Item | Situação atual | O que falta |
|---|---|---|---|
| Alta | Integrações/MCP externos | Implementado para Redmine | Adaptador MCP Redmine com ping, capabilities somente leitura, timeout, auditoria e bloqueio de escrita; outros MCPs continuam pendentes. |
| Alta | Configurações editáveis | Implementado | Draft, validação básica, aplicação confirmada, auditoria e rollback em overlay local. |
| Alta | Ações operacionais | Implementado | Pause, resume, approve e retry delegados ao Runtime com confirmação e idempotência. |
| Alta | Busca global | Implementado | Busca segura em execuções e sessões de chat. |
| Alta | Command Palette | Implementado | Registro de comandos e confirmação para ações mutáveis. |
| Média | Detalhe completo da tarefa | Parcial | APIs, checkpoint, eventos e diff existem; a tela ainda pode receber mais drill-down visual. |
| Média | Interface dedicada de agentes | Implementado | Histórico, tarefas, findings e consumo por agent em `/api/agents/<agent>`. |
| Média | Logs avançados | Implementado | Eventos correlacionados, SSE, filtros básicos e fallback por polling. |
| Média | Modelos e métricas avançados | Parcial | Filtros por modelo/reasoning/período existem; gráficos visuais ainda faltam. |
| Média | Evidence Explorer completo | Implementado | Grafo seguro de agents produtores, findings e referências. |
| Média | Temas e navegação completa | Parcial | Tema responsivo existe; revisão formal de acessibilidade e navegação ainda falta. |
| Alta | Prompts e saídas completas | Não previsto por segurança | Exibir somente resumo seguro, hashes, referências e evidências; não persistir conteúdo sensível. |

## Dependências e ordem recomendada

1. Concluído: contratos, autorização, auditoria, ações, busca, comandos, checkpoints, logs, agents e evidências.
2. Concluído: configurações revisionadas com aprovação e rollback local.
3. Concluído para Redmine: adaptador MCP local integrado à Dashboard.
4. Próximo: adicionar gráficos e filtros visuais avançados.
5. Próximo: concluir acessibilidade e testes de navegador.

## Riscos

- Ações operacionais sem autorização podem causar execução indevida.
- Configurações editáveis podem alterar budget, policy ou segurança sem rastreabilidade.
- Integrações reais exigem credenciais, escopos mínimos e tratamento de falhas.
- Logs, prompts e resultados completos não devem ser persistidos sem sanitização.

## Critério de conclusão

Considerar a dashboard completa somente quando as ações estiverem ligadas ao Runtime real, as integrações forem auditáveis, os contratos forem validados, os dados forem seguros e houver testes de integração para os fluxos principais.
