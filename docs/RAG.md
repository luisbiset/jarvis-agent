# RAG local-first do Jarvis

O RAG seleciona evidÃªncias antes da leitura aprofundada dos agentes. Ele nÃ£o substitui a fonte original e nÃ£o Ã© um novo agente. A recuperaÃ§Ã£o pode usar reranker local e taxonomia AGHUse; o aprendizado Ã© assistido e exige aprovaÃ§Ã£o humana.

## Contexto por time

`jarvis_runtime.py retrieve --team ANALISE|DESENVOLVIMENTO|REVISAO_QUALIDADE` valida o time contra o estado e o agente, quando informado. Sem `--team`, o runtime infere pelo estado; em `NEW`, retrieval legado usa o contexto de anÃ¡lise. Os packs sÃ£o separados por time, sem duplicar o Ã­ndice compartilhado.

## IndexaÃ§Ã£o

```bash
python3 scripts/jarvis_rag.py index --repo /caminho/do/repositorio
python3 scripts/jarvis_rag.py status
```

O Ã­ndice padrÃ£o fica em `.jarvis/rag/index.db`, separado da telemetria. A indexaÃ§Ã£o usa SHA-256: arquivos inalterados nÃ£o sÃ£o reprocessados; alterados invalidam apenas os prÃ³prios chunks; removidos ficam inativos. Entram somente formatos textuais permitidos. `.git`, `.jarvis`, builds, dependÃªncias, binÃ¡rios e arquivos secretos sÃ£o ignorados. ConteÃºdo com credencial reconhecÃ­vel Ã© recusado antes de persistÃªncia ou embedding.

## Busca isolada

```bash
python3 scripts/jarvis_rag.py search \
  --query "agrupamento de profissionais no espelho APAC" \
  --context-budget MEDIUM
```

SQLite FTS5 Ã© usado quando disponÃ­vel. Caso contrÃ¡rio, a busca degrada para um fallback lexical. O modo reportado Ã© `LEXICAL_ONLY` atÃ© existir um `EmbeddingProvider` configurado. As interfaces de provider e vector store jÃ¡ impedem acoplamento a SDK ou serviÃ§o externo.

## Taxonomia, reranker e feedback

As camadas principais sÃ£o `backend`, `frontend`, `banco`, `testes`, `seguranca` e `documentacao`. Para usar classificaÃ§Ã£o e reranker local:

```bash
python3 scripts/jarvis_rag.py index --repo /caminho/do/repositorio --taxonomy-model .jarvis/rag/taxonomy.json
python3 scripts/jarvis_rag.py search --query "regra de negÃ³cio" --reranker .jarvis/rag/reranker.json --taxonomy layer=backend
```

CorreÃ§Ãµes podem ser registradas pelo fluxo de [RAG_FEEDBACK.md](RAG_FEEDBACK.md), mas sÃ³ feedback aprovado entra no treino. O manual completo estÃ¡ em [MANUAL_TREINO_RAG_AGHUSE.md](MANUAL_TREINO_RAG_AGHUSE.md).

## IntegraÃ§Ã£o ao runtime

```bash
python3 scripts/jarvis_runtime.py retrieve \
  --run-dir .jarvis/runs/<run_id> \
  --query "agrupamento de profissionais no espelho APAC" \
  --domain aghuse \
  --agent aghuse_backend
```

O runtime usa o budget `SMALL`, `MEDIUM` ou `LARGE` jÃ¡ escolhido pela policy de reasoning e grava `.jarvis/runs/<run_id>/context-packs/rag-context.json`. A query nÃ£o Ã© persistida em texto: somente seu SHA-256. Cada hit carrega repo, path, symbol, linhas, hash, scores e texto recuperado. Um pack sÃ³ Ã© reutilizado quando a query, o budget e os hashes das fontes continuam iguais.

Retrieval determinÃ­stico nÃ£o aumenta `model_calls_used`. Estado, eventos e SQLite registram quantidade de candidatos, chunks selecionados, tokens estimados, latÃªncia e cache. Tokens sÃ£o estimativa explÃ­cita de orÃ§amento, nÃ£o mediÃ§Ã£o do executor.

## ConfirmaÃ§Ã£o e seguranÃ§a

Um hit significa â€œrecuperadoâ€, nÃ£o â€œconfirmadoâ€. MudanÃ§as em faturamento, banco, seguranÃ§a e contratos crÃ­ticos exigem abrir a fonte original. NÃ£o configure provider externo de embeddings sem polÃ­tica e autorizaÃ§Ã£o explÃ­citas para o corpus.

## Evals offline

ApÃ³s indexar os repositÃ³rios necessÃ¡rios, execute:

```bash
python3 scripts/run_rag_evals.py
```

Os casos em `evals/rag-cases.json` medem Recall@K, MRR, conformidade de budget e funcionamento do fallback, sem chamada de modelo. Um caso sem a evidÃªncia esperada retorna status diferente de zero.

