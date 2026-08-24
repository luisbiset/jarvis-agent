---
name: aghuse-roteiro-homologacao
description: Criar roteiro manual e reproduzível de homologação para tarefas AGHUse, cobrindo pré-condições, permissões, dados fictícios, passos, resultados, regressão e evidências. Usar quando o usuário quiser testar em tela; não executar a interface por padrão.
---

# Roteiro de homologação do AGHUse

Acione `aghuse_qa` para preparar tecnicamente o roteiro a partir de requisito, diff, mensagens, permissões e scripts relacionados. Acione `qa_homologacao` somente quando o usuário solicitar a execução funcional em tela e houver ambiente autorizado no escopo.

## Estruturar

- Objetivo e versão ou branch sob teste.
- Pré-condições de banco, segurança, cadastro e perfil.
- Dados exclusivamente fictícios ou anonimizados.
- Navegação e ações numeradas, com resultado esperado em cada passo.
- Cenário principal, validações, alternativas, persistência e regressões diretas.
- Logs ou mensagens que não podem ocorrer.
- Evidências necessárias e limpeza dos dados criados.

## Resultado

Fornecer checklist executável e critérios de `Aprovado`, `Reprovado` ou `Bloqueado`. Preparar roteiro não significa homologar: casos ainda não executados devem ser declarados assim. Não usar computer use nem alterar dados reais sem pedido e autorização explícitos.
