#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
codex_home="${CODEX_HOME:-$HOME/.codex}"
marketplace_name="codex-agents"
dry_run=false

usage() {
  echo "Uso: ./scripts/install.sh [--dry-run] [--copy-agents]"
}

run() {
  if [[ "$dry_run" == true ]]; then
    printf 'DRY-RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=true
      ;;
    --copy-agents)
      # Compatibilidade com chamadas antigas. Agentes agora são sempre copiados.
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
  shift
done

python3 "$project_root/scripts/validate.py"
run mkdir -p "$codex_home/agents"

global_instructions_source="$project_root/config/AGENTS.md"
global_instructions_destination="$codex_home/AGENTS.md"
if [[ ! -e "$global_instructions_destination" ]] || grep -q "managed-by: jarvis-agent" "$global_instructions_destination"; then
  run cp -f --remove-destination "$global_instructions_source" "$global_instructions_destination"
else
  echo "ERRO: $global_instructions_destination já existe e não é gerenciado pelo Jarvis Agent." >&2
  echo "Mescle config/AGENTS.md manualmente para preservar suas instruções globais." >&2
  exit 1
fi
if [[ "$dry_run" == true ]]; then
  printf 'DRY-RUN: gravar %q em %q\n' "$project_root" "$codex_home/jarvis-agent-root"
else
  printf '%s\n' "$project_root" > "$codex_home/jarvis-agent-root"
fi

for agent in "$project_root"/agents/*.toml; do
  destination="$codex_home/agents/$(basename "$agent")"
  run cp -f --remove-destination "$agent" "$destination"
done

if ! codex plugin marketplace list | grep -q "^$marketplace_name[[:space:]]"; then
  run codex plugin marketplace add "$project_root"
fi

for plugin in redmine-agent sfa-agent aghuse-agent; do
  run codex plugin add "$plugin@$marketplace_name"
done

if [[ "$dry_run" == true ]]; then
  echo "Simulação concluída; nenhuma instalação foi alterada."
else
  echo "Instalação central concluída. Abra uma conversa nova para carregar agentes e skills atualizados."
fi
