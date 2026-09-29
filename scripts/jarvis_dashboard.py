#!/usr/bin/env python3
"""Painel local somente leitura para a telemetria do Jarvis."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "scripts" / "jarvis_runtime.py"

HTML = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jarvis Observability</title>
<style>body{font:15px system-ui;background:#0f172a;color:#e2e8f0;margin:0}main{max-width:1180px;margin:auto;padding:28px}h1{margin:0 0 6px}.muted{color:#94a3b8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:24px 0}.card,table{background:#1e293b;border:1px solid #334155;border-radius:10px}.card{padding:16px}.value{font-size:26px;font-weight:700;margin-top:7px}table{width:100%;border-collapse:collapse;overflow:hidden}th,td{text-align:left;padding:11px;border-bottom:1px solid #334155}th{color:#94a3b8;font-size:12px;text-transform:uppercase}tr:hover{background:#263449}a{color:#7dd3fc;text-decoration:none}.ok{color:#86efac}.bad{color:#fca5a5}.section{margin-top:28px}button{background:#2563eb;color:white;border:0;border-radius:6px;padding:8px 12px;cursor:pointer}@media(max-width:600px){main{padding:16px}th:nth-child(n+4),td:nth-child(n+4){display:none}}</style></head><body><main>
<h1>Jarvis Observability</h1><div class="muted">Telemetria local · somente leitura · atualização manual</div><div id="app">Carregando…</div>
<script>
const fmtMs=v=>v?`${Math.round(v)} ms`:'—'; const pct=v=>`${Math.round((v||0)*100)}%`; const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function load(){const r=await fetch('/api/dashboard');const d=await r.json();if(d.error){app.innerHTML=`<p class="bad">${esc(d.error)}</p>`;return}app.innerHTML=`<div class="grid">${[['Execuções',d.total_runs],['Sucesso',d.successful_runs],['Bloqueadas',d.failed_runs],['Duração média',fmtMs(d.average_duration_ms)],['Primeira tentativa',pct(d.first_pass_success_rate)],['Retries médios',d.average_rework_cycles?.toFixed(2)||'0'],['Agentes/execução',d.average_agent_invocations?.toFixed(1)||'0'],['Escaladas',d.escalation_count||0]].map(x=>`<div class="card"><div class="muted">${x[0]}</div><div class="value">${x[1]}</div></div>`).join('')}</div><div class="section"><h2>Execuções recentes</h2><table><thead><tr><th>Tarefa</th><th>Status</th><th>Complexidade</th><th>Risco</th><th>Início</th><th>Duração</th></tr></thead><tbody>${(d.recent_runs||[]).map(x=>`<tr><td><a href="/run/${encodeURIComponent(x.run_id)}">${esc(x.task_id||x.run_id)}</a></td><td class="${x.status==='DONE'?'ok':'bad'}">${esc(x.status)}</td><td>${esc(x.complexity)}</td><td>${esc(x.risk_class)}</td><td>${esc((x.started_at||'').replace('T',' ').replace('Z',''))}</td><td>${fmtMs(x.duration_ms)}</td></tr>`).join('')||'<tr><td colspan="6">Nenhuma execução registrada.</td></tr>'}</tbody></table></div><div class="section"><h2>Agentes</h2><table><thead><tr><th>Agente</th><th>Chamadas</th><th>Com findings</th><th>Findings acionáveis</th><th>Créditos observados</th></tr></thead><tbody>${Object.entries(d.agent_metrics||{}).map(([n,x])=>`<tr><td>${esc(n)}</td><td>${x.invocations}</td><td>${pct(x.finding_rate)}</td><td>${x.actionable_findings}</td><td>${x.credits}</td></tr>`).join('')||'<tr><td colspan="5">Sem chamadas.</td></tr>'}</tbody></table></div><p class="muted section">Banco: ${esc(d.telemetry_db)}</p>`}
load();
</script></main></body></html>"""

def dashboard(db: Path) -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("jarvis_runtime", RUNTIME)
    module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
    data = module.dashboard(type("Args", (), {"runs_dir": db.parent.parent, "telemetry_db": db})())
    if db.is_file():
        con = sqlite3.connect(db)
        try:
            con.row_factory = sqlite3.Row
            data["recent_runs"] = [dict(x) for x in con.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 30")]
        finally:
            con.close()
    return data

def models(root: Path = ROOT) -> dict:
    """Resumo somente leitura dos modelos, feedback e fila de treinamento."""
    rag = root / ".jarvis" / "rag"
    result = {"active": {}, "feedback": {}, "queue": {"pending": 0, "running": 0, "done": 0, "failed": 0}, "last_training": None}
    for name in ("reranker", "taxonomy"):
        path = rag / f"{name}.json"; item = {"status": "ACTIVE" if path.is_file() else "NONE", "updated_at": None, "examples": None}
        if path.is_file():
            item["updated_at"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
            try: item["examples"] = json.loads(path.read_text(encoding="utf-8")).get("examples")
            except (OSError, json.JSONDecodeError): item["status"] = "INVALID"
        result["active"][name] = item
    feedback = rag / "feedback.jsonl"
    if feedback.is_file():
        for line in feedback.read_text(encoding="utf-8").splitlines():
            if line.strip():
                status = json.loads(line).get("status", "UNKNOWN"); result["feedback"][status] = result["feedback"].get(status, 0) + 1
    queue = rag / "training-queue.jsonl"
    if queue.is_file():
        for line in queue.read_text(encoding="utf-8").splitlines():
            if line.strip():
                status = json.loads(line).get("status", "UNKNOWN").lower(); result["queue"][status] = result["queue"].get(status, 0) + 1
    manifest = rag / "training-manifest.json"
    if manifest.is_file():
        try: result["last_training"] = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): result["last_training"] = {"status": "INVALID"}
    return result

class Handler(BaseHTTPRequestHandler):
    db: Path
    def send(self, status, content, kind="text/html; charset=utf-8"):
        raw = content.encode() if isinstance(content, str) else content
        self.send_response(status); self.send_header("Content-Type", kind); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/": return self.send(200, HTML)
        if path == "/api/dashboard": return self.send(200, json.dumps(dashboard(self.db), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/models": return self.send(200, json.dumps(models(), ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/run/"):
            run_id = path.rsplit('/', 1)[-1]
            con = sqlite3.connect(self.db)
            try:
                con.row_factory = sqlite3.Row
                row = con.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            finally:
                con.close()
            return self.send(200, json.dumps(dict(row) if row else {"error":"execução não encontrada"}), "application/json; charset=utf-8")
        return self.send(404, "Não encontrado")
    def log_message(self, *_): pass

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=8765); p.add_argument('--telemetry-db',type=Path,default=ROOT/'.jarvis/telemetry/jarvis.db'); a=p.parse_args(); Handler.db=a.telemetry_db.resolve(); server=ThreadingHTTPServer((a.host,a.port),Handler); print(f'Jarvis Observability: http://{a.host}:{a.port}'); server.serve_forever()
if __name__ == '__main__': main()
