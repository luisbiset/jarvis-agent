---
name: aghuse-development
description: Coordenar análise, implementação, testes e revisão no AGHUse por meio dos subagentes aghuse_analyst, aghuse_frontend, aghuse_backend, aghuse_database e aghuse_tests. Usar em tarefas de um repositório com aghu/pom.xml e aghu-entidades/pom.xml ou que mencionem AGHUse, EJB, JSF, PrimeFaces, RN, ON, Facade ou módulos clínicos do sistema.
---

# Coordenação do AGHUse

## Identificar o projeto

- Localizar a raiz que contém `aghu/pom.xml` e `aghu-entidades/pom.xml`; se estiverem em um diretório aninhado `aghuse/`, trabalhar a partir dele.
- Não aplicar estas convenções a outro sistema Java EE apenas pela semelhança da stack.
- Ler o estado do Git antes de qualquer alteração e preservar trabalho existente.

## Manter o escopo mínimo

- Tratar o requisito e as decisões explícitas do usuário como limite fechado da implementação. Alterar somente o indispensável para atendê-los, compilar e preservar os contratos diretamente afetados.
- Antes de modificar um arquivo, relacionar a mudança a um item concreto do requisito. Se não houver relação direta, não alterar o arquivo.
- Preferir a menor solução compatível com a arquitetura existente. Não aproveitar a tarefa para refatorar, modernizar, renomear, reorganizar, reformatar, generalizar ou corrigir comportamento adjacente não solicitado.
- Não adicionar flexibilidade especulativa, abstrações para uso futuro, validações extras, novos fluxos ou cobertura alheia ao comportamento alterado. Testes devem ser proporcionais ao requisito e às regressões diretas da mudança.
- Quando identificar melhoria, débito técnico ou defeito fora do requisito, registrar separadamente no handoff e não implementar sem autorização explícita.
- Se uma ambiguidade puder ampliar o escopo ou mudar o comportamento pedido, interromper essa parte e solicitar decisão; não assumir a alternativa mais abrangente.

## Coordenar os especialistas

- `aghuse_analyst`: análise somente leitura de chamados e requisitos, com relatório de escopo, abordagem, alternativas, prós, contras, riscos, testes e recomendação.
- `aghuse_frontend`: JSF/Facelets, PrimeFaces, XHTML, controllers de apresentação, navegação e recursos dos WARs de interface.
- `aghuse_backend`: Java 17, EJB/CDI, manutenção de RNs existentes, novas ONs, Facades, APIs, services, integrações, contratos `*-client` e empacotamento EAR.
- `aghuse_database`: entidades JPA, DAOs, consultas, Oracle/PostgreSQL, JTA, Envers, Search, cache e desempenho.
- `aghuse_tests`: criação e manutenção de testes unitários exclusivamente para ONs e RNs existentes, com JUnit 5, Mockito, Surefire, fixtures, isolamento, diagnóstico e cobertura. Pode executar outros testes para diagnóstico, mas não deve criá-los nem modificá-los.

Ao criar ou revisar scripts de banco com o `aghuse_database`, aplicar também a skill `aghuse-idempotent-database-scripts`. Scripts de aplicação e rollback devem ser idempotentes.

Acionar o `aghuse_analyst` quando o usuário pedir análise, triagem, entendimento, planejamento ou relatório de uma tarefa. Ele deve permanecer somente leitura e entregar o relatório antes que qualquer especialista de implementação seja acionado. Não exigir essa etapa quando o pedido já estiver suficientemente especificado e for apenas uma correção pequena e direta.

Para tarefa restrita, delegar apenas ao perfil correspondente. Para tarefa transversal, delegar a análise aos especialistas relevantes e definir handoffs explícitos antes da implementação. Permitir trabalho paralelo somente com arquivos sem sobreposição. Se contrato, schema ou comportamento ainda estiver ambíguo, sequenciar banco -> backend -> frontend -> testes, adaptando a ordem à tarefa.

Ao solicitar cobertura ao `aghuse_tests`, identifique a ON ou RN responsável. Antes de autorizar uma nova classe `*ONTest` ou `*RNTest`, exija a busca por testes do mesmo fluxo no módulo, em todo o repositório e nas branches relacionadas, usando `git log --all`, `git ls-tree` e `git show` sem trocar de branch. Prefira ampliar ou portar a classe de teste existente, preservando seus cenários compatíveis; uma nova classe só deve ser criada quando a busca demonstrar que não há teste adequado. Não importe produção alheia apenas para fazer compilar um teste encontrado em outra branch.

Não delegue ao `aghuse_tests` a criação ou alteração de testes de controller/action, facade, EJB/service, DAO/repository, entidade, VO, converter, listener, resource ou integração. Se o comportamento ainda não estiver em uma ON/RN coerente, encaminhe primeiro a decisão de desenho ao `aghuse_backend`, sem criar produção apenas para acomodar o teste.

O coordenador deve revisar o diff integrado e validar o fluxo completo. Não ocupar todos os perfis quando um ou dois bastarem.

## Preservar a arquitetura

- Tratar `aghu-entidades` como projeto Maven separado e `aghu/pom.xml` como agregador multi-módulo.
- Preservar Java 17, Maven 3.9+, WildFly 26.1.3, Java EE 8, EJB 3.2, CDI e o uso predominante de `javax.*`; não migrar mecanicamente para `jakarta.*`.
- Tratar módulos `*-client` como contratos Java, não como frontend web.
- Tratar `aghu-web`, `aghu-pesquisa-web` e `aghu-mobile-web` como interfaces JSF; `aghu-api-web` e `aghu-api-jwt-web` pertencem ao backend.
- Preservar padrões RN existentes, ON, Facade, BaseBusiness, BaseFacade, BaseDao e BaseFitDao. Para uma nova regra, reutilizar uma RN existente quando sua responsabilidade for compatível e coesa. Se não houver classe compatível e for necessária uma nova classe de negócio, criá-la como `*ON`; nunca criar uma nova `*RN`. Não renomear nem migrar RNs em massa sem solicitação explícita.
- Considerar Oracle e PostgreSQL em consultas específicas e manter separadas as unidades `aghu-pu` e `aghu-fit-pu`.

## Proteger dados e infraestrutura

- Tratar dados clínicos, pacientes, profissionais e faturamento como sensíveis. Usar somente dados fictícios e anonimizados.
- Nunca expor credenciais, tokens, URLs privadas, strings de conexão ou identificadores pessoais.
- Não conectar a banco, LDAP, WildFly ou serviços reais sem autorização explícita.
- Não executar deploy, DDL, DML, procedures, Docker, Kubernetes ou scripts de CI contra ambientes compartilhados.
- Não executar `.scripts-validate/dao-tests` automaticamente; ele depende de configuração externa e pode acessar banco.

## Validar proporcionalmente

Começar pelo teste ou módulo afetado. Para build amplo sem testes, instalar primeiro as entidades e depois o agregador:

```bash
mvn clean install --activate-profiles '!PMD' --threads 1C --file aghu-entidades/pom.xml -Dmaven.test.skip=true -Dpmd.skip=true
mvn clean install --activate-profiles '!PMD,!gitinfo' --threads 1C --file aghu/pom.xml -Dmaven.test.skip=true -Dpmd.skip=true
```

Para escopo direcionado, preferir `--projects <modulo> --also-make`. Não executar a suíte completa de aproximadamente 1.400 testes quando um teste ou módulo reproduzir adequadamente a mudança.

## Auditar o diff da implementação

Antes de editar, registrar o baseline da worktree com `git status --short`, `git diff --name-status`, `git diff --numstat` e `git diff --check`. Inspecionar o diff preexistente dos arquivos que possam ser alterados. Esse baseline pertence ao usuário e não deve ser removido, sobrescrito nem atribuído à implementação atual.

Após integrar a implementação e antes de concluir:

1. Executar novamente `git status --short`, `git diff --name-status`, `git diff --stat`, `git diff --numstat` e `git diff --check` a partir da raiz correta do repositório.
2. Comparar o resultado com o baseline e revisar `git diff -- <arquivo>` de cada arquivo tocado pela tarefa. Para arquivos novos ainda não rastreados, inspecionar o conteúdo completo e executar `git diff --no-index --check /dev/null <arquivo>`.
3. Confirmar que cada hunk é necessário ao requisito e que nenhum arquivo alheio entrou no escopo. Mudanças preexistentes podem permanecer, mas devem ser distinguidas das mudanças da tarefa no handoff.
4. Tratar como defeito um diff desproporcional ao trabalho realizado, como um arquivo inteiro alterado para poucas linhas funcionais. Investigar imediatamente EOL/CRLF, encoding, BOM, indentação, formatador, geração automática ou substituição mecânica. Usar `git diff --ignore-space-at-eol --ignore-cr-at-eol -- <arquivo>` quando isso ajudar a isolar a causa.
5. Se houver alteração massiva acidental, reconstruir somente a edição da tarefa preservando os bytes, finais de linha e formatação originais; não usar reset, checkout ou outra operação que descarte mudanças do usuário. Repetir a auditoria até o diff conter apenas as alterações funcionais indispensáveis.

Não declarar a implementação concluída enquanto `git diff --check` falhar, houver arquivo inesperado ou permanecer diff integral causado apenas por formatação, EOL ou encoding. Não executar formatador sobre arquivo ou módulo inteiro sem solicitação explícita.

## Higienizar a worktree

Ao final de toda implementação, comparar `git status --short --untracked-files=all` com o baseline e higienizar a worktree antes do handoff:

- Remover somente resíduos comprovadamente criados pela execução atual e que não pertençam à entrega, como dumps de diagnóstico, relatórios temporários, backups de edição e arquivos acidentais.
- Manter os arquivos necessários à implementação, mesmo ainda não rastreados, e preservar todas as mudanças preexistentes do usuário.
- Nunca usar `git clean`, `git reset`, `git checkout`, exclusão recursiva ampla ou outro atalho capaz de apagar trabalho legítimo. Resolver apenas caminhos exatos cuja origem e descarte estejam confirmados.
- Se a propriedade de um arquivo for incerta, não removê-lo; registrar a pendência no handoff.
- Repetir `git status`, a auditoria do diff e `git diff --check`. O estado final deve conter somente o baseline preservado e os arquivos indispensáveis ao requisito, sem artefatos ou mudanças inesperadas.

## Concluir

Consolidar o handoff com: resultado, evidências, especialistas acionados, arquivos alterados, contratos entre camadas, comandos e validações, auditoria do diff contra o baseline, riscos, limitações e próxima responsabilidade. Não declarar pronto para homologação sem revisão do diff e roteiro reproduzível do fluxo afetado.
