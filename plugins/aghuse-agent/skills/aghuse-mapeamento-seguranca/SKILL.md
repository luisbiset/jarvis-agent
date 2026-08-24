---
name: aghuse-mapeamento-seguranca
description: Diagnosticar permissões, perfis e menus do AGHUse a partir de página negada, log do SecurityPhaseListener ou tarefa de mapeamento. Usar para localizar a alteração e orientar simulação do atualizador; execução real exige autorização explícita.
---

# Mapeamento de segurança do AGHUse

Use o subcomando `seguranca` de `scripts/aghuse_automacao.py` para extrair usuário, página e método de logs. Depois pesquise a página, permissão, menu e perfil nos repositórios de aplicação, mapeamento e atualizador disponíveis.

## Diagnosticar

- Distinguir permissão inexistente no mapeamento, atualização não aplicada, perfil sem permissão e usuário sem perfil.
- Confirmar que a branch informada pertence ao repositório `mapeamento-seguranca`.
- Relacionar página e ação aos nomes exatos das permissões; não adivinhar pelo texto do menu.
- Recomendar simulação antes da execução e comparar seus resultados.
- Após atualização, orientar nova autenticação e conferência do vínculo usuário-perfil.

## Limites

Não executar Jenkins, atualizador, banco, LDAP ou concessão real automaticamente. Apresentar parâmetros e efeitos esperados e pedir autorização imediatamente antes de qualquer alteração compartilhada.
