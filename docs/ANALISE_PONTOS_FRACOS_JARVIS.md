# Análise dos pontos fracos do Jarvis

Data da análise: 2026-09-29  
Escopo: runtime, RAG local, taxonomia, feedback, treinamento, telemetria e operação.

## Resumo executivo

O Jarvis possui uma base funcional intermediária: runtime com policy engine, telemetria, RAG local, taxonomia, reranker, feedback supervisionado e treinamento sem GPU.

O principal limite atual é que a automação ainda é orientada por comandos. O RAG gera contexto e sugestões, mas não está conectado como um interceptor real do canal de conversa. Além disso, a taxonomia é predominantemente heurística e o pipeline de treinamento ainda não mede qualidade suficiente antes de promover um modelo.

## Pontos críticos

### 1. O RAG não intercepta realmente o chat

O projeto possui `scripts/jarvis_chat_rag.py` e uma orientação no `AGENTS.md`, mas a consulta ainda depende da execução do script pelo agente. Não existe um middleware ou hook real no canal de conversa.

Impacto: alto. Uma tarefa pode ser respondida sem consulta ao RAG caso a ponte não seja chamada.

Correção recomendada: integrar a consulta ao ciclo obrigatório de recebimento da mensagem, antes do planejamento da tarefa.

### 2. Recuperação predominantemente lexical

O mecanismo atual usa FTS5, termos, símbolos, caminhos e reranking por pesos de termos. O campo `semantic_score` permanece sem uso efetivo.

Impacto: alto. Paráfrases, sinônimos e relações semânticas podem não recuperar o documento correto.

Correção recomendada: adicionar embeddings locais opcionais e manter o fallback lexical para ambientes sem GPU.

### 3. Falsos positivos na taxonomia

A classificação atual usa heurísticas de caminho e conteúdo. Termos genéricos como `on`, `config` e `security` podem classificar documentação ou configuração como componentes AGHUse.

Impacto: alto. Filtros taxonômicos podem restringir a busca de maneira incorreta.

Correção recomendada: exigir padrões de identificador e contexto estrutural, diferenciando `ContaON.java` de ocorrências da palavra `on` em texto livre.

### 4. As 14 novas categorias ainda não são treináveis

O classificador supervisionado treina atualmente apenas `layer` e `artifact`. As categorias `ON`, `RN`, `EJB`, `Facade`, `DAO`, `Entity`, `XHTML`, `Controller`, `Service`, `Test`, `SQL`, `Security`, `Message` e `Configuration` são classificadas por heurística.

Impacto: alto. O feedback não consegue melhorar diretamente essas categorias.

Correção recomendada: transformar as categorias em campo supervisionado multilabel e treinar/avaliar seus classificadores.

### 5. Promoção de modelo sem avaliação comparativa

O pipeline exige exemplos aprovados e separa treino/validação, mas ainda não compara o modelo novo com o modelo ativo usando métricas de recuperação.

Impacto: alto. Um modelo pior pode ser promovido se o dataset tiver estrutura válida.

Correção recomendada: bloquear promoção quando não houver ganho mínimo em Recall@K, MRR e conformidade de orçamento.

### 6. Contrato incompleto do feedback automático

Sugestões automáticas são criadas com `relevant: null`. O treinamento exige `relevant: true` ou `false`, enquanto a aprovação atual apenas altera o status para `APPROVED`.

Impacto: crítico. Um feedback aprovado pode gerar dataset inválido ou interromper o treinamento.

Correção recomendada: exigir uma decisão explícita de relevância na aprovação, por exemplo `approve --relevant` ou `reject`.

## Pontos importantes

### 7. Explicação de seleção limitada

O RAG informa razões básicas, como `query_term_in_path` e `query_term_in_content`, mas não detalha a contribuição de cada componente do score nem os motivos de descarte por orçamento.

### 8. Consulta textual no feedback

O contexto principal preserva apenas o hash da consulta, mas o arquivo de feedback contém a consulta em texto. O filtro cobre credenciais conhecidas, mas não todos os dados pessoais, clínicos ou internos possíveis.

### 9. Ausência de confirmação de uso pelo modelo

O sistema registra o contexto recuperado, mas não confirma quais trechos foram efetivamente lidos ou utilizados pelo modelo na resposta final.

### 10. Invalidação de cache limitada

O cache considera consulta, filtros, orçamento e hashes das fontes. Alterações na lógica de ranking, taxonomia ou versão do classificador deveriam também invalidar packs antigos.

### 11. Mistura de fontes no índice

Código, testes, documentação, configurações, agentes TOML e contratos podem concorrer na mesma busca. Sem priorização por tipo de fonte, instruções do próprio Jarvis podem superar o código de negócio.

### 12. Isolamento de índice insuficiente

Embora o hit registre repositório, caminho e branch disponível no indexador, ainda falta uma política operacional forte para separar projetos, branches e commits em índices ou namespaces confiáveis.

### 13. Ruído na geração de feedback

A criação automática de um feedback por hit pode gerar muitas sugestões irrelevantes para uma única tarefa e contaminar a revisão humana.

### 14. Cobertura de testes incompleta para as novas automações

A suíte validada possui 56 testes, mas ainda faltam testes end-to-end para ponte de chat, aprovação de feedback automático, pipeline de promoção, rollback e acionamento automático completo no início de uma tarefa.

### 15. Ausência de worker de aprendizado

O treinamento automatizado ainda depende de comando manual. Não há fila persistente, agendamento, retry controlado ou painel de modelos candidatos.

## Priorização recomendada

| Prioridade | Melhoria | Impacto |
|---|---|---|
| P0 | Corrigir aprovação com valor explícito de relevância | Crítico |
| P1 | Avaliar modelo novo contra o modelo ativo antes da promoção | Alto |
| P2 | Integrar RAG ao interceptor real de mensagens | Alto |
| P3 | Reduzir falsos positivos da taxonomia | Alto |
| P4 | Tornar as 14 categorias treináveis | Alto |
| P5 | Adicionar embeddings locais opcionais | Alto |
| P6 | Criar testes end-to-end e rollback | Alto |
| P7 | Isolar índices por projeto/branch/commit | Médio |
| P8 | Criar worker e fila de aprendizado | Médio |

## Evidências de validação

- `python scripts/validate.py`: aprovado.
- Suíte local: 56 testes aprovados na última validação.
- O RAG atual informa origem, linhas, hashes, scores, taxonomia e razões básicas de seleção.
- O pipeline local não promoveu modelo novo por ausência de feedback aprovado suficiente.

## Conclusão

O Jarvis já possui os componentes fundamentais, mas ainda opera como uma plataforma local assistida, não como um sistema autônomo de aprendizado contínuo. A prioridade deve ser corrigir o contrato de feedback e criar uma avaliação objetiva de modelos antes de ampliar a automação.
