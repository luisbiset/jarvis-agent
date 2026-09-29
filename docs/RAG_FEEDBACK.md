# Aprendizado assistido do RAG

O RAG não aprende diretamente durante o uso. O feedback entra como `PENDING` e só participa do treinamento após aprovação humana.

```bash
python scripts/aghuse_rag_feedback.py add --query "regra de conta" --path "src/ContaON.java" --layer backend --artifact codigo --relevant --reason "regra de negócio"
python scripts/aghuse_rag_feedback.py list
python scripts/aghuse_rag_feedback.py approve --id fb-XXXX
python scripts/aghuse_rag_feedback.py export --output .jarvis/rag/approved.jsonl
python scripts/aghuse_rag_dataset.py build --input .jarvis/rag/approved.jsonl --output .jarvis/rag/dataset
python scripts/train_rag_reranker.py --train .jarvis/rag/dataset/train.jsonl --output .jarvis/rag/reranker.json
python scripts/train_taxonomy_classifier.py --input .jarvis/rag/approved.jsonl --output .jarvis/rag/taxonomy.json
python scripts/jarvis_rag.py index --repo /caminho/do/aghuse --taxonomy-model .jarvis/rag/taxonomy.json
```

Feedback pendente, aprovado e modelos ficam em `.jarvis/`, que é local e ignorado pelo Git.
