---
name: aghuse-entrega-banco
description: Preparar ou revisar o pacote de scripts Oracle e PostgreSQL de uma tarefa AGHUse para entrega externa, incluindo aplicação, rollback, comentários, índices, grants, ordem e manifesto. Usar quando os scripts serão enviados ao Redmine; não adicionar scripts de implantação ao repositório AGHUse.
---

# Entrega de banco do AGHUse

Acione `aghuse_database` e aplique também `aghuse-idempotent-database-scripts`. Mantenha scripts de implantação fora do Git do AGHUse, preferencialmente em diretório temporário dedicado à tarefa.

## Revisar o pacote

- Confirmar tarefa, dialeto, schema, ambiente-alvo e ordem de execução.
- Parear aplicação e rollback idempotentes, inclusive após execução parcial.
- Exigir comentários de dicionário para novas tabelas e colunas.
- Conferir PKs, FKs, sequences, auditoria e índices sem duplicar índices ou prefixos já atendidos.
- Em Oracle, conferir `ENABLE NOVALIDATE` em novas FKs e unique constraints sobre tabelas já populadas, um índice associado para cada FK e `ONLINE` ao final de todo `CREATE INDEX`; não transportar essas cláusulas para PostgreSQL.
- Conceder somente privilégios necessários e justificar exceções.
- Não mascarar erros inesperados nem inserir `COMMIT` sem convenção confirmada.
- Usar o subcomando `banco` de `scripts/aghuse_automacao.py` para inspeção estática e `manifesto` para checksums.

## Entregar

Produzir lista ordenada de arquivos, finalidade, objetos, guardas de idempotência, limitações do rollback, achados estáticos e consultas de conferência. Nunca executar DDL ou DML em ambiente compartilhado sem autorização explícita.
