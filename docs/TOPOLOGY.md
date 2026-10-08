# Topologia gerada do AGHUse Assistant

> Arquivo gerado por `python3 scripts/generate_topology.py`. Não editar manualmente.

Versão comportamental: `3.1.0`.

## Plugins

| Plugin | Versão | Skills |
|---|---|---:|
| aghuse-assistant | `0.1.0` | 4 |
| redmine-agent | `0.1.0+codex.20261006013631` | 1 |
| sfa-agent | `0.1.0+codex.20261006013631` | 1 |

## Times de agentes

| Time | Agente | Papel | Reasoning padrão | Sandbox | Responsabilidade |
|---|---|---|---|---|---|
| Time de Revisão e Qualidade | architecture | DIFF_AUDITOR | adaptive | read-only | Auditor do diff do AGHUse em modo somente leitura. |
| Time de Desenvolvimento | backend | BACKEND | adaptive | workspace-write | Especialista no backend do AGHUse em Java 17, Maven multi-módulo, Java EE 8, EJB, CDI, JAX-RS e WildFly. Use para regras, facades, serviços, APIs, integrações e empacotamento EAR. |
| Time de Desenvolvimento | database | DATABASE | adaptive | workspace-write | Especialista na persistência Oracle/PostgreSQL do AGHUse. Use para entidades JPA, DAOs, HQL/Criteria/SQL, dialetos, JTA, unidades aghu-pu/aghu-fit-pu, Envers, Search, cache e desempenho. |
| Time de Desenvolvimento | frontend | FRONTEND | adaptive | workspace-write | Especialista no frontend server-side do AGHUse com Java 17, JSF 2.3, Facelets, PrimeFaces 12 e CDI. Use para XHTML, componentes, controllers de apresentação, navegação, CSS e JavaScript dos módulos web. |
| Time de Desenvolvimento | qa | TEST_DEVELOPMENT | adaptive | workspace-write | Especialista em testes unitários de ONs e RNs do AGHUse com JUnit 5, Mockito, Maven Surefire, AGHUBaseUnitTest, JaCoCo e Clover. Use para criar, corrigir, isolar e diagnosticar testes e cobertura dessas regras de negócio. |
| Time de Análise, Time de Desenvolvimento | sfa_backend | BACKEND | adaptive | workspace-write | Especialista no backend do SFA em Java 11 e Spring Boot 2.5.2. Use para controllers, services, VOs, segurança, regras BPA/faturamento, integrações, contratos HTTP e testes Java em sfa/. |
| Time de Análise, Time de Desenvolvimento | sfa_database | DATABASE | adaptive | workspace-write | Especialista de banco do SFA para Oracle e PostgreSQL. Use para entidades JPA, repositories, datasources, transações, consultas, desempenho, schema e scripts SQL em sfa/. |
| Time de Análise, Time de Desenvolvimento | sfa_frontend | FRONTEND | adaptive | workspace-write | Especialista no frontend do SFA em Angular 12, RxJS 6 e TypeScript 4.3. Use para telas, formulários, rotas, Angular Material, models, services HTTP, interceptors, autenticação e testes Karma/Jasmine em sfa-client/. |
| Time de Desenvolvimento, Time de Revisão e Qualidade | sfa_tests | TESTS | adaptive | workspace-write | Especialista em testes do SFA. Use para JUnit/Mockito/Spring Test no backend e Jasmine/Karma no Angular, incluindo regressão, fixtures, cobertura e diagnóstico de falhas. |

## Skills

| Plugin | Skill | Roteamento |
|---|---|---|
| aghuse-assistant | analisar | Executa uma análise independente do AGHUse Assistant sobre projeto, tarefa ou escopo, em modo somente leitura. |
| aghuse-assistant | implementar | Executa uma implementação controlada pelo AGHUse Assistant, com aprovação e checkpoint. |
| aghuse-assistant | planejar | Cria um plano técnico independente pelo AGHUse Assistant, sem alterar arquivos. |
| aghuse-assistant | validar | Executa uma validação independente pelo AGHUse Assistant, sem corrigir automaticamente. |
| redmine-agent | redmine-workflows | Consultar e gerenciar projetos, chamados, comentários, status, responsáveis e horas no Redmine da SESAB. Usar quando o usuário pedir para localizar, resumir, criar ou atualizar chamados do Redmine, acompanhar suas pendências, registrar trabalho ou preparar triagens e relatórios a partir dos tickets. |
| sfa-agent | sfa-development | Coordenar análise, implementação, testes e revisão no Sistema de Faturamento AGHUse (SFA) por meio dos subagentes sfa_frontend, sfa_backend, sfa_database e sfa_tests. Usar em tarefas que mencionem SFA, faturamento AGHUse, BPA, CNES, CBO, SIGTAP, glosas ou um repositório que contenha sfa/pom.xml e sfa-client/angular.json. |

## Políticas

| ID | Categoria | Resumo |
|---|---|---|
| `AGH-RN-001` | critical_invariant | No AGHUse, reutilizar RN coesa existente ou criar ON; nunca criar nova classe RN. |
| `AGH-DB-001` | critical_invariant | Scripts de implantação AGHUse são entregues externamente e não entram no Git do sistema. |
| `AGH-DB-002` | critical_invariant | Aplicação e rollback de banco AGHUse devem ser idempotentes. |
| `AGH-DB-003` | critical_invariant | Novas consultas Criteria do AGHUse usam JPA CriteriaBuilder, não a API Criteria legada do Hibernate. |
| `DB-DDL-001` | critical_invariant | No Oracle, novas FKs e unique constraints sobre tabelas populadas usam ENABLE NOVALIDATE, toda FK possui índice associado e todo CREATE INDEX termina com ONLINE. |
| `AGH-TEST-001` | critical_invariant | O especialista qa cria ou altera testes unitários somente de ONs e RNs existentes. |
| `SEC-001` | critical_invariant | Credenciais, URLs privadas e dados clínicos ou de faturamento reais não podem ser persistidos em código, handoffs ou telemetria. |
| `FLOW-001` | flow_policy | Gate humano é obrigatório para aceitação final e não pode ser substituído por agente. |
| `FLOW-002` | flow_policy | Redmine, banco, deploy, commit e push exigem autorização própria; aprovação anterior não é autorização implícita. |
| `FLOW-003` | flow_policy | Toda tarefa usa sinais objetivos e policy V3 para reasoning adaptativo, budgets e telemetria por tentativa, com resumo métrico no fechamento. |
| `FLOW-004` | flow_policy | Mudanças relevantes geram transferência de conhecimento proporcional, baseada em evidências e recuperável por tarefa. |
| `FLOW-005` | flow_policy | O runtime seleciona times lógicos antes do menor conjunto de agentes, preservando escrita e revisão independente. |
| `RAG-001` | knowledge_policy | Retrieval local usa provenance, respeita o context budget, recusa conteúdo sensível antes da indexação e exige confirmação na fonte para decisões críticas. |
