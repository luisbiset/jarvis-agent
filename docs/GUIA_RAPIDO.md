# Guia rápido das skills do Jarvis Agent

Use `$nome-da-skill` no início do pedido quando quiser forçar um fluxo específico. Commit, push, Redmine, banco e deploy continuam exigindo autorização própria.

## Coordenação

### `$aghuse-development`

Use para analisar, implementar, testar ou revisar mudanças no AGHUse.

> Use `$aghuse-development` para corrigir esta regra no AGHUse, preservar minha worktree e executar somente os testes proporcionais ao risco. Não faça commit.

### `$sfa-development`

Use para mudanças no frontend Angular, backend Spring ou banco do SFA.

> Use `$sfa-development` para corrigir a dupla submissão neste formulário, atualizar os testes e validar o menor escopo possível.

### `$redmine-workflows`

Use para consultar ou atualizar chamados, comentários, status e horas.

> Use `$redmine-workflows` para resumir o chamado 51093 e suas pendências. Não altere nada.

## Preparação e diagnóstico do AGHUse

### `$aghuse-preparacao-tarefa`

Use antes de implementar para conferir tarefa, branch, commits, módulos e dependências.

> Use `$aghuse-preparacao-tarefa` para preparar a tarefa 51093 e informar o que falta antes da implementação.

### `$aghuse-historico-alteracoes`

Use para descobrir quando código, mensagem ou regra foi alterado ou removido.

> Use `$aghuse-historico-alteracoes` para localizar em qual commit esta mensagem foi removida, sem trocar de branch.

### `$aghuse-diagnostico-logs`

Use para encontrar a causa raiz de logs e stack traces, sem corrigir automaticamente.

> Use `$aghuse-diagnostico-logs` para analisar este stack trace, classificar a falha e indicar o arquivo e o especialista provável. Não implemente ainda.

### `$aghuse-mapeamento-seguranca`

Use para página negada, menu ausente, permissão, perfil ou `SecurityPhaseListener`.

> Use `$aghuse-mapeamento-seguranca` para diagnosticar este acesso negado e indicar página, permissão, menu e perfil a conferir. Não execute o atualizador.

## Banco do AGHUse

### `$aghuse-idempotent-database-scripts`

Use ao criar ou revisar aplicação e rollback Oracle/PostgreSQL.

> Use `$aghuse-idempotent-database-scripts` para revisar estes scripts de aplicação e rollback, garantindo que ambos possam ser executados duas vezes com segurança. Não execute no banco.

### `$aghuse-entrega-banco`

Use para preparar o pacote de scripts que será entregue externamente pelo Redmine.

> Use `$aghuse-entrega-banco` para organizar aplicação, rollback, ordem e manifesto da tarefa 51093. Mantenha os SQL fora do Git e não publique no Redmine.

## Validação e entrega do AGHUse

### `$aghuse-validacao-direcionada`

Use para escolher módulos Maven, testes e verificações mínimas após uma mudança.

> Use `$aghuse-validacao-direcionada` para mapear estes arquivos alterados aos menores testes e builds necessários. Mostre os comandos antes de executar.

### `$aghuse-roteiro-homologacao`

Use para preparar um roteiro manual e reproduzível de teste em tela.

> Use `$aghuse-roteiro-homologacao` para criar o roteiro da tarefa 51093 com pré-condições, perfil, dados fictícios, passos e resultados esperados. Não execute a interface.

### `$aghuse-verificacao-entrega`

Use como conferência final de escopo, diff, validações e prontidão.

> Use `$aghuse-verificacao-entrega` para conferir se a tarefa 51093 está pronta para o gate humano. Não faça commit, push nem atualização no Redmine.

## Escolha rápida

- Apenas AGHUse: `$aghuse-development`.
- Apenas SFA: `$sfa-development`.
- Apenas Redmine: `$redmine-workflows`.
- Dúvida sobre uma etapa AGHUse: use diretamente a skill especializada correspondente.
