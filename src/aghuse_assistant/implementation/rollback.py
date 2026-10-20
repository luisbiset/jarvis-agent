def notes(files: list[str], failed_tools: list[str], rollback_failures: list[str]) -> str:
    if not files:
        return "Nenhuma alteração pendente; rollback não necessário."
    if rollback_failures:
        return "Rollback incompleto para os arquivos: " + ", ".join(sorted(set(files))) + ". Falhas: " + "; ".join(rollback_failures) + "."
    if failed_tools:
        return "Rollback executado após falha de: " + ", ".join(failed_tools) + "."
    return "Rollback disponível para os arquivos alterados desta execução: " + ", ".join(sorted(set(files))) + "."
