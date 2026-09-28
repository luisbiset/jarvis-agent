# Dataset supervisionado do RAG AGHUse

Use somente exemplos fictícios ou anonimizados. O arquivo `examples.jsonl` é local e não deve ser commitado; `examples.example.jsonl` é apenas um modelo.

```bash
python scripts/aghuse_rag_dataset.py build --input datasets/rag/examples.example.jsonl --output .jarvis/rag/dataset
python scripts/train_rag_reranker.py --train .jarvis/rag/dataset/train.jsonl --output .jarvis/rag/reranker.json
```
