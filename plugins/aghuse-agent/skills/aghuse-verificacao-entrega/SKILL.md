---
name: aghuse-verificacao-entrega
description: Verificar se uma mudança AGHUse está pronta para commit, revisão ou homologação, conferindo tarefa, diff, arquivos inesperados, scripts, mensagens, validações e roteiro. Usar como portão final; não criar commit ou push sem solicitação explícita.
---

# Verificação de entrega do AGHUse

Compare o estado final com o baseline registrado no início. Use `contexto`, `mensagens` e, quando houver pacote externo, `manifesto` de `scripts/aghuse_automacao.py`.

Acione `aghuse_auditor_do_diff` para esta verificação de escopo e higiene. Não acione `sesab_reviewer` apenas para repetir status, hunks e EOL; reserve-o para revisão sistêmica de risco alto/crítico.

## Conferir

- Cada hunk deve estar ligado ao requisito e à tarefa correta.
- Não pode haver diff integral causado por EOL, encoding ou formatação.
- Scripts de implantação não devem entrar no repositório AGHUse.
- Chaves de mensagens usadas devem existir e não ter duplicações conflitantes.
- Aplicação e rollback de banco devem estar pareados no pacote externo.
- Builds e testes proporcionais devem possuir evidências.
- Mudanças de segurança e pré-condições de homologação devem estar explícitas.
- A mensagem de commit proposta deve identificar a tarefa sem misturar chamados.

## Decidir

Classificar como `Pronto`, `Pronto com ressalvas` ou `Bloqueado`, listando evidências e pendências. Commit, push, Redmine, banco e deploy continuam exigindo autorização própria.
