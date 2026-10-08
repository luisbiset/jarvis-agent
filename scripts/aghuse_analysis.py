#!/usr/bin/env python3
"""Analisa uma tarefa AGHUse localmente, sem alterar o projeto ou acessar serviços."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

LAYERS = {
    "database": ("aghu-entidades", "dao", "entity", "entidade", "persistence", "persistence.xml"),
    "backend": ("-server", "-core", "-client", "on.java", "rn.java", "facade", "service", "resource"),
    "frontend": ("-web", ".xhtml", "primefaces", "faces-config", "menu"),
    "tests": ("test", "src/test", "surefire"),
    "security": ("segur", "permission", "perfil", "menu", "role"),
}
AGENTS = {"database":"database", "backend":"backend", "frontend":"frontend", "tests":"qa", "security":"architecture"}

def locate(root: Path) -> dict:
    candidates = [root, root / "aghuse", root / "aghu"]
    for base in candidates:
        if (base / "aghu" / "pom.xml").is_file() and (base / "aghu-entidades" / "pom.xml").is_file(): return base
        if (base / "pom.xml").is_file() and (base / "aghu-entidades").is_dir(): return base
    return root

def files(base: Path) -> list[Path]:
    ignored = {"target", ".git", ".idea", "node_modules"}
    return [p for p in base.rglob("*") if p.is_file() and not ignored.intersection(p.parts)]

def analyze(args: argparse.Namespace) -> dict:
    base = locate(Path(args.project).resolve()); all_files = files(base)
    names = [str(p.relative_to(base)).replace("\\", "/") for p in all_files]
    task = args.requisito.strip()
    if not task: raise ValueError("o requisito não pode ser vazio")
    lower = task.lower()
    impact = {}
    for layer, markers in LAYERS.items():
        hits = [n for n in names if any(marker in n.lower() for marker in markers)]
        keywords = {"database":("tabela","campo","entidade","banco","coluna","persist"), "backend":("regra","serviço","api","facade","rn","on"), "frontend":("tela","campo","botão","primefaces","xhtml"), "tests":("teste","validar","regress"), "security":("permiss","perfil","menu","acesso","segurança")}[layer]
        relevant = any(k in lower for k in keywords)
        impact[layer] = {"detected": bool(hits) and (relevant or layer in ("backend", "tests")), "candidate_files": hits[:20], "candidate_count": len(hits)}
    selected = [layer for layer, item in impact.items() if item["detected"]]
    if not selected: selected = ["backend", "tests"]
    agents = [AGENTS[x] for x in ("database", "backend", "frontend", "tests", "security") if x in selected]
    complexity = "TRANSVERSAL" if len(selected) >= 4 else "LOCALIZED"
    risk = "HIGH" if any(x in selected for x in ("database", "security")) else "MEDIUM"
    return {"analysis":"aghuse-task", "read_only":True, "project_root":str(base), "requirement":task, "repository_detected":(base/"aghu"/"pom.xml").is_file() and (base/"aghu-entidades"/"pom.xml").is_file(), "inventory":{"files":len(all_files),"modules":sorted({n.split('/')[0] for n in names if n.endswith("pom.xml")})}, "classification":{"complexity":complexity,"risk_class":risk,"operational_mode":"READ_ONLY_AUDIT","signals":{"estimated_files":sum(x["candidate_count"] for x in impact.values()),"estimated_modules":len(impact),"database_migration":"database" in selected,"security_sensitive":"security" in selected,"tests_required":True}}, "impact":impact, "agents_recommended":agents, "plan":["confirmar requisito e critérios de aceite", "revisar legado e histórico do fluxo", "avaliar banco e impacto Oracle/PostgreSQL" if "database" in selected else "confirmar contratos e persistência existentes", "implementar por camada após plano aprovado", "executar validação direcionada e auditoria independente", "preparar roteiro de homologação"], "risks":["arquivos candidatos são heurísticos e exigem confirmação do especialista", "nenhuma conexão com banco, WildFly, Redmine ou ambiente compartilhado foi realizada"], "next_step":"revisar este plano e aprovar a implementação"}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--project", default="."); p.add_argument("--requisito", required=True); a=p.parse_args()
    try:
        result = analyze(a)
        result["result_kind"] = "candidate_inventory"
        result["diagnostic_complete"] = False
        result["next_step"] = "revisar este inventário; a saída heurística não é um diagnóstico concluído"
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError) as exc: print(json.dumps({"error":str(exc)}, ensure_ascii=False)); return 2
if __name__ == "__main__": raise SystemExit(main())
