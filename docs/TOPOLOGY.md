# Topologia gerada do Jarvis Agent

> Arquivo gerado por `python3 scripts/generate_topology.py`. Não editar manualmente.

Versão comportamental: `3.1.0`.

## Plugins

| Plugin | Versão | Skills |
|---|---|---:|
| aghuse-agent | `0.1.0+codex.20260827080925` | 10 |
| redmine-agent | `0.1.0+codex.20260826141923` | 1 |
| sfa-agent | `0.1.0+codex.20260827081002` | 1 |

## Agentes

| Agente | Reasoning padrão | Sandbox | Responsabilidade |
|---|---|---|---|
| aghuse_analyst | adaptive | read-only | Analista ad-hoc do AGHUse. Use quando o usuário pedir um relatório técnico independente fora do pipeline completo; não acione junto com aghuse_requisitos_e_legado sem justificativa explícita. |
| aghuse_auditor_do_diff | adaptive | read-only | Auditor do diff do AGHUse. Verifica em modo somente leitura baseline, escopo, hunks, arquivos inesperados, EOL/encoding, segredos e higiene da worktree. |
| aghuse_backend | adaptive | workspace-write | Especialista no backend do AGHUse em Java 17, Maven multi-módulo, Java EE 8, EJB, CDI, JAX-RS e WildFly. Use para regras, facades, serviços, APIs, integrações e empacotamento EAR. |
| aghuse_banco_e_impacto | adaptive | read-only | Banco e impacto do AGHUse. Analisa em modo somente leitura persistência, schema, consultas, auditoria, desempenho, segurança e efeitos entre módulos antes do plano. |
| aghuse_database | adaptive | workspace-write | Especialista na persistência Oracle/PostgreSQL do AGHUse. Use para entidades JPA, DAOs, HQL/Criteria/SQL, dialetos, JTA, unidades aghu-pu/aghu-fit-pu, Envers, Search, cache e desempenho. |
| aghuse_desenvolvedor | adaptive | workspace-write | Desenvolvedor do AGHUse. Executa o plano aprovado e integra somente os especialistas técnicos necessários de frontend, backend, banco e testes. |
| aghuse_frontend | adaptive | workspace-write | Especialista no frontend server-side do AGHUse com Java 17, JSF 2.3, Facelets, PrimeFaces 12 e CDI. Use para XHTML, componentes, controllers de apresentação, navegação, CSS e JavaScript dos módulos web. |
| aghuse_qa | adaptive | workspace-write | QA do AGHUse. Valida de forma independente requisitos, testes, build direcionado e roteiro funcional, sem corrigir o código que está avaliando. |
| aghuse_requisitos_e_legado | adaptive | read-only | Discovery formal de requisitos e legado do AGHUse. Use no pipeline profissional antes do plano; não acione junto com aghuse_analyst sem justificativa explícita. |
| aghuse_tests | adaptive | workspace-write | Especialista em testes unitários de ONs e RNs do AGHUse com JUnit 5, Mockito, Maven Surefire, AGHUBaseUnitTest, JaCoCo e Clover. Use para criar, corrigir, isolar e diagnosticar testes e cobertura dessas regras de negócio. |
| qa_homologacao | adaptive | read-only | Especialista de homologação do SFA e AGHUse. Executa em ambiente autorizado roteiros preparados, verifica o fluxo em tela e produz evidências sem revisar ou alterar código. |
| sesab_reviewer | adaptive | read-only | Revisor sistêmico final e somente leitura para SFA e AGHUse. Avalia arquitetura, contratos, transações, segurança e regressão em tarefas de risco alto ou crítico. |
| sfa_backend | adaptive | workspace-write | Especialista no backend do SFA em Java 11 e Spring Boot 2.5.2. Use para controllers, services, VOs, segurança, regras BPA/faturamento, integrações, contratos HTTP e testes Java em sfa/. |
| sfa_database | adaptive | workspace-write | Especialista de banco do SFA para Oracle e PostgreSQL. Use para entidades JPA, repositories, datasources, transações, consultas, desempenho, schema e scripts SQL em sfa/. |
| sfa_frontend | adaptive | workspace-write | Especialista no frontend do SFA em Angular 12, RxJS 6 e TypeScript 4.3. Use para telas, formulários, rotas, Angular Material, models, services HTTP, interceptors, autenticação e testes Karma/Jasmine em sfa-client/. |
| sfa_tests | adaptive | workspace-write | Especialista em testes do SFA. Use para JUnit/Mockito/Spring Test no backend e Jasmine/Karma no Angular, incluindo regressão, fixtures, cobertura e diagnóstico de falhas. |

## Skills

| Plugin | Skill | Roteamento |
|---|---|---|
| aghuse-agent | aghuse-development | Coordenar o ciclo do AGHUse entre análise paralela, plano aprovado, desenvolvimento, validação independente e gate humano. Usar em tarefas de um repositório com aghu/pom.xml e aghu-entidades/pom.xml ou que mencionem AGHUse, EJB, JSF, PrimeFaces, RN, ON, Facade ou módulos clínicos do sistema. |
| aghuse-agent | aghuse-diagnostico-logs | Analisar logs e stack traces do AGHUse para localizar a causa raiz e classificar falhas de banco, segurança, JSF, CDI/EJB, persistência ou deploy. Usar para diagnóstico somente leitura, sem implementar correções automaticamente. |
| aghuse-agent | aghuse-entrega-banco | Preparar ou revisar o pacote de scripts Oracle e PostgreSQL de uma tarefa AGHUse para entrega externa, incluindo aplicação, rollback, comentários, índices, grants, ordem e manifesto. Usar quando os scripts serão enviados ao Redmine; não adicionar scripts de implantação ao repositório AGHUse. |
| aghuse-agent | aghuse-historico-alteracoes | Investigar no histórico Git do AGHUse quando código, mensagens, páginas ou regras existiam e foram alterados, removidos ou restaurados. Usar para comparar tarefa oficial, branches e regressões sem trocar de branch nem modificar arquivos. |
| aghuse-agent | aghuse-idempotent-database-scripts | Criar e revisar scripts de banco do AGHUse para Oracle e PostgreSQL garantindo aplicação e rollback idempotentes. Usar sempre que um script DDL ou DML do AGHUse for criado ou alterado. |
| aghuse-agent | aghuse-mapeamento-seguranca | Diagnosticar permissões, perfis e menus do AGHUse a partir de página negada, log do SecurityPhaseListener ou tarefa de mapeamento. Usar para localizar a alteração e orientar simulação do atualizador; execução real exige autorização explícita. |
| aghuse-agent | aghuse-preparacao-tarefa | Preparar uma tarefa do AGHUse antes da implementação, identificando número, branch, commits, módulos, alterações locais e dependências de banco ou segurança. Usar para iniciar chamados, conferir prontidão ou delimitar o escopo; não usar como substituto da implementação. |
| aghuse-agent | aghuse-roteiro-homologacao | Criar roteiro manual e reproduzível de homologação para tarefas AGHUse, cobrindo pré-condições, permissões, dados fictícios, passos, resultados, regressão e evidências. Usar quando o usuário quiser testar em tela; não executar a interface por padrão. |
| aghuse-agent | aghuse-validacao-direcionada | Selecionar e executar validações proporcionais aos arquivos alterados no AGHUse, mapeando módulos Maven, entidades, XHTML, mensagens e testes ON/RN. Usar para evitar builds e suítes amplas sem perder a cobertura direta da mudança. |
| aghuse-agent | aghuse-verificacao-entrega | Verificar se uma mudança AGHUse está pronta para commit, revisão ou homologação, conferindo tarefa, diff, arquivos inesperados, scripts, mensagens, validações e roteiro. Usar como portão final; não criar commit ou push sem solicitação explícita. |
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
| `AGH-TEST-001` | critical_invariant | O especialista aghuse_tests cria ou altera testes unitários somente de ONs e RNs existentes. |
| `SEC-001` | critical_invariant | Credenciais, URLs privadas e dados clínicos ou de faturamento reais não podem ser persistidos em código, handoffs ou telemetria. |
| `FLOW-001` | flow_policy | Gate humano é obrigatório para aceitação final e não pode ser substituído por agente. |
| `FLOW-002` | flow_policy | Redmine, banco, deploy, commit e push exigem autorização própria; aprovação anterior não é autorização implícita. |
| `FLOW-003` | flow_policy | Toda tarefa usa sinais objetivos e policy V3 para reasoning adaptativo, budgets e telemetria por tentativa, com resumo métrico no fechamento. |
| `FLOW-004` | flow_policy | Mudanças relevantes geram transferência de conhecimento proporcional, baseada em evidências e recuperável por tarefa. |
