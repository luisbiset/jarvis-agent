---
name: aghuse-historico-alteracoes
description: Investigar no histórico Git do AGHUse quando código, mensagens, páginas ou regras existiam e foram alterados, removidos ou restaurados. Usar para comparar tarefa oficial, branches e regressões sem trocar de branch nem modificar arquivos.
---

# Histórico de alterações do AGHUse

Investigue somente em leitura. Use o subcomando `historico` de `scripts/aghuse_automacao.py` para localizar commits por tarefa ou termo e complemente com `git show`, `git log -S`, `git log -G`, `git blame` e `git ls-tree` quando necessário.

## Comparar

- Identificar o commit que introduziu o comportamento e os commits posteriores que o tocaram.
- Examinar arquivos diretamente do objeto Git; não fazer checkout de outra branch.
- Distinguir remoção intencional, regressão, conflito de merge e ausência apenas na branch atual.
- Para mensagens, comparar chaves e valores sem restaurar traduções alheias ao fluxo.
- Para testes encontrados em outra branch, avaliar compatibilidade antes de recomendar portabilidade.

## Entregar

Apresentar linha do tempo, evidências por commit e arquivo, conclusão e menor restauração recomendada. Não restaurar ou commitar até o usuário solicitar a mudança.
