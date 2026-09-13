# RAG local-first do Jarvis

O RAG seleciona evidências antes da leitura aprofundada dos agentes. Ele não substitui a fonte original e não é um novo agente.

## Contexto por time

`jarvis_runtime.py retrieve --team ANALISE|DESENVOLVIMENTO|REVISAO_QUALIDADE` valida o time contra o estado e o agente, quando informado. Sem `--team`, o runtime infere pelo estado; em `NEW`, retrieval legado usa o contexto de análise. Os packs são separados por time, sem duplicar o índice compartilhado.

## Indexação

```bash
python3 scripts/jarvis_rag.py index --repo /caminho/do/repositorio
python3 scripts/jarvis_rag.py status
```

O índice padrão fica em `.jarvis/rag/index.db`, separado da telemetria. A indexação usa SHA-256: arquivos inalterados não são reprocessados; alterados invalidam apenas os próprios chunks; removidos ficam inativos. Entram somente formatos textuais permitidos. `.git`, `.jarvis`, builds, dependências, binários e arquivos secretos são ignorados. Conteúdo com credencial reconhecível é recusado antes de persistência ou embedding.

## Busca isolada

```bash
python3 scripts/jarvis_rag.py search \
  --query "agrupamento de profissionais no espelho APAC" \
  --context-budget MEDIUM
```

SQLite FTS5 é usado quando disponível. Caso contrário, a busca degrada para um fallback lexical. O modo reportado é `LEXICAL_ONLY` até existir um `EmbeddingProvider` configurado. As interfaces de provider e vector store já impedem acoplamento a SDK ou serviço externo.

## Integração ao runtime

```bash
python3 scripts/jarvis_runtime.py retrieve \
  --run-dir .jarvis/runs/<run_id> \
  --query "agrupamento de profissionais no espelho APAC" \
  --domain aghuse \
  --agent aghuse_backend
```

O runtime usa o budget `SMALL`, `MEDIUM` ou `LARGE` já escolhido pela policy de reasoning e grava `.jarvis/runs/<run_id>/context-packs/rag-context.json`. A query não é persistida em texto: somente seu SHA-256. Cada hit carrega repo, path, symbol, linhas, hash, scores e texto recuperado. Um pack só é reutilizado quando a query, o budget e os hashes das fontes continuam iguais.

Retrieval determinístico não aumenta `model_calls_used`. Estado, eventos e SQLite registram quantidade de candidatos, chunks selecionados, tokens estimados, latência e cache. Tokens são estimativa explícita de orçamento, não medição do executor.

## Confirmação e segurança

Um hit significa “recuperado”, não “confirmado”. Mudanças em faturamento, banco, segurança e contratos críticos exigem abrir a fonte original. Não configure provider externo de embeddings sem política e autorização explícitas para o corpus.

## Evals offline

Após indexar os repositórios necessários, execute:

```bash
python3 scripts/run_rag_evals.py
```

Os casos em `evals/rag-cases.json` medem Recall@K, MRR, conformidade de budget e funcionamento do fallback, sem chamada de modelo. Um caso sem a evidência esperada retorna status diferente de zero.
