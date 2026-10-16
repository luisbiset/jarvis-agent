def notes(files: list[str], failed_tools: list[str]) -> str:
    if not files:
        return "Nenhuma alteração observada; rollback não necessário."
    suffix = f" Ferramentas com falha: {', '.join(failed_tools)}." if failed_tools else ""
    return "Reverter somente os arquivos alterados desta execução: " + ", ".join(sorted(set(files))) + "." + suffix
