# AGHUse Assistant

O core é composto por quatro operações independentes:

- `ANALYZE`: investigação somente leitura.
- `PLAN`: estratégia técnica sem alterar o workspace.
- `IMPLEMENT`: alteração controlada do workspace.
- `VALIDATE`: build, testes, revisão e diagnóstico sem correção automática.

Cada execução é uma `OperationRun`. O Runtime cria e acompanha a Run, aplica a Policy e disponibiliza capabilities; ele não impõe uma sequência de negócio. Os únicos estados são `CREATED`, `RUNNING`, `WAITING_INPUT`, `SUCCEEDED`, `FAILED` e `CANCELLED`.

O pacote `src/aghuse_assistant/` contém as fronteiras públicas:

```text
aghuse_assistant/
├── operations/   # quatro operações
├── runtime/      # Run, Context, Dispatcher e Store
├── policy/       # permissões por operação
├── agents/       # capabilities técnicas
├── mcp/          # registro passivo de tools
├── rag/          # retrieval opcional
└── api/          # catálogo e RunService
```

Implementação é a única operação autorizada a editar arquivos ou executar mutações. RAG e MCP são sob demanda. Agents representam competência (`backend`, `database`, `frontend`, `qa`, `architecture`) e podem apoiar mais de uma operação.

`scripts/` contém somente tooling do repositório: validação, instalação, geração de artefatos e manutenção. Ele não participa do core de execução do AGHUse Assistant. O RAG fica em `src/aghuse_assistant/rag`; configurações e contratos ficam em `config/agents` e `config/contracts`; fixtures ficam em `tests/fixtures`. Novos componentes devem depender de `aghuse_assistant`, e não criar novos estados, fases ou agentes por etapa.


A API canônica é servida pelo comando ghuse-assistant-api e expõe GET /api/operations, POST /api/runs, GET /api/runs, GET /api/runs/{run_id} e POST /api/runs/{run_id}/cancel. Endpoints específicos de operação permanecem apenas como aliases de compatibilidade.
