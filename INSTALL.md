# Guia de instalação do Jarvis Agent

Este guia instala globalmente os agentes, skills e plugins do Jarvis Agent no Codex. A instalação não altera os repositórios do SFA ou do AGHUse.

## 1. Pré-requisitos

Ambiente recomendado: Linux, macOS ou Windows com WSL e Bash.

Instale e valide:

- Git;
- Python 3.11 ou superior;
- Node.js 18 ou superior;
- Codex com suporte ao comando `plugin`;
- acesso SSH ou HTTPS ao repositório.

```bash
git --version
python3 --version
node --version
codex --version
codex plugin --help
```

Se `codex plugin --help` não funcionar, atualize o Codex antes de continuar.

## 2. Clonar o projeto

Com SSH:

```bash
git clone git@github.com:luisbiset/jarvis-agent.git
cd jarvis-agent
```

Ou com HTTPS:

```bash
git clone https://github.com/luisbiset/jarvis-agent.git
cd jarvis-agent
```

## 3. Preparar a integração com o Redmine

O arquivo real do MCP é local e ignorado pelo Git. Crie-o a partir do modelo:

```bash
cp plugins/redmine-agent/.mcp.json.example plugins/redmine-agent/.mcp.json
```

Abra `plugins/redmine-agent/.mcp.json` e configure somente a URL do seu Redmine. Para a SESAB:

```json
"REDMINE_URL": "https://redmine.saude.ba.gov.br/"
```

Não grave a chave da API nesse arquivo. O servidor lê a chave exclusivamente da variável de ambiente `REDMINE_API_KEY`.

Para testar na sessão atual sem registrar a chave no histórico do terminal:

```bash
read -rsp "Chave da API do Redmine: " REDMINE_API_KEY
echo
export REDMINE_API_KEY
```

Para uso permanente, configure `REDMINE_API_KEY` no gerenciador de segredos do sistema ou em um arquivo de inicialização protegido. A variável precisa existir no ambiente que inicia o VS Code ou o Codex. Nunca envie a chave em conversas, commits, capturas de tela ou arquivos do projeto.

### MCP Redmine global

Para disponibilizar o Redmine em qualquer projeto e permitir a verificação do `doctor.py`, adicione a configuração abaixo em `~/.codex/config.toml`, trocando o caminho pelo caminho absoluto do seu clone:

```toml
[mcp_servers.redmine]
command = "node"
args = ["/CAMINHO/ABSOLUTO/jarvis-agent/plugins/redmine-agent/scripts/server.mjs"]
env_vars = ["REDMINE_API_KEY"]
default_tools_approval_mode = "writes"
enabled = true
```

Descubra o caminho absoluto estando na raiz do clone:

```bash
pwd
```

## 4. Validar antes de instalar

```bash
python3 scripts/validate.py
./scripts/install.sh --dry-run
```

O primeiro comando valida plugins, agentes, skills, avaliações e segredos literais. O segundo mostra as ações de instalação sem alterar o Codex.

## 5. Instalar

Instalação recomendada para uma máquina de desenvolvimento:

```bash
./scripts/install.sh
```

O instalador:

1. valida o projeto;
2. registra o marketplace local `codex-agents`;
3. instala os quatro plugins;
4. cria os agentes globais em `~/.codex/agents/`;
5. copia cada agente como um arquivo TOML independente, compatível com o carregador de subagentes do Codex.

O argumento legado continua aceito para compatibilidade, mas produz o mesmo resultado da instalação padrão:

```bash
./scripts/install.sh --copy-agents
```

Execute o instalador novamente após cada atualização para copiar as versões novas dos agentes.

## 6. Reiniciar e verificar

Feche e reabra o Codex ou recarregue a janela do VS Code. Depois, na raiz do Jarvis Agent, execute:

```bash
python3 scripts/doctor.py --strict
codex plugin list
```

O diagnóstico saudável confirma:

- 16 agentes globais;
- os plugins `redmine-agent`, `sfa-agent` e `aghuse-agent`;
- o MCP Redmine apontando para este clone;
- a presença de `REDMINE_API_KEY` sem exibir seu valor;
- ausência de instalações legadas conflitantes.

Validação adicional opcional:

```bash
python3 scripts/smoke_install.py
node plugins/redmine-agent/scripts/server.mjs --self-test
python3 scripts/run_evals.py
python3 scripts/run_evals.py --canary
```

## 7. Testar no Codex

Abra uma conversa nova e experimente:

```text
Quais skills e agentes estão disponíveis?
```

```text
Liste meus chamados abertos no Redmine.
```

```text
Use `$aghuse-development` para analisar e conduzir a tarefa 51093 no AGHUse.
```

Consultas ao Redmine podem ser executadas diretamente. Alterações de chamado, comentários e lançamentos de horas devem pedir confirmação antes da escrita.

## 8. Atualizar a instalação

```bash
cd /caminho/do/jarvis-agent
git pull --ff-only
./scripts/install.sh
python3 scripts/doctor.py --strict
```

Depois, abra uma conversa nova para carregar as versões atualizadas.

## 9. Instalação manual

Se o instalador não puder ser usado:

```bash
mkdir -p ~/.codex/agents
cp agents/*.toml ~/.codex/agents/

codex plugin marketplace add "$PWD"
codex plugin add redmine-agent@codex-agents
codex plugin add sfa-agent@codex-agents
codex plugin add aghuse-agent@codex-agents
```

## 10. Solução de problemas

### `REDMINE_API_KEY` não está disponível

Confirme apenas a presença da variável, sem imprimir o valor:

```bash
test -n "${REDMINE_API_KEY:-}" && echo "configurada" || echo "ausente"
```

Se estiver ausente, configure a variável e inicie novamente o VS Code ou o Codex a partir desse ambiente.

### MCP Redmine aponta para outro diretório

Atualize `args` em `~/.codex/config.toml` com o caminho absoluto do clone atual e recarregue o Codex.

### Plugin não aparece

```bash
codex plugin marketplace list
codex plugin list
./scripts/install.sh
```

Abra uma conversa nova depois da reinstalação.

### Agente global não foi atualizado

Execute o instalador novamente e confirme que os perfis são arquivos regulares, não links simbólicos:

```bash
find ~/.codex/agents -maxdepth 1 -type f -name '*.toml' -print
```

### Instalação antiga ou duplicada

Execute:

```bash
python3 scripts/doctor.py --strict
```

O diagnóstico informa plugins e skills legados que precisam ser removidos antes de uma instalação limpa.

## Segurança

- `plugins/redmine-agent/.mcp.json` nunca deve ser versionado;
- `REDMINE_API_KEY` nunca deve aparecer em arquivos do projeto;
- não copie agentes para repositórios corporativos sem autorização;
- revise comandos de escrita no Redmine antes de confirmar;
- mantenha o clone e o Codex atualizados.

O formato dos plugins segue a [documentação oficial de empacotamento de plugins da OpenAI](https://developers.openai.com/plugins/build/plugins).
