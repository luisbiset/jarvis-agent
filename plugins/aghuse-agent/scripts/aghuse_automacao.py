#!/usr/bin/env python3
"""Automações locais e somente leitura para o ciclo de tarefas do AGHUse."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

TAREFA_RE = re.compile(r"(?<!\d)(\d{4,7})(?!\d)")
SEGURANCA_RE = re.compile(
    r"Usuario\s*=\s*(?P<usuario>[^,]+),\s*Pagina\s*=\s*(?P<pagina>[^,]+),\s*Metodo\s*=\s*(?P<metodo>[^\s,]+)",
    re.IGNORECASE,
)
EXCECAO_RE = re.compile(r"(?:Caused by:\s*)?([\w.$]+(?:Exception|Error)(?::\s*.*)?)")
CLASSE_AGHU_RE = re.compile(r"(?:at\s+)?(br\.gov\.mec\.aghu\.[\w.$]+)")
ORA_RE = re.compile(r"ORA-\d{5}")


class FalhaAutomacao(RuntimeError):
    """Falha previsível apresentada sem stack trace ao usuário."""


def executar_git(raiz: Path, *argumentos: str, aceitar_falha: bool = False) -> str:
    resultado = subprocess.run(
        ["git", *argumentos],
        cwd=raiz,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if resultado.returncode and not aceitar_falha:
        detalhe = resultado.stderr.strip() or resultado.stdout.strip() or "comando Git falhou"
        raise FalhaAutomacao(detalhe)
    return resultado.stdout.rstrip("\n")


def raiz_git(caminho: Path) -> Path:
    caminho = caminho.resolve()
    topo = executar_git(caminho, "rev-parse", "--show-toplevel")
    return Path(topo)


def raiz_aghuse(caminho: Path) -> Path:
    caminho = caminho.resolve()
    candidatos = (caminho, caminho / "aghuse")
    for candidato in candidatos:
        if (candidato / "aghu" / "pom.xml").is_file() and (candidato / "aghu-entidades" / "pom.xml").is_file():
            return raiz_git(candidato)
    try:
        topo = raiz_git(caminho)
    except FalhaAutomacao:
        topo = None
    if topo and (topo / "aghu" / "pom.xml").is_file() and (topo / "aghu-entidades" / "pom.xml").is_file():
        return topo
    raise FalhaAutomacao("não foi localizada uma raiz AGHUse com aghu/pom.xml e aghu-entidades/pom.xml")


def extrair_tarefas(*textos: str) -> list[str]:
    return sorted({numero for texto in textos for numero in TAREFA_RE.findall(texto or "")})


def arquivos_alterados(raiz: Path) -> list[str]:
    linhas = executar_git(raiz, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    arquivos: list[str] = []
    for linha in linhas:
        if len(linha) < 4:
            continue
        caminho = linha[3:]
        if " -> " in caminho:
            caminho = caminho.split(" -> ", 1)[1]
        arquivos.append(caminho)
    return sorted(set(arquivos))


def contexto_repositorio(raiz: Path) -> dict:
    raiz = raiz_aghuse(raiz)
    branch = executar_git(raiz, "branch", "--show-current") or "HEAD destacado"
    head = executar_git(raiz, "rev-parse", "--short=12", "HEAD")
    assuntos = executar_git(raiz, "log", "-20", "--pretty=%s", aceitar_falha=True).splitlines()
    alterados = arquivos_alterados(raiz)
    return {
        "raiz": str(raiz),
        "branch": branch,
        "head": head,
        "tarefas_candidatas": extrair_tarefas(branch, *assuntos),
        "arquivos_alterados": alterados,
        "quantidade_alterada": len(alterados),
        "worktree_limpa": not alterados,
    }


def modulo_de_arquivo(arquivo: str) -> str:
    partes = Path(arquivo).parts
    if not partes:
        return "desconhecido"
    if partes[0] == "aghu-entidades":
        return "aghu-entidades"
    if partes[0] == "aghu" and len(partes) == 2 and partes[1] == "pom.xml":
        return "aghu"
    if partes[0] == "aghu" and len(partes) > 1:
        return partes[1]
    return partes[0]


def mapear_modulos(arquivos: list[str]) -> dict:
    por_modulo: dict[str, list[str]] = {}
    tipos: Counter[str] = Counter()
    for arquivo in sorted(set(arquivos)):
        por_modulo.setdefault(modulo_de_arquivo(arquivo), []).append(arquivo)
        sufixo = Path(arquivo).suffix.lower() or "sem_extensao"
        tipos[sufixo] += 1
    return {
        "modulos": por_modulo,
        "tipos": dict(sorted(tipos.items())),
        "possui_entidades": "aghu-entidades" in por_modulo,
        "possui_xhtml": tipos[".xhtml"] > 0,
        "possui_java": tipos[".java"] > 0,
        "possui_mensagens": tipos[".properties"] > 0,
        "possui_sql": tipos[".sql"] > 0,
    }


def historico_git(raiz: Path, termo: str, limite: int) -> dict:
    raiz = raiz_aghuse(raiz)
    formato = "%H%x1f%ad%x1f%an%x1f%s"
    saida = executar_git(
        raiz,
        "log",
        "--all",
        f"--max-count={limite}",
        "--date=iso-strict",
        f"--pretty=format:{formato}",
        "--regexp-ignore-case",
        f"--grep={termo}",
        aceitar_falha=True,
    )
    commits = []
    for linha in saida.splitlines():
        campos = linha.split("\x1f", 3)
        if len(campos) == 4:
            commits.append(dict(zip(("commit", "data", "autor", "assunto"), campos)))
    return {"termo": termo, "commits": commits, "quantidade": len(commits)}


def ler_texto(caminho: Path) -> tuple[str, str]:
    dados = caminho.read_bytes()
    for codificacao in ("utf-8-sig", "utf-8"):
        try:
            return dados.decode(codificacao), codificacao
        except UnicodeDecodeError:
            pass
    return dados.decode("latin-1"), "latin-1"


def analisar_mensagens(caminhos: list[Path]) -> dict:
    resultados = []
    for caminho in caminhos:
        texto, codificacao = ler_texto(caminho)
        chaves: list[str] = []
        for linha in texto.splitlines():
            limpa = linha.strip()
            if not limpa or limpa.startswith(("#", "!")):
                continue
            separador = re.search(r"(?<!\\)[:=]", limpa)
            if separador:
                chaves.append(limpa[: separador.start()].strip())
        contagem = Counter(chaves)
        resultados.append(
            {
                "arquivo": str(caminho),
                "codificacao": codificacao,
                "quantidade_chaves": len(chaves),
                "duplicadas": sorted(chave for chave, total in contagem.items() if total > 1),
            }
        )
    return {"arquivos": resultados, "possui_duplicacoes": any(item["duplicadas"] for item in resultados)}


def analisar_sql(caminhos: list[Path]) -> dict:
    resultados = []
    for caminho in caminhos:
        texto, codificacao = ler_texto(caminho)
        superior = texto.upper()
        objetos = {
            "tabelas": sorted(set(re.findall(r"\bCREATE\s+TABLE\s+([\w.$\"]+)", superior))),
            "sequences": sorted(set(re.findall(r"\bCREATE\s+SEQUENCE\s+([\w.$\"]+)", superior))),
            "indices": sorted(set(re.findall(r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+([\w.$\"]+)", superior))),
        }
        cria_estrutura = bool(objetos["tabelas"] or objetos["sequences"])
        achados = []
        if objetos["tabelas"] and "COMMENT ON TABLE" not in superior:
            achados.append("nova tabela sem COMMENT ON TABLE detectável")
        if objetos["tabelas"] and "COMMENT ON COLUMN" not in superior:
            achados.append("nova tabela sem COMMENT ON COLUMN detectável")
        if cria_estrutura and "GRANT " not in superior:
            achados.append("estrutura criada sem GRANT detectável; confirmar necessidade")
        if re.search(r"(^|\s)COMMIT\s*;", superior):
            achados.append("COMMIT explícito; confirmar convenção de execução")
        guardas = {
            "oracle_catalogo": bool(re.search(r"\b(?:ALL|USER)_(?:TABLES|SEQUENCES|INDEXES|OBJECTS)\b", superior)),
            "postgres_if_exists": "IF EXISTS" in superior or "IF NOT EXISTS" in superior,
            "bloco_condicional": "EXECUTE IMMEDIATE" in superior or "DO $$" in superior,
        }
        resultados.append(
            {
                "arquivo": str(caminho),
                "codificacao": codificacao,
                "objetos": objetos,
                "possui_grant": "GRANT " in superior,
                "possui_comentarios_dicionario": "COMMENT ON " in superior,
                "guardas_idempotencia": guardas,
                "achados": achados,
            }
        )
    return {"arquivos": resultados, "quantidade_achados": sum(len(item["achados"]) for item in resultados)}


def obter_entrada(arquivo: Path | None) -> str:
    if arquivo:
        return ler_texto(arquivo)[0]
    if sys.stdin.isatty():
        raise FalhaAutomacao("informe --arquivo ou envie o conteúdo pela entrada padrão")
    return sys.stdin.read()


def analisar_seguranca(texto: str) -> dict:
    ocorrencias = []
    for correspondencia in SEGURANCA_RE.finditer(texto):
        ocorrencias.append(
            {
                "usuario_detectado": bool(correspondencia.group("usuario").strip()),
                "pagina": correspondencia.group("pagina").strip(),
                "metodo": correspondencia.group("metodo").strip(),
            }
        )
    return {"ocorrencias": ocorrencias, "quantidade": len(ocorrencias)}


def classificar_log(texto: str) -> dict:
    excecoes = EXCECAO_RE.findall(texto)
    classes = CLASSE_AGHU_RE.findall(texto)
    codigos_oracle = sorted(set(ORA_RE.findall(texto)))
    superior = texto.upper()
    if codigos_oracle or "SQL" in superior and "EXCEPTION" in superior:
        categoria = "banco"
    elif "SECURITYPHASELISTENER" in superior or "ERRO DE PERMISSAO" in superior or "ERRO DE PERMISSÃO" in superior:
        categoria = "segurança"
    elif "JAVAX.FACES" in superior or "JAKARTA.FACES" in superior or "PROPERTYNOTFOUND" in superior:
        categoria = "JSF"
    elif "HIBERNATE" in superior or "JAVAX.PERSISTENCE" in superior:
        categoria = "persistência"
    elif "EJB" in superior or "WELD" in superior or "CDI" in superior:
        categoria = "CDI/EJB"
    elif "DEPLOY" in superior or "WFLY" in superior:
        categoria = "deploy"
    else:
        categoria = "não classificado"
    return {
        "categoria": categoria,
        "excecao_raiz_candidata": excecoes[-1] if excecoes else None,
        "primeira_classe_aghuse": classes[0] if classes else None,
        "codigos_oracle": codigos_oracle,
        "linhas": len(texto.splitlines()),
    }


def sugerir_validacao(arquivos: list[str]) -> dict:
    mapa = mapear_modulos(arquivos)
    comandos: list[dict[str, str]] = []
    if mapa["possui_entidades"]:
        comandos.append(
            {
                "finalidade": "instalar entidades antes dos consumidores",
                "comando": "mvn clean install --activate-profiles '!PMD' --threads 1C --file aghu-entidades/pom.xml -Dmaven.test.skip=true -Dpmd.skip=true",
            }
        )
    modulos_aghu = [modulo for modulo in mapa["modulos"] if modulo not in {"aghu-entidades", "aghu"}]
    for modulo in modulos_aghu:
        comandos.append(
            {
                "finalidade": f"compilar o módulo {modulo} e dependências necessárias",
                "comando": f"mvn --file aghu/pom.xml --projects {modulo} --also-make test -Dpmd.skip=true",
            }
        )
    if mapa["possui_xhtml"]:
        comandos.append({"finalidade": "validar sintaxe dos Facelets alterados", "comando": "xmllint --noout <arquivos-xhtml>"})
    if mapa["possui_mensagens"]:
        comandos.append(
            {
                "finalidade": "verificar chaves de mensagens e duplicações",
                "comando": "python3 <plugin>/scripts/aghuse_automacao.py mensagens <arquivos-properties>",
            }
        )
    return {"mapa": mapa, "comandos_sugeridos": comandos, "executar_automaticamente": False}


def gerar_manifesto(caminhos: list[Path], tarefa: str | None) -> dict:
    arquivos = []
    for ordem, caminho in enumerate(caminhos, start=1):
        dados = caminho.read_bytes()
        arquivos.append(
            {
                "ordem": ordem,
                "nome": caminho.name,
                "tamanho_bytes": len(dados),
                "sha256": hashlib.sha256(dados).hexdigest(),
            }
        )
    return {"tarefa": tarefa, "arquivos": arquivos, "quantidade": len(arquivos)}


def caminhos_existentes(valores: list[str]) -> list[Path]:
    caminhos = [Path(valor).resolve() for valor in valores]
    ausentes = [str(caminho) for caminho in caminhos if not caminho.is_file()]
    if ausentes:
        raise FalhaAutomacao(f"arquivo(s) inexistente(s): {', '.join(ausentes)}")
    return caminhos


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    for nome in ("contexto", "modulos", "validacao"):
        comando = sub.add_parser(nome)
        comando.add_argument("--raiz", type=Path, default=Path.cwd())
        if nome != "contexto":
            comando.add_argument("arquivos", nargs="*")

    historico = sub.add_parser("historico")
    historico.add_argument("termo")
    historico.add_argument("--raiz", type=Path, default=Path.cwd())
    historico.add_argument("--limite", type=int, default=30)

    for nome in ("mensagens", "banco"):
        comando = sub.add_parser(nome)
        comando.add_argument("arquivos", nargs="+")

    for nome in ("seguranca", "log"):
        comando = sub.add_parser(nome)
        comando.add_argument("--arquivo", type=Path)

    manifesto = sub.add_parser("manifesto")
    manifesto.add_argument("arquivos", nargs="+")
    manifesto.add_argument("--tarefa")
    return parser


def main() -> int:
    args = criar_parser().parse_args()
    try:
        if args.comando == "contexto":
            resultado = contexto_repositorio(args.raiz)
        elif args.comando in {"modulos", "validacao"}:
            raiz = raiz_aghuse(args.raiz)
            arquivos = args.arquivos or arquivos_alterados(raiz)
            resultado = mapear_modulos(arquivos) if args.comando == "modulos" else sugerir_validacao(arquivos)
        elif args.comando == "historico":
            if args.limite < 1 or args.limite > 200:
                raise FalhaAutomacao("--limite deve estar entre 1 e 200")
            resultado = historico_git(args.raiz, args.termo, args.limite)
        elif args.comando == "mensagens":
            resultado = analisar_mensagens(caminhos_existentes(args.arquivos))
        elif args.comando == "banco":
            resultado = analisar_sql(caminhos_existentes(args.arquivos))
        elif args.comando == "seguranca":
            resultado = analisar_seguranca(obter_entrada(args.arquivo))
        elif args.comando == "log":
            resultado = classificar_log(obter_entrada(args.arquivo))
        else:
            resultado = gerar_manifesto(caminhos_existentes(args.arquivos), args.tarefa)
    except (FalhaAutomacao, OSError) as exc:
        print(json.dumps({"erro": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(resultado, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
