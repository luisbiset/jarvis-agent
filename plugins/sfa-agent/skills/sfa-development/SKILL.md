---
name: sfa-development
description: Coordenar análise, implementação, testes e revisão no Sistema de Faturamento AGHUse (SFA) por meio dos subagentes sfa_frontend, sfa_backend, sfa_database e sfa_tests. Usar em tarefas que mencionem SFA, faturamento AGHUse, BPA, CNES, CBO, SIGTAP, glosas ou um repositório que contenha sfa/pom.xml e sfa-client/angular.json.
---

# Coordenação do desenvolvimento do SFA

## Identificar o projeto

- Confirmar que o repositório contém `sfa/pom.xml` e `sfa-client/angular.json` antes de aplicar estas regras.
- Localizar a raiz do Git quando a sessão começar em um subdiretório.
- Não aplicar convenções do SFA a outro sistema apenas porque ele também usa Java ou Angular.

## Missão

Antes de delegar, classificar a tarefa com o protocolo Jarvis V2: `TRIVIAL` usa um especialista e Auditor opcional (até dois agentes); `LOCALIZED` usa até três; `TRANSVERSAL` usa até seis; `CRITICAL` usa até oito e exige reviewer. Declarar também risco, modo operacional, classe FAST/NORMAL/DEEP, budget e ownership de arquivos. Exceder o budget exige justificativa no handoff.

Atuar como coordenador do Sistema de Faturamento AGHUse. Entregar mudanças pequenas, rastreáveis e compatíveis com a base legada, delegando o trabalho aos três perfis do projeto em `.codex/agents/`:

- `sfa_frontend`: Angular, componentes, formulários, models, services HTTP e testes do `sfa-client/`.
- `sfa_backend`: controllers, services, VOs, segurança, integrações, regras BPA/faturamento e testes Java.
- `sfa_database`: entidades, repositories, datasources, transações, consultas e scripts Oracle/PostgreSQL.

- `sfa_tests`: testes JUnit/Mockito/Spring Test e Jasmine/Karma, regressão, fixtures e cobertura.

O agente principal é o coordenador; os quatro perfis acima são os especialistas. Antes de editar, localizar o fluxo completo afetado e confirmar os contratos entre frontend, API, regras de faturamento e persistência.

Responder em português, salvo solicitação em contrário. Explicar impactos funcionais com os termos do domínio presentes no código, como BPA, competência, CNES, CBO, SIGTAP, auditoria, tratamento e glosa.

## Mapear o repositório

- Tratar `sfa/` como backend Java 11, Spring Boot 2.5.2, Spring MVC, Security, JPA e WAR.
- Localizar controllers, services, repositories, models, VOs, configuração e segurança em `sfa/src/main/java/br/gov/ba/saude/sfa/`.
- Tratar `sfa/src/main/resources/` como configuração da aplicação e referências SIGTAP.
- Tratar `sfa/scripts/` como scripts de Oracle/PostgreSQL que exigem revisão cuidadosa antes de execução.
- Tratar `sfa-client/` como frontend Angular 12, Angular Material, RxJS 6 e TypeScript 4.3.
- Localizar telas em `_components`, integração HTTP em `_services` e contratos em `_models`.
- Tratar `sfa/src/main/webapp/` como destino de artefatos estáticos do WAR. Não editar saídas geradas manualmente.
- Consultar `DEPARA CODIGOS LOCALIDADE DATASUS-AGHUSE.pdf` somente em tarefas relacionadas ao de/para de localidades.

## Trabalhar com segurança

1. Ler o estado do Git e preservar mudanças existentes. Nunca reverter trabalho do usuário.
2. Rastrear a funcionalidade de ponta a ponta antes de mudar contratos: rota/componente Angular -> service/model Angular -> controller -> service -> repository/model/VO.
3. Reutilizar padrões do módulo adjacente. Não introduzir nova arquitetura nem atualizar frameworks em uma correção comum.
4. Preferir a menor alteração que resolva a causa. Evitar reformatação e refatoração sem relação com a tarefa.
5. Para correções, acrescentar ou ajustar um teste que reproduza o defeito quando viável.
6. Validar primeiro o escopo alterado e depois executar a verificação mais ampla permitida pelo ambiente.

## Delegar aos subagentes

1. Para uma tarefa restrita a um domínio, delegar ao especialista correspondente.
2. Para uma tarefa transversal, delegar primeiro a análise aos especialistas relevantes. Podem analisar em paralelo quando as frentes forem independentes.
3. Durante implementação paralela, atribuir arquivos sem sobreposição. Não permitir que dois agentes editem o mesmo contrato, entidade, repository ou arquivo de configuração.
4. Tratar o contrato como handoff explícito: frontend descreve necessidade de API; backend define request/response e regras; banco define persistência e fronteiras transacionais.
5. Se o contrato ainda estiver ambíguo, sequenciar a implementação: banco -> backend -> frontend, ajustando a ordem quando a tarefa justificar.
6. Ao receber os resultados, revisar o diff integrado, resolver divergências e executar as validações proporcionais ao risco.

Os handoffs devem seguir `contracts/handoff.schema.json`, relacionar arquivo a requisito e owner, separar evidência observada de interpretação e declarar validações não executadas. Redmine, banco, deploy, commit e push continuam fora de qualquer autorização implícita (`FLOW-002`).

Acionar `sfa_tests` quando houver comportamento novo ou corrigido, risco de regressão, falha de suíte ou necessidade de cobertura. O especialista de implementação continua responsável por código testável; o agente de testes possui os arquivos de teste para evitar sobreposição.

Não delegar trabalho irrelevante apenas para ocupar os três perfis. Em diagnóstico somente leitura, solicitar que cada especialista devolva evidências e recomendações sem editar. Em correções, deixar claro quais diretórios cada agente pode alterar.

## Proteger dados e infraestrutura

- Tratar dados de pacientes, profissionais e faturamento como sensíveis. Não expor em respostas, logs, fixtures, commits ou mensagens de erro.
- Nunca mostrar, copiar ou gravar credenciais, tokens, senhas, endereços internos ou strings de conexão reais. Redigir valores sensíveis em diagnósticos.
- Preservar `sfa/src/main/resources/application.properties` quando houver configuração local. Não alterar sem necessidade explícita nem substituir mudanças existentes.
- Não conectar a Oracle, PostgreSQL, LDAP ou serviços reais sem autorização explícita.
- Usar somente dados fictícios, mínimos e anonimizados nos testes.
- Não registrar conteúdo integral de arquivos BPA nem identificadores pessoais.

## Contrato do backend

- Preservar compatibilidade com Java 11 e Spring Boot 2.5.2. Não usar APIs ou sintaxe mais novas.
- Preferir injeção por construtor e manter controllers focados em HTTP, regras em services e acesso a dados em repositories.
- Preservar contratos JSON. Quando uma mudança for necessária, atualizar VOs Java, models/services Angular e testes na mesma entrega.
- Tratar Oracle como datasource principal. Manter modelos gerais em `br.gov.ba.saude.sfa.model`, com `entityManagerFactory` e `transactionManager` padrão.
- Tratar PostgreSQL como datasource secundário. Manter modelos em `br.gov.ba.saude.sfa.model.postgres` e usar `postgresEntityManagerFactory` e `postgresTransactionManager` explicitamente.
- Não misturar entidades ou transações Oracle/PostgreSQL por conveniência.
- Preservar `hibernate.hbm2ddl.auto=none`; o schema é administrado externamente.
- Preservar posições fixas, competência, zeros à esquerda, finais de linha e charset dos arquivos BPA. Manter `ISO_8859_1` quando o fluxo existente o exigir.
- Tratar valores monetários com `BigDecimal`, nunca `double` ou `float`.
- Evitar N+1, carregamento irrestrito e concatenação de entrada em SQL. Parametrizar consultas.
- Não executar DDL ou DML em ambiente compartilhado.

## Contrato do frontend

- Preservar compatibilidade com Angular 12, RxJS 6 e TypeScript 4.3.
- Seguir estrutura e estilo dos componentes e services adjacentes. Não migrar para standalone components, signals ou APIs de Angular moderno.
- Manter HTTP em `_services`, contratos em `_models` e regras de apresentação nos componentes.
- Usar `environment.apiUrl`; não gravar URLs de ambiente diretamente no código.
- Cobrir estados de carregamento, vazio, sucesso e erro em formulários e fluxos assíncronos. Evitar submissão duplicada.
- Preservar rótulos, navegação por teclado, foco e mensagens de erro compreensíveis.
- Não editar `dist/`, `node_modules/` ou arquivos copiados para `sfa/src/main/webapp/static/`.

## Validar

Executar conforme o escopo e a partir da raiz do repositório:

```bash
cd sfa
bash ./mvnw test
bash ./mvnw package

cd ../sfa-client
npm test -- --watch=false --browsers=ChromeHeadless
npm run build -- --configuration development
```

- Executar `npm ci` somente quando as dependências precisarem ser instaladas ou restauradas pelo lockfile.
- Não apontar testes para infraestrutura real para contornar falhas de contexto. Preferir testes unitários com dependências simuladas e registrar a limitação.
- Para regras BPA e faturamento, validar também formato, competência, quantidade, valor, arredondamento e casos-limite.

## Revisar

- Sinalizar vazamento de credencial, dado pessoal, arquivo BPA ou informação de infraestrutura.
- Sinalizar alterações de posição de campo, charset, arredondamento, competência ou zeros à esquerda sem evidência funcional e testes.
- Sinalizar repositories PostgreSQL sem unidade de persistência ou transaction manager secundário.
- Sinalizar contratos divergentes entre DTO/VO Java e models/consumidores Angular.
- Sinalizar mudanças de autenticação, autorização ou CORS que ampliem acesso sem requisito explícito.
- Sinalizar artefatos gerados, segredos, dumps, uploads ou arquivos de ambiente adicionados ao Git.

## Concluir

Consolidar o handoff com: resultado, evidências, arquivos alterados, contrato afetado, validações executadas, riscos, limitações e próxima responsabilidade. Informar qualquer validação impedida por banco, LDAP, navegador ou ambiente.
