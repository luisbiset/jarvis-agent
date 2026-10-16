# AGHUse Assistant

O core é composto por um Orchestrator determinístico e operações independentes:

- `ANALYZE`: investigação somente leitura.
- `PLAN`: estratégia técnica sem alterar o workspace.
- `IMPLEMENT`: alteração controlada do workspace.
- `VALIDATE`: build, testes, revisão e diagnóstico sem correção automática.
- `MANUTENCAO`: mudança controlada e isolada no próprio Assistant.

Cada execução recebe um `ExecutionContext`. O Orchestrator aplica permissões, seleciona o time e devolve um `ExecutionResult`; o Codex permanece como agente principal. Os estados são `CREATED`, `RUNNING`, `WAITING_INPUT`, `SUCCEEDED`, `FAILED` e `CANCELLED`.

O pacote `src/aghuse_assistant/` contém as fronteiras públicas:

```text
aghuse_assistant/
├── operations/   # quatro operações
├── analysis/     # engine genérico, pipeline, evidências e estratégia AGHUse
├── planning/     # plano técnico; exige AnalysisResult COMPLETE
├── implementation/ # execução mutável autorizada e rollback
├── validation/   # checks somente leitura e regressões
├── maintenance/  # manutenção assistant-only
├── orchestrator/ # contexto, estado e coordenação determinística
├── policy/       # permissões por operação
├── agents/       # capabilities técnicas
├── mcp/          # registro passivo de tools
├── teams/        # Analysis, Planning, Development, QA e Maintenance
├── gateway/      # Tool Gateway/MCP
└── app.py        # CLI do Codex
```

Implementação e manutenção confirmadas são as únicas operações autorizadas a editar arquivos. Artefatos tipados circulam pelo `ExecutionContext` sem store persistente. Todas as ferramentas passam pelo Tool Gateway; planejamento e validação aceitam somente leitura.

`scripts/` contém somente tooling do repositório: validação, instalação, geração de artefatos e manutenção. Busca de código é feita diretamente pelo Codex e pelas ferramentas MCP; configurações e contratos ficam em `config/agents` e `config/contracts`; fixtures ficam em `tests/fixtures`.
