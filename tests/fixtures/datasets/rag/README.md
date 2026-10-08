# Dataset supervisionado do RAG AGHUse

Use somente exemplos fictícios ou anonimizados. O arquivo `examples.jsonl` é local e não deve ser commitado; `examples.example.jsonl` é apenas um modelo.

```bash
python scripts/aghuse_rag_dataset.py build --input tests/fixtures/datasets/rag/examples.example.jsonl --output .aghuse-assistant/rag/dataset
python scripts/train_rag_reranker.py --train .aghuse-assistant/rag/dataset/train.jsonl --output .aghuse-assistant/rag/reranker.json
```
