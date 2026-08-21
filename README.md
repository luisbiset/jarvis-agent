# Codex Agents

Projeto-fonte dos agentes pessoais usados no Codex.

## Estrutura

- `plugins/redmine-agent/`: plugin de integração e workflows do Redmine.
- `plugins/sfa-agent/`: coordenador de desenvolvimento do SFA.
- `agents/sfa_frontend.toml`: especialista Angular do SFA.
- `agents/sfa_backend.toml`: especialista Java/Spring do SFA.
- `agents/sfa_database.toml`: especialista Oracle/PostgreSQL do SFA.
- `.agents/plugins/marketplace.json`: marketplace local deste projeto.

## Segurança

O arquivo `plugins/redmine-agent/.mcp.json` é local e ignorado pelo Git porque contém configuração de ambiente. Use `.mcp.json.example` como modelo. A chave do Redmine deve existir somente na variável `REDMINE_API_KEY`; nunca a grave neste repositório.

## Instalação dos plugins

Na raiz deste projeto:

```bash
codex plugin marketplace add "$PWD"
codex plugin add redmine-agent@codex-agents
codex plugin add sfa-agent@codex-agents
```

## Instalação dos subagentes

Os arquivos TOML podem ser copiados para `.codex/agents/` de um projeto ou para `~/.codex/agents/` quando devem ficar disponíveis globalmente. O repositório SFA mantém cópias em sua própria `.codex/agents/` para que outros desenvolvedores recebam os perfis junto do código.

Depois de alterar um plugin, valide-o, atualize o cachebuster e reinstale-o antes de testar em uma conversa nova.

