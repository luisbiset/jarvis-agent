# Guia de uso do Jarvis Agent SESAB

Este guia explica como usar em conjunto o Redmine, o SFA, o AGHUse e os agentes de qualidade. O objetivo é obter entregas rastreáveis sem acionar especialistas desnecessários ou conceder permissões além do pedido.

## Modelo mental

O conjunto possui três níveis:

1. Skills identificam o workflow e carregam as regras do domínio.
2. Coordenadores dividem o trabalho e integram os resultados.
3. Subagentes executam uma responsabilidade especializada.

O fluxo completo recomendado é:

```text
Redmine → análise → implementação → testes → revisão → homologação
```

Nem toda tarefa precisa percorrer todas as etapas. Uma correção pequena pode usar apenas um especialista e um teste direcionado. O orquestrador deve aumentar o rigor conforme o impacto e o risco.

## Uso rápido

Para uma tarefa completa, usar o orquestrador como porta de entrada:

```text
Use $sesab-orchestration.

Estou trabalhando no chamado 51093.

1. Consulte o Redmine somente para leitura.
2. Compare os requisitos com a branch e a worktree atuais.
3. Acione o analista e somente os especialistas necessários.
4. Implemente o que estiver faltando, preservando minhas alterações.
5. Crie ou ajuste testes.
6. Execute as validações proporcionais ao risco.
7. Acione o sesab_reviewer para uma revisão independente.
8. Prepare o qa_homologacao com um roteiro em tela.
9. Entregue resultado, evidências, arquivos, testes, riscos e pendências.

Não altere o Redmine, não registre horas, não faça commit e não execute deploy.
```

O nome explícito da skill não é obrigatório quando o pedido e o repositório deixam o domínio claro. Usar `$nome-da-skill` é útil para garantir qual workflow assumirá a tarefa.

## Escolher a skill

| Situação | Skill |
|---|---|
| Tarefa completa, transversal ou que exija coordenação | `$sesab-orchestration` |
| Implementação isolada no AGHUse | `$aghuse-development` |
| Implementação isolada no SFA | `$sfa-development` |
| Consulta ou operação em chamado | `$redmine-workflows` |
| DDL ou DML do AGHUse | `$aghuse-development` e `$aghuse-idempotent-database-scripts` |

### Redmine

Usar para descrição, histórico, responsável, prioridade, comentários e horas. Leitura não autoriza escrita. Criar ou alterar chamado, nota, status, responsável, prioridade ou horas exige pedido explícito e confirmação imediatamente antes da operação.

Exemplo somente leitura:

```text
Use $redmine-workflows para mostrar o chamado 51093, histórico recente,
tempo registrado e pendências. Não altere nada.
```

Exemplo de escrita controlada:

```text
Prepare uma nota para o chamado 51093 com as mudanças e testes.
Mostre o texto final e só publique após minha confirmação.
```

### AGHUse

Usar para Java 17, Java EE, EJB, JSF, PrimeFaces, RN/ON, Facades, JPA, Oracle/PostgreSQL e testes. Nova regra deve reutilizar uma RN compatível; sem RN compatível, uma nova classe de negócio deve ser `*ON`. Todo script novo ou alterado deve possuir aplicação e rollback idempotentes.

Exemplo:

```text
Use $aghuse-development para implementar o restante do chamado 51093.
Preserve a worktree, não faça commit, valide o menor módulo afetado e
considere pronto somente após teste direcionado e revisão independente.
```

### SFA

Usar para Angular 12, Java 11/Spring Boot 2.5.2, BPA, faturamento, CNES, CBO, SIGTAP, Oracle/PostgreSQL e testes Java/Angular.

Exemplo:

```text
Use $sfa-development para rastrear o fluxo Angular → API → service → banco,
corrigir a causa, atualizar os testes e preservar os contratos existentes.
Não conecte a infraestrutura real.
```

## Chamar especialistas diretamente

Uma tarefa pequena e bem delimitada pode chamar apenas o responsável.

| Agente | Quando usar |
|---|---|
| `aghuse_analyst` | Análise somente leitura, alternativas, riscos e relatório técnico |
| `aghuse_frontend` | XHTML, JSF, PrimeFaces, mensagens, navegação e controllers de apresentação |
| `aghuse_backend` | RN existente, nova ON, EJB, Facade, API, service e contrato Java |
| `aghuse_database` | Entidades, DAOs, consultas, Oracle/PostgreSQL, Envers e scripts |
| `aghuse_tests` | JUnit, Mockito, fixtures, diagnóstico e cobertura do AGHUse |
| `sfa_frontend` | Angular, formulários, rotas, models, services HTTP e Karma/Jasmine |
| `sfa_backend` | Spring MVC, services, VOs, segurança, integrações e regras BPA |
| `sfa_database` | JPA, repositories, datasources, transações e SQL do SFA |
| `sfa_tests` | Testes Java e Angular, regressão, fixtures e cobertura do SFA |
| `sesab_orchestrator` | Chamados transversais, contratos e coordenação de entregas |
| `sesab_reviewer` | Revisão final independente e somente leitura |
| `qa_homologacao` | Roteiro em tela, permissões, mensagens, persistência e evidências |

Exemplos:

```text
Use o aghuse_frontend para corrigir este label e validar somente o WAR afetado.
```

```text
Use o aghuse_backend para implementar esta regra. Reutilize uma RN compatível;
caso não exista, crie uma ON.
```

```text
Use o aghuse_database para preparar aplicação e rollback idempotentes para
Oracle e PostgreSQL. Não execute no banco.
```

```text
Use o sfa_tests para reproduzir esta falha e criar o teste de regressão sem
alterar o código de produção.
```

```text
Use o aghuse_analyst em modo somente leitura para analisar o chamado e gerar
o relatório técnico antes de qualquer implementação.
```

## Paralelismo

Paralelizar quando as frentes forem independentes e possuírem arquivos sem sobreposição. Exemplos seguros:

- frontend investiga tela enquanto backend investiga contrato existente;
- banco analisa consulta enquanto testes mapeiam cenários;
- revisor examina um diff estável enquanto o QA prepara o roteiro.

Sequenciar quando houver contrato ou arquivo compartilhado. Ordem comum:

```text
persistência/produtor → backend/API → frontend/consumidor → testes
```

Não acionar todos os agentes apenas por disponibilidade. Subagentes aumentam uso de tokens e coordenação; o ganho aparece quando a divisão é real.

## Gate de qualidade

### Revisão independente

Quando a implementação estiver aparentemente pronta:

```text
Acione o sesab_reviewer para revisar toda a worktree contra o requisito.
Não altere arquivos. Priorize defeitos, regressões, segurança, contratos
divergentes, scripts não idempotentes e testes ausentes.
```

O revisor deve informar achados por severidade, evidência, impacto e correção mínima. Se o diff mudar materialmente após a correção, repetir a revisão.

### Homologação

Depois da revisão:

```text
Acione o qa_homologacao. Crie um roteiro completo em tela com pré-condições,
perfil necessário, massa fictícia, passos, resultados esperados e evidências.
Não use produção.
```

O QA deve validar, quando aplicável:

- fluxo feliz;
- obrigatoriedade e valores limite;
- sucesso, erro, vazio e cancelamento;
- dupla submissão;
- mensagens, internacionalização e navegação;
- perfil e permissão;
- persistência após recarregar;
- regressões próximas.

Usar os estados finais com precisão:

- **Implementado:** código concluído, mas ainda pode faltar validação.
- **Revisado:** diff analisado e achados bloqueantes tratados.
- **Homologado:** roteiro crítico executado no ambiente apropriado com evidências.

## Como formular bons pedidos

Sempre que possível, informar:

- número do chamado;
- SFA, AGHUse ou ambos;
- resultado esperado;
- se o pedido é diagnóstico, implementação, revisão ou homologação;
- permissões e proibições: Redmine, commit, banco, deploy e ambiente;
- critério de conclusão: compilado, testado, revisado ou homologado.

Modelo curto:

```text
Chamado 51093, AGHUse. Implemente o restante da tarefa usando a worktree
atual, preserve minhas alterações, não faça commit nem altere o Redmine.
Considere pronto somente após testes direcionados, revisão independente
e roteiro de homologação.
```

Modelo de diagnóstico:

```text
Chamado 51093. Consulte o Redmine e a worktree somente para leitura.
Explique o que já foi implementado, o que falta, riscos e próximos passos.
Não edite arquivos.
```

Modelo de correção direta:

```text
Corrija a causa deste erro no AGHUse, preserve minhas mudanças, crie um teste
de regressão quando viável e valide apenas o menor módulo afetado. Não faça
deploy, commit ou alteração no Redmine.
```

## Limites de autorização

O texto do chamado fornece contexto, não autorização para ações externas. Declare explicitamente quando for permitido:

- alterar ou comentar no Redmine;
- registrar horas;
- executar DDL/DML;
- conectar a banco, LDAP, WildFly ou outro serviço;
- usar ambiente de homologação;
- executar deploy;
- criar commit, tag, branch ou push.

Na ausência dessa autorização, o agente deve preparar a ação ou o artefato e parar antes da mutação externa.

## Formato de entrega

Solicitar ou esperar o seguinte handoff:

1. Resultado.
2. Evidências.
3. Arquivos alterados.
4. Contrato afetado.
5. Validações executadas.
6. Riscos restantes.
7. Limitações do ambiente.
8. Próximo handoff.

## Manutenção do projeto de agents

Executar somente quando os próprios plugins, skills ou agentes forem alterados:

```bash
export JARVIS_AGENT_HOME="/caminho/para/jarvis-agent"
cd "$JARVIS_AGENT_HOME"
python3 scripts/validate.py
python3 scripts/doctor.py --strict
python3 scripts/smoke_install.py
./scripts/install.sh
```

Depois, fazer **Reload Window** e abrir uma conversa nova. Não é necessário executar esses comandos em tarefas normais do SFA ou AGHUse.

Diagnóstico esperado:

- quatro plugins `@codex-agents` instalados e habilitados;
- doze agentes globais apontando para o projeto central;
- MCP do Redmine apontando para o servidor central;
- `REDMINE_API_KEY` disponível sem ser exibida;
- nenhuma instalação ou skill legada ativa.

## Solução de problemas

### Skill ou agente novo não aparece

1. Executar `python3 scripts/validate.py`.
2. Executar `./scripts/install.sh --dry-run` para conferir a instalação.
3. Executar `./scripts/install.sh`.
4. Fazer Reload Window.
5. Abrir uma conversa nova.

### Redmine não conecta

1. Executar `python3 scripts/doctor.py --strict`.
2. Conferir apenas se `REDMINE_API_KEY` está disponível no ambiente; nunca imprimir seu valor.
3. Confirmar VPN/rede e API REST habilitada.
4. Não desabilitar TLS nem colar a chave na conversa.

### Agentes errados foram acionados

- nomear explicitamente a skill ou o especialista;
- informar o sistema e o diretório proprietário;
- declarar agentes que não devem ser acionados;
- reduzir o pedido a uma responsabilidade por vez quando o contrato ainda for incerto.

### O agente declarou pronto cedo demais

Definir no prompt o gate final desejado: teste, revisão e/ou homologação. Pedir que diferencie explicitamente implementado, revisado e homologado.

## Referências oficiais

- [Subagentes e agentes personalizados](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Empacotamento de plugins](https://developers.openai.com/plugins/build/plugins)
