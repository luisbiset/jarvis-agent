# Manual de treinamento do RAG AGHUse

Este manual descreve como evoluir o RAG local do AGHUse com feedback supervisionado. O processo não treina automaticamente sem aprovação humana.

## Visão geral

```text
consulta → resultado do RAG → feedback PENDING
                              ↓
                    aprovação humana
                              ↓
                    dataset aprovado
                              ↓
             reranker + classificador de taxonomia
                              ↓
                         reindexação
```

O treinamento atual é local, determinístico e baseado em pesos de termos. Não exige GPU, API externa ou modelo hospedado.

## 1. Pré-requisitos

Execute a partir da raiz do repositório:

```bash
python scripts/validate.py
python -m unittest tests.test_rag
```

O diretório `.jarvis/` é local e ignorado pelo Git. Ele armazena índice, feedback aprovado e modelos treinados.

## 2. Registrar feedback

Cada feedback deve indicar se o candidato recuperado é relevante e sua taxonomia:

```bash
python scripts/aghuse_rag_feedback.py add \
  --query "alterar regra de cálculo da conta" \
  --path "modulo/src/main/java/exemplo/ContaON.java" \
  --symbol calcular \
  --layer backend \
  --artifact codigo \
  --relevant \
  --reason "contém a regra de negócio"
```

Para um resultado incorreto, omita `--relevant`:

```bash
python scripts/aghuse_rag_feedback.py add \
  --query "alterar regra de cálculo da conta" \
  --path "modulo/src/main/webapp/conta.xhtml" \
  --layer frontend \
  --artifact tela \
  --reason "é a tela, não a regra de negócio"
```

O comando gera um identificador `fb-...` e grava o item como `PENDING`.

## 3. Revisar e aprovar

Liste os registros pendentes:

```bash
python scripts/aghuse_rag_feedback.py list
```

Revise query, caminho, símbolo, relevância e justificativa. Aprove somente exemplos corretos:

```bash
python scripts/aghuse_rag_feedback.py approve --id fb-XXXXXXXXXXXX
```

Não aprove exemplos com código de produção sem autorização, dados de pacientes, faturamento real, credenciais, tokens, URLs privadas ou identificadores pessoais.

## 4. Exportar o dataset aprovado

```bash
python scripts/aghuse_rag_feedback.py export \
  --output .jarvis/rag/approved.jsonl
```

O exportador inclui somente registros `APPROVED`. Em seguida, valide e separe treino/validação:

```bash
python scripts/aghuse_rag_dataset.py build \
  --input .jarvis/rag/approved.jsonl \
  --output .jarvis/rag/dataset
```

O manifesto registra quantidade de exemplos e hash do arquivo de entrada.

## 5. Treinar o reranker

O reranker aprende pesos de termos que ajudam a distinguir candidatos relevantes de irrelevantes:

```bash
python scripts/train_rag_reranker.py \
  --train .jarvis/rag/dataset/train.jsonl \
  --output .jarvis/rag/reranker.json
```

Esse modelo reordena os candidatos depois da busca lexical. Ele não gera texto nem altera os documentos originais.

## 6. Treinar a classificação taxonômica

```bash
python scripts/train_taxonomy_classifier.py \
  --input .jarvis/rag/approved.jsonl \
  --output .jarvis/rag/taxonomy.json
```

Os rótulos atuais são:

- camadas: `backend`, `frontend`, `banco`, `testes`, `seguranca`, `documentacao`;
- artefatos: `codigo`, `tela`, `script_banco`, `teste`, `documento`.

## 7. Reindexar o AGHUse

```bash
python scripts/jarvis_rag.py index \
  --repo /caminho/do/aghuse \
  --source-type CODE \
  --taxonomy-model .jarvis/rag/taxonomy.json
```

Para consultar usando o reranker e um filtro taxonômico:

```bash
python scripts/jarvis_rag.py search \
  --query "alterar regra de cálculo" \
  --reranker .jarvis/rag/reranker.json \
  --taxonomy layer=backend \
  --context-budget MEDIUM
```

Se o reranker não for informado, a busca continua funcionando no modo lexical.

## 8. Avaliar antes de promover

Execute os testes e os evals offline:

```bash
python -m unittest tests.test_rag
python scripts/run_rag_evals.py
python scripts/validate.py
```

Compare recall@k e MRR com a versão anterior. Não substitua um modelo funcionando por outro com piora sem registrar a decisão.

## 9. Boas práticas do dataset

- Use pares positivos e negativos para a mesma consulta.
- Varie sinônimos e formas reais de pedir a mesma tarefa.
- Inclua backend, frontend, banco, testes e segurança.
- Prefira caminhos e símbolos estáveis a trechos longos de código.
- Não use dados clínicos, faturamento real ou credenciais.
- Separe consultas de treino e validação.
- Não aprove automaticamente o feedback coletado.
- Registre uma justificativa curta e verificável para cada rótulo.

## 10. Troubleshooting

`dataset precisa conter consultas suficientes`: adicione exemplos com consultas diferentes para que a divisão determinística produza treino e validação.

`feedback contém conteúdo não permitido`: remova credenciais, tokens, URLs ou conteúdo sensível; o bloqueio é intencional.

`reranker incompatível`: gere novamente o modelo com `train_rag_reranker.py`.

Resultados ruins: aumente exemplos negativos difíceis, revise os rótulos e reexecute os evals. Não aumente o top-k como substituto para dados mal rotulados.
