---
name: aghuse-idempotent-database-scripts
description: Criar e revisar scripts de banco do AGHUse para Oracle e PostgreSQL garantindo aplicação e rollback idempotentes. Usar sempre que um script DDL ou DML do AGHUse for criado ou alterado.
---

# Scripts idempotentes de banco do AGHUse

## Invariante

Todo script novo ou alterado deve poder ser executado novamente com segurança. A aplicação repetida deve convergir para o mesmo estado esperado, sem falhar por objetos já existentes ou ausentes e sem duplicar ou corromper dados. A mesma regra vale para o rollback.

## Implementação

- Identificar explicitamente o dialeto, schema e objetos afetados.
- No Oracle, consultar o catálogo adequado ao schema e executar DDL dinâmico somente quando o estado exigir. No PostgreSQL, preferir `IF EXISTS`, `IF NOT EXISTS` ou bloco condicional quando o comando não oferecer essas cláusulas.
- Para DML, usar chaves estáveis e predicados determinísticos. Inserir, atualizar ou remover somente quando necessário; não considerar uma captura genérica de violação de chave como estratégia de idempotência.
- Considerar execução parcialmente concluída: verificar cada objeto ou alteração de forma independente e conduzir o banco ao estado final esperado.
- Não capturar nem ignorar erros inesperados. Guardas de existência devem tratar apenas o estado previsto; permissões, tipos incompatíveis e demais falhas devem continuar visíveis.
- Tornar o rollback reexecutável e seguro quando o objeto ou dado já não existir. Se a reversão não puder recuperar dados removidos, registrar claramente essa limitação.
- Não adicionar `COMMIT` incondicional sem confirmar a convenção e o mecanismo de execução adotados pelo projeto.
- Quando houver suporte aos dois bancos, entregar scripts equivalentes para Oracle e PostgreSQL e manter pares claros de aplicação e rollback.

## Validação

Revisar estaticamente os estados inicial, já aplicado, parcialmente aplicado e já revertido. Não executar em banco real sem autorização explícita. Quando houver ambiente isolado autorizado, validar nesta ordem: aplicação duas vezes, rollback duas vezes e aplicação novamente.

Ao concluir, informar o dialeto, os objetos afetados, as guardas de idempotência usadas, as limitações do rollback e o que foi ou não executado.
