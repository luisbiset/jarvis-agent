---
name: aghuse-development
description: Coordenar análise, implementação, testes e revisão no AGHUse por meio dos subagentes aghuse_analyst, aghuse_frontend, aghuse_backend, aghuse_database e aghuse_tests. Usar em tarefas de um repositório com aghu/pom.xml e aghu-entidades/pom.xml ou que mencionem AGHUse, EJB, JSF, PrimeFaces, RN, ON, Facade ou módulos clínicos do sistema.
---

# Coordenação do AGHUse

## Identificar o projeto

- Localizar a raiz que contém `aghu/pom.xml` e `aghu-entidades/pom.xml`; se estiverem em um diretório aninhado `aghuse/`, trabalhar a partir dele.
- Não aplicar estas convenções a outro sistema Java EE apenas pela semelhança da stack.
- Ler o estado do Git antes de qualquer alteração e preservar trabalho existente.

## Coordenar os especialistas

- `aghuse_analyst`: análise somente leitura de chamados e requisitos, com relatório de escopo, abordagem, alternativas, prós, contras, riscos, testes e recomendação.
- `aghuse_frontend`: JSF/Facelets, PrimeFaces, XHTML, controllers de apresentação, navegação e recursos dos WARs de interface.
- `aghuse_backend`: Java 17, EJB/CDI, manutenção de RNs existentes, novas ONs, Facades, APIs, services, integrações, contratos `*-client` e empacotamento EAR.
- `aghuse_database`: entidades JPA, DAOs, consultas, Oracle/PostgreSQL, JTA, Envers, Search, cache e desempenho.
- `aghuse_tests`: JUnit 5, Mockito, Surefire, fixtures, isolamento, diagnóstico e cobertura de testes unitários.

Ao criar ou revisar scripts de banco com o `aghuse_database`, aplicar também a skill `aghuse-idempotent-database-scripts`. Scripts de aplicação e rollback devem ser idempotentes.

Acionar o `aghuse_analyst` quando o usuário pedir análise, triagem, entendimento, planejamento ou relatório de uma tarefa. Ele deve permanecer somente leitura e entregar o relatório antes que qualquer especialista de implementação seja acionado. Não exigir essa etapa quando o pedido já estiver suficientemente especificado e for apenas uma correção pequena e direta.

Para tarefa restrita, delegar apenas ao perfil correspondente. Para tarefa transversal, delegar a análise aos especialistas relevantes e definir handoffs explícitos antes da implementação. Permitir trabalho paralelo somente com arquivos sem sobreposição. Se contrato, schema ou comportamento ainda estiver ambíguo, sequenciar banco -> backend -> frontend -> testes, adaptando a ordem à tarefa.

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

## Concluir

Consolidar o handoff com: resultado, evidências, especialistas acionados, arquivos alterados, contratos entre camadas, comandos e validações, riscos, limitações e próxima responsabilidade. Não declarar pronto para homologação sem revisão do diff e roteiro reproduzível do fluxo afetado.
