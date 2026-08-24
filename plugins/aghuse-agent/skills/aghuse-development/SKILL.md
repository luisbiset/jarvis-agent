---
name: aghuse-development
description: Coordenar o ciclo do AGHUse entre análise paralela, plano aprovado, desenvolvimento, validação independente e gate humano. Usar em tarefas de um repositório com aghu/pom.xml e aghu-entidades/pom.xml ou que mencionem AGHUse, EJB, JSF, PrimeFaces, RN, ON, Facade ou módulos clínicos do sistema.
---

# Coordenação do AGHUse

## Identificar o projeto

- Localizar a raiz que contém `aghu/pom.xml` e `aghu-entidades/pom.xml`; se estiverem em um diretório aninhado `aghuse/`, trabalhar a partir dele.
- Não aplicar estas convenções a outro sistema Java EE apenas pela semelhança da stack.
- Ler o estado do Git antes de qualquer alteração e preservar trabalho existente.

## Executar a arquitetura do AGHUse Agent

Antes de rotear, declare no handoff V2: `complexity`, `risk_class`, `operational_mode`, `reasoning_class`, `max_agents` e `max_parallel_agents`. Use `TRIVIAL` (um especialista e Auditor opcional, até 2 agentes), `LOCALIZED` (até 3), `TRANSVERSAL` (até 6) ou `CRITICAL` (até 8); exceder o budget exige justificativa. Um especialista único pode implementar diretamente uma correção trivial, sem camada adicional de Desenvolvedor. O Reviewer não participa de tarefa trivial e torna-se obrigatório somente por risco sistêmico alto/crítico.

Use `FAST` para baseline, busca e validação mecânica; `NORMAL` para implementação localizada; `DEEP` para ambiguidade, impacto transversal, incidente difícil ou revisão de alto risco. Escalone somente com evidência. Não acione `aghuse_analyst` e `aghuse_requisitos_e_legado` juntos sem justificativa explícita.

Para uma tarefa completa, conduzir este fluxo:

```text
Coordenador
    ↓
Análise paralela
    ├── Requisitos e legado
    └── Banco e impacto
             ↓
      Plano aprovado
             ↓
       Desenvolvedor
             ↓
    Validação paralela
    ├── QA
    └── Auditor do diff
             ↓
        Gate humano
```

Os nomes do fluxo correspondem a estes contratos:

- **Coordenador:** esta skill; delimita a tarefa, preserva o baseline, distribui o trabalho e integra os handoffs.
- **Requisitos e legado:** `aghuse_requisitos_e_legado`; confirma requisitos, critérios de aceite, comportamento e histórico sem editar.
- **Banco e impacto:** `aghuse_banco_e_impacto`; avalia persistência, schema e impactos transversais sem editar.
- **Desenvolvedor:** `aghuse_desenvolvedor`; executa o plano e integra somente os especialistas técnicos necessários.
- **QA:** `aghuse_qa`; valida requisitos, testes, build e roteiro funcional sem corrigir a implementação avaliada.
- **Auditor do diff:** `aghuse_auditor_do_diff`; revisa baseline, escopo, hunks, arquivos inesperados, EOL/encoding, segredos e higiene da worktree em modo somente leitura.
- **Gate humano:** o usuário; decide aceitar, pedir correções, autorizar commit/push ou liberar qualquer ação externa. Nunca substituir este gate por um agente.

Na **Análise paralela**, acionar Requisitos e legado e Banco e impacto simultaneamente quando as frentes puderem ser investigadas sem sobreposição. Consolidar os dois resultados em um único plano com escopo, critérios de aceite, arquivos ou módulos prováveis, contratos, responsáveis, validações, riscos e pendências. Não iniciar a implementação até o usuário aprovar esse plano. Um pedido direto de implementação que já contenha escopo e decisões suficientes vale como aprovação do plano descrito no próprio pedido; não criar uma confirmação cerimonial para correções pequenas e inequívocas.

No estágio **Desenvolvedor**, usar os especialistas de camada abaixo do perfil integrador. Definir propriedade de arquivos e evitar edições paralelas sobre o mesmo contrato. Quando houver mudança de contrato, sequenciar produtor antes do consumidor.

Na **Validação paralela**, congelar o diff funcional e acionar QA e Auditor do diff de forma independente. Se qualquer um reprovar, retornar os achados mínimos ao Desenvolvedor e repetir a validação afetada. Apresentar ao Gate humano o resultado consolidado, incluindo o que foi executado, o que não pôde ser validado e os riscos restantes. Gate humano não implica autorização automática para Redmine, banco, deploy, commit ou push; cada ação continua limitada ao pedido explícito do usuário.

Persistir as transições `NEW -> DISCOVERY -> PLAN_READY -> PLAN_APPROVED -> IMPLEMENTING -> VALIDATING -> REVIEW_READY -> HUMAN_GATE -> HOMOLOGATION_READY -> DONE` quando o runtime local estiver disponível. Falha de validação ou pedido de mudança retorna somente ao estágio necessário. Tarefas triviais/localizadas com pedido direto inequívoco podem ir de `NEW` a `PLAN_APPROVED`; fluxos formais não podem iniciar developer antes desse estado.

Parar antes de escrever por requisito ambíguo, contrato compartilhado fora do escopo, teste contraditório, autorização externa ausente, contexto insuficiente ou divergência não resolvida. Se a solução de risco alto não puder ser explicada, usar `NEEDS_EXPLANATION`.

Para diagnóstico ou correção restrita, o Coordenador pode reduzir o fluxo aos perfis necessários. Não simular paralelismo, aprovação ou validação sem benefício real, mas nunca omitir o Gate humano para ações externas ou destrutivas.

## Manter o escopo mínimo

- Tratar o requisito e as decisões explícitas do usuário como limite fechado da implementação. Alterar somente o indispensável para atendê-los, compilar e preservar os contratos diretamente afetados.
- Antes de modificar um arquivo, relacionar a mudança a um item concreto do requisito. Se não houver relação direta, não alterar o arquivo.
- Preferir a menor solução compatível com a arquitetura existente. Não aproveitar a tarefa para refatorar, modernizar, renomear, reorganizar, reformatar, generalizar ou corrigir comportamento adjacente não solicitado.
- Não adicionar flexibilidade especulativa, abstrações para uso futuro, validações extras, novos fluxos ou cobertura alheia ao comportamento alterado. Testes devem ser proporcionais ao requisito e às regressões diretas da mudança.
- Quando identificar melhoria, débito técnico ou defeito fora do requisito, registrar separadamente no handoff e não implementar sem autorização explícita.
- Se uma ambiguidade puder ampliar o escopo ou mudar o comportamento pedido, interromper essa parte e solicitar decisão; não assumir a alternativa mais abrangente.

## Coordenar os especialistas

Os perfis do fluxo governam os handoffs; os especialistas abaixo executam responsabilidades técnicas dentro do estágio Desenvolvedor:

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

O coordenador deve integrar os handoffs, mas a revisão independente do diff pertence ao `aghuse_auditor_do_diff`. Não ocupar todos os perfis quando um fluxo reduzido for proporcional ao pedido.

## Acionar automações especializadas

Use somente as skills necessárias ao estágio atual:

- `aghuse-preparacao-tarefa`: baseline, tarefa, branch, módulos e pré-requisitos antes da implementação.
- `aghuse-historico-alteracoes`: investigação de código, mensagens ou regras removidas e comparação de branches sem checkout.
- `aghuse-entrega-banco`: pacote externo de aplicação e rollback para Redmine; scripts de implantação não entram no repositório AGHUse.
- `aghuse-mapeamento-seguranca`: diagnóstico de página negada, permissões, perfis, menus e orientação do atualizador.
- `aghuse-validacao-direcionada`: seleção proporcional de módulos Maven, testes, XHTML e mensagens.
- `aghuse-diagnostico-logs`: causa raiz de logs e stack traces, sem implementar a correção automaticamente.
- `aghuse-roteiro-homologacao`: roteiro manual reproduzível com `qa_homologacao`; não usar computer use por padrão.
- `aghuse-verificacao-entrega`: portão final de diff, tarefa, validações, scripts externos e prontidão.

As automações são complementares e não formam uma sequência obrigatória. Diagnóstico e preparação permanecem somente leitura; qualquer alteração compartilhada continua exigindo autorização própria.

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

## Preparar o diff para auditoria

Antes de editar, registrar o baseline da worktree com `git status --short`, `git diff --name-status`, `git diff --numstat` e `git diff --check`. Inspecionar o diff preexistente dos arquivos que possam ser alterados. Esse baseline pertence ao usuário e não deve ser removido, sobrescrito nem atribuído à implementação atual.

Após integrar a implementação e antes de entregar ao Auditor do diff:

1. Executar novamente `git status --short`, `git diff --name-status`, `git diff --stat`, `git diff --numstat` e `git diff --check` a partir da raiz correta do repositório.
2. Comparar o resultado com o baseline e revisar `git diff -- <arquivo>` de cada arquivo tocado pela tarefa. Para arquivos novos ainda não rastreados, inspecionar o conteúdo completo e executar `git diff --no-index --check /dev/null <arquivo>`.
3. Confirmar que cada hunk é necessário ao requisito e que nenhum arquivo alheio entrou no escopo. Mudanças preexistentes podem permanecer, mas devem ser distinguidas das mudanças da tarefa no handoff.
4. Tratar como defeito um diff desproporcional ao trabalho realizado, como um arquivo inteiro alterado para poucas linhas funcionais. Investigar imediatamente EOL/CRLF, encoding, BOM, indentação, formatador, geração automática ou substituição mecânica. Usar `git diff --ignore-space-at-eol --ignore-cr-at-eol -- <arquivo>` quando isso ajudar a isolar a causa.
5. Se houver alteração massiva acidental, reconstruir somente a edição da tarefa preservando os bytes, finais de linha e formatação originais; não usar reset, checkout ou outra operação que descarte mudanças do usuário. Repetir a auditoria até o diff conter apenas as alterações funcionais indispensáveis.

Não encaminhar a implementação à Validação paralela enquanto `git diff --check` falhar, houver arquivo inesperado ou permanecer diff integral causado apenas por formatação, EOL ou encoding. Não executar formatador sobre arquivo ou módulo inteiro sem solicitação explícita.

## Higienizar a worktree

Ao final de toda implementação, comparar `git status --short --untracked-files=all` com o baseline e higienizar a worktree antes do handoff:

- Remover somente resíduos comprovadamente criados pela execução atual e que não pertençam à entrega, como dumps de diagnóstico, relatórios temporários, backups de edição e arquivos acidentais.
- Manter os arquivos necessários à implementação, mesmo ainda não rastreados, e preservar todas as mudanças preexistentes do usuário.
- Nunca usar `git clean`, `git reset`, `git checkout`, exclusão recursiva ampla ou outro atalho capaz de apagar trabalho legítimo. Resolver apenas caminhos exatos cuja origem e descarte estejam confirmados.
- Se a propriedade de um arquivo for incerta, não removê-lo; registrar a pendência no handoff.
- Repetir `git status`, a auditoria do diff e `git diff --check`. O estado final deve conter somente o baseline preservado e os arquivos indispensáveis ao requisito, sem artefatos ou mudanças inesperadas.

## Concluir

Consolidar para o Gate humano usando `contracts/handoff.schema.json`: run/version, plano aprovado, requisitos, evidência observada separada de interpretação, provenance, ownership por arquivo, contratos, validações executadas/aprovadas/reprovadas/não executadas, parecer do QA, auditoria do diff, riscos, limitações, stop reason e próxima responsabilidade. Aplicar as políticas `AGH-RN-001`, `AGH-DB-001`, `AGH-DB-002`, `AGH-DB-003`, `AGH-TEST-001`, `SEC-001`, `FLOW-001` e `FLOW-002`. Não declarar pronto para homologação sem parecer do Auditor do diff e roteiro reproduzível do fluxo afetado.
