---
name: aghuse-diagnostico-logs
description: Analisar logs e stack traces do AGHUse para localizar a causa raiz e classificar falhas de banco, segurança, JSF, CDI/EJB, persistência ou deploy. Usar para diagnóstico somente leitura, sem implementar correções automaticamente.
---

# Diagnóstico de logs do AGHUse

Trate logs como potencialmente sensíveis. Não reproduza credenciais, conexões, identificadores pessoais ou dados clínicos. Use o subcomando `log` de `scripts/aghuse_automacao.py` para extrair sinais sem enviar o conteúdo a serviços externos.

## Analisar

- Separar exceção raiz de wrappers Java EE e linhas repetidas.
- Identificar a primeira classe AGHUse relevante e o módulo provável.
- Classificar banco, segurança, JSF, CDI/EJB, JPA/Hibernate, configuração ou deploy.
- Correlacionar timestamp, página e operação quando disponíveis.
- Consultar código e histórico somente para hipóteses verificáveis.
- Não concluir que o último commit causou a falha apenas por proximidade temporal.

## Entregar

Informar causa mais provável, evidências, hipóteses alternativas, verificações seguras e especialista indicado. Corrigir somente quando o usuário solicitar explicitamente.
