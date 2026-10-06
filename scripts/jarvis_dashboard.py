#!/usr/bin/env python3
"""Painel local somente leitura para a telemetria do Jarvis."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "scripts" / "jarvis_runtime.py"

HTML = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jarvis Observability</title>
<style>body{font:15px system-ui;background:#0f172a;color:#e2e8f0;margin:0}main{max-width:1180px;margin:auto;padding:28px}h1{margin:0 0 6px}.muted{color:#94a3b8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:24px 0}.card,table{background:#1e293b;border:1px solid #334155;border-radius:10px}.card{padding:16px}.value{font-size:26px;font-weight:700;margin-top:7px}table{width:100%;border-collapse:collapse;overflow:hidden}th,td{text-align:left;padding:11px;border-bottom:1px solid #334155}th{color:#94a3b8;font-size:12px;text-transform:uppercase}tr:hover{background:#263449}a{color:#7dd3fc;text-decoration:none}.ok{color:#86efac}.bad{color:#fca5a5}.section{margin-top:28px}button{background:#2563eb;color:white;border:0;border-radius:6px;padding:8px 12px;cursor:pointer}@media(max-width:600px){main{padding:16px}th:nth-child(n+4),td:nth-child(n+4){display:none}}</style></head><body><main>
<header style="display:flex;justify-content:space-between;align-items:center;gap:12px"><div><div class="muted" style="text-transform:uppercase;letter-spacing:.08em;font-size:11px">Central de execução</div><h1>Jarvis Control Center</h1><div class="muted"><span class="ok">● Runtime local ativo</span> · atualização automática</div></div><button onclick="load();loadControl()">↻ Atualizar</button></header><form onsubmit="return startTask(event)" style="display:flex;gap:8px;flex-wrap:wrap;margin:18px 0"><input id="new-task-id" required placeholder="ID da tarefa" style="padding:9px;border:1px solid #334155;border-radius:7px"><input id="new-task-query" required placeholder="Descreva o que precisa ser feito" style="padding:9px;min-width:300px;flex:1;border:1px solid #334155;border-radius:7px"><button type="submit">Iniciar tarefa</button></form><div id="app">Carregando…</div><div id="run-detail" class="section" style="display:none"></div>
<script>
const fmtMs=v=>v?`${Math.round(v)} ms`:'—'; const pct=v=>`${Math.round((v||0)*100)}%`; const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function load(){const r=await fetch('/api/dashboard');const d=await r.json();if(d.error){app.innerHTML=`<p class="bad">${esc(d.error)}</p>`;return}app.innerHTML=`<div class="grid">${[['Execuções',d.total_runs],['Sucesso',d.successful_runs],['Bloqueadas',d.failed_runs],['Duração média',fmtMs(d.average_duration_ms)],['Primeira tentativa',pct(d.first_pass_success_rate)],['Retries médios',d.average_rework_cycles?.toFixed(2)||'0'],['Agentes/execução',d.average_agent_invocations?.toFixed(1)||'0'],['Escaladas',d.escalation_count||0]].map(x=>`<div class="card"><div class="muted">${x[0]}</div><div class="value">${x[1]}</div></div>`).join('')}</div><div class="section"><h2>Execuções recentes</h2><table><thead><tr><th>ID da tarefa</th><th>Tarefa</th><th>Status</th><th>Complexidade</th><th>Risco</th><th>Início</th><th>Duração</th></tr></thead><tbody>${(d.recent_runs||[]).map(x=>`<tr><td>${esc(x.task_id||'UNKNOWN')}</td><td><a href="#" onclick="showRun('${encodeURIComponent(x.run_id)}');return false">${esc(x.task_id||x.run_id)}</a></td><td class="${x.status==='DONE'?'ok':'bad'}">${esc(x.status)}</td><td>${esc(x.complexity)}</td><td>${esc(x.risk_class)}</td><td>${esc((x.started_at||'').replace('T',' ').replace('Z',''))}</td><td>${fmtMs(x.duration_ms)}</td></tr>`).join('')||'<tr><td colspan="7">Nenhuma execução registrada.</td></tr>'}</tbody></table></div><div class="section"><h2>Agentes</h2><table><thead><tr><th>Agente</th><th>Chamadas</th><th>Com findings</th><th>Findings acionáveis</th><th>Créditos observados</th></tr></thead><tbody>${Object.entries(d.agent_metrics||{}).map(([n,x])=>`<tr><td>${esc(n)}</td><td>${x.invocations}</td><td>${pct(x.finding_rate)}</td><td>${x.actionable_findings}</td><td>${x.credits}</td></tr>`).join('')||'<tr><td colspan="5">Sem chamadas.</td></tr>'}</tbody></table></div><p class="muted section">Banco: ${esc(d.telemetry_db)}</p>`}
async function startTask(event){event.preventDefault();const response=await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:document.getElementById('new-task-id').value,query:document.getElementById('new-task-query').value})});const data=await response.json();if(!response.ok){alert(data.error||'Falha ao iniciar tarefa');return false}event.target.reset();alert('Tarefa criada; o plano está disponível no Runtime V3');load();return false}
async function showRun(runId){const response=await fetch('/api/runs/'+encodeURIComponent(runId));const data=await response.json();const panel=document.getElementById('run-detail');panel.style.display='block';if(data.error){panel.innerHTML='<p class="bad">'+esc(data.error)+'</p>';return}panel.innerHTML='<h2>'+esc(data.run.task_id||data.run.run_id)+'</h2><p>Status: <b>'+esc(data.run.status)+'</b> · risco: '+esc(data.run.risk_class)+'</p><h3>Timeline</h3><table><thead><tr><th>Estado</th><th>Data</th><th>Motivo</th></tr></thead><tbody>'+data.timeline.map(function(item){return '<tr><td>'+esc(item.target||item.status)+'</td><td>'+esc(item.at)+'</td><td>'+esc(item.reason)+'</td></tr>'}).join('')+'</tbody></table><h3>Invocações</h3><p>'+data.invocations.length+' chamadas de agentes · findings: '+data.findings.length+'</p>'}
load(); setInterval(load, 15000);
async function loadControl(){const r=await fetch('/api/control');const d=await r.json();let box=document.getElementById('rag-control');if(!box){box=document.createElement('div');box.id='rag-control';box.className='section';document.querySelector('main').appendChild(box)}box.innerHTML=`<h2>Controle do RAG</h2><p class="muted">Feedback pendente: ${d.feedback.pending.length} · Fila: ${d.queue.pending} · Modelos ativos: ${Object.values(d.models.active).filter(x=>x.status==='ACTIVE').length}</p><table><thead><tr><th>Consulta</th><th>Arquivo</th><th>Ação</th></tr></thead><tbody>${d.feedback.pending.map(x=>`<tr><td>${esc(x.query)}</td><td>${esc(x.candidate?.path)}</td><td><button onclick="decide('${x.id}',true)">Relevante</button> <button onclick="decide('${x.id}',false)">Irrelevante</button></td></tr>`).join('')||'<tr><td colspan="3">Nenhum feedback pendente.</td></tr>'}</tbody></table><p><button onclick="enqueue()">Enfileirar treinamento</button> <button onclick="loadControl()">Atualizar</button></p>`}
async function decide(id,relevant){await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,action:relevant?'approve':'reject'})});location.reload()}
async function enqueue(){await fetch('/api/training',{method:'POST'});location.reload()}
const renderControl=loadControl;loadControl=async function(){document.querySelectorAll('main>#control-panel').forEach(node=>node.remove());await renderControl();const panels=document.querySelectorAll('main>.section');if(panels.length)panels[panels.length-1].id='control-panel'};loadControl();
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
    data["metrics_contract"] = {"schema_version": "1.0.0", "source": "Runtime V3", "phases": ["INITIAL", "FINAL"], "unknown_value": "UNKNOWN/NOT_OBSERVED"}
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


def filtered_runs(db: Path, query: dict[str, list[str]]) -> list[dict]:
    """Consulta operacional segura para Tasks, sem expor conteúdo sensível."""
    if not db.is_file():
        return []
    clauses, values = [], []
    for field in ("status", "complexity", "risk_class"):
        if query.get(field):
            clauses.append(f"{field}=?")
            values.append(query[field][0])
    if query.get("q"):
        clauses.append("(task_id LIKE ? OR run_id LIKE ?)")
        values.extend([f"%{query['q'][0]}%"] * 2)
    sql = "SELECT * FROM runs" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY started_at DESC LIMIT 100"
    connection = sqlite3.connect(db)
    try:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(sql, values)]
    finally:
        connection.close()


def run_detail(db: Path, run_id: str) -> dict:
    """Retorna task, invocações, timeline e findings correlacionados."""
    if not db.is_file():
        return {"error": "telemetria não encontrada"}
    connection = sqlite3.connect(db)
    try:
        connection.row_factory = sqlite3.Row
        run = connection.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            return {"error": "execução não encontrada"}
        invocations = [dict(row) for row in connection.execute("SELECT * FROM agent_invocations WHERE run_id=? ORDER BY started_at", (run_id,))]
        timeline = [dict(row) for row in connection.execute("SELECT * FROM transitions WHERE run_id=? ORDER BY at", (run_id,))]
        findings = [dict(row) for row in connection.execute("SELECT * FROM findings WHERE run_id=?", (run_id,))]
        events_path = db.parent / "runs" / run_id / "events.jsonl"
        if not events_path.is_file():
            events_path = db.parent.parent / "runs" / run_id / "events.jsonl"
        logs = []
        if events_path.is_file():
            for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]:
                try:
                    event = json.loads(line)
                    logs.append({key: event.get(key) for key in ("event", "at", "status", "stage", "agent", "termination_reason", "budget_warnings") if event.get(key) is not None})
                except json.JSONDecodeError:
                    continue
        return {"run": dict(run), "invocations": invocations, "timeline": timeline, "findings": findings, "logs": logs}
    finally:
        connection.close()


def agents_summary(db: Path) -> dict:
    data = _runtime_dashboard(db)
    return {"agents": data.get("agent_metrics", {}), "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def models_usage(db: Path) -> dict:
    if not db.is_file():
        return {"models": [], "calls": 0, "input_tokens": 0, "output_tokens": 0, "credits": UNKNOWN}
    connection = sqlite3.connect(db)
    try:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute("SELECT model_effective AS model, effective_reasoning AS reasoning, COUNT(*) AS calls, COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens, COALESCE(SUM(credits),0) AS credits FROM execution_attempts GROUP BY model_effective, effective_reasoning ORDER BY credits DESC")]
    finally:
        connection.close()
    return {"models": rows, "calls": sum(row["calls"] for row in rows), "input_tokens": sum(row["input_tokens"] for row in rows), "output_tokens": sum(row["output_tokens"] for row in rows), "credits": sum(row["credits"] for row in rows)}


def evidence(db: Path, query: dict[str, list[str]]) -> dict:
    if not db.is_file():
        return {"items": []}
    connection = sqlite3.connect(db)
    try:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute("SELECT * FROM findings ORDER BY rowid DESC LIMIT 200")]
    finally:
        connection.close()
    if query.get("q"):
        term = query["q"][0].lower()
        rows = [row for row in rows if term in json.dumps(row, ensure_ascii=False).lower()]
    return {"items": rows}


def attention(db: Path) -> dict:
    rows = filtered_runs(db, {})
    return {"items": [{"run_id": row["run_id"], "task_id": row["task_id"], "kind": row["status"]} for row in rows if row["status"] in {"BLOCKED", "HUMAN_GATE", "PLAN_READY"}][:30]}


def task_payload(payload: dict) -> tuple[dict | None, str | None]:
    """Valida o formulário da dashboard sem aceitar comandos arbitrários."""
    task_id = str(payload.get("task_id", "")).strip()
    query = str(payload.get("query", "")).strip()
    if not task_id or not query:
        return None, "task_id e query são obrigatórios"
    allowed = {
        "complexity": {"TRIVIAL", "LOCALIZED", "TRANSVERSAL", "CRITICAL"},
        "risk_class": {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
        "operational_mode": {"COPILOT", "ASSISTED_AUTOPILOT", "READ_ONLY_AUDIT"},
    }
    result = {"task_id": task_id[:120], "query": query[:4000]}
    for key, values in allowed.items():
        value = str(payload.get(key, "LOCALIZED" if key == "complexity" else "MEDIUM" if key == "risk_class" else "COPILOT")).upper()
        if value not in values:
            return None, f"{key} inválido"
        result[key] = value
    return result, None

class Handler(BaseHTTPRequestHandler):
    db: Path
    def send(self, status, content, kind="text/html; charset=utf-8"):
        raw = content.encode() if isinstance(content, str) else content
        self.send_response(status); self.send_header("Content-Type", kind); self.send_header("Cache-Control", "no-store, no-cache, must-revalidate"); self.send_header("Pragma", "no-cache"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        if path == "/":
            compact_css = "<style>:root{--bg:#f4f7fb;--surface:#fff;--line:#e5eaf2;--text:#172033;--muted:#718096;--blue:#2563eb;--green:#059669;--red:#dc2626;--shadow:0 8px 24px rgba(30,55,90,.07)}*{box-sizing:border-box}body{font:14px Inter,ui-sans-serif,system-ui;background:var(--bg);color:var(--text)}main{max-width:1440px;padding:22px 28px;margin:auto}.grid{grid-template-columns:repeat(8,minmax(110px,1fr));gap:10px;margin:16px 0}.card,table{background:var(--surface);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}.card{padding:13px}.value{font-size:22px;margin-top:5px}.section{margin-top:16px;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:var(--shadow)}.section h2{font-size:15px;margin:0 0 11px}.section table{box-shadow:none;display:block;max-height:245px;overflow:auto}th,td{padding:9px 10px;white-space:nowrap}th{position:sticky;top:0;background:var(--surface)}button{border-radius:7px;padding:7px 10px;font-weight:600}@media(max-width:1050px){.grid{grid-template-columns:repeat(4,1fr)}}@media(max-width:600px){main{padding:14px}.grid{grid-template-columns:repeat(2,1fr)}}</style>"
            compact_css = "<style>" + (ROOT / "scripts" / "dashboard-modern.css").read_text(encoding="utf-8") + "</style>"
            return self.send(200, HTML.replace("</head>", compact_css + "</head>"))
        if path == "/api/dashboard": return self.send(200, json.dumps(dashboard(self.db), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/runs": return self.send(200, json.dumps({"runs": filtered_runs(self.db, parse_qs(urlparse(self.path).query))}, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/attention": return self.send(200, json.dumps(attention(self.db), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/agents": return self.send(200, json.dumps(agents_summary(self.db), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/models/usage": return self.send(200, json.dumps(models_usage(self.db), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/evidence": return self.send(200, json.dumps(evidence(self.db, query), ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/runs/"): return self.send(200, json.dumps(run_detail(self.db, path.rsplit('/', 1)[-1]), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/models": return self.send(200, json.dumps(models(), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/control":
            feedback_path = ROOT / ".jarvis/rag/feedback.jsonl"; rows = []
            if feedback_path.is_file(): rows = [json.loads(line) for line in feedback_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            return self.send(200, json.dumps({"models": models(), "feedback": {"pending": [row for row in rows if row.get("status") == "PENDING"]}, "queue": models().get("queue", {})}, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/run/"):
            run_id = path.rsplit('/', 1)[-1]
            return self.send(200, json.dumps(run_detail(self.db, run_id), ensure_ascii=False), "application/json; charset=utf-8")
        return self.send(404, "Não encontrado")
    def do_POST(self):
        path = urlparse(self.path).path
        try: payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0")) or 0) or b"{}")
        except json.JSONDecodeError: return self.send(400, json.dumps({"error": "JSON inválido"}), "application/json; charset=utf-8")
        if path == "/api/tasks":
            clean, error = task_payload(payload)
            if error:
                return self.send(400, json.dumps({"error": error}, ensure_ascii=False), "application/json; charset=utf-8")
            command = [sys.executable, str(ROOT / "scripts" / "jarvis_runtime.py"), "init", "--task-id", clean["task_id"], "--complexity", clean["complexity"], "--risk-class", clean["risk_class"], "--operational-mode", clean["operational_mode"], "--task-query", clean["query"]]
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            if result.returncode:
                return self.send(500, json.dumps({"error": result.stderr[-1000:] or "não foi possível iniciar a task"}, ensure_ascii=False), "application/json; charset=utf-8")
            try:
                created = json.loads(result.stdout)
            except json.JSONDecodeError:
                return self.send(500, json.dumps({"error": "resposta inválida do Runtime V3"}), "application/json; charset=utf-8")
            return self.send(201, json.dumps({"ok": True, "run_dir": created.get("run_dir"), "state": created.get("state", {})}, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/feedback":
            from aghuse_rag_feedback import read, write
            feedback_path = ROOT / ".jarvis/rag/feedback.jsonl"; rows = read(feedback_path); item = next((row for row in rows if row.get("id") == payload.get("id") and row.get("status") == "PENDING"), None)
            if not item: return self.send(404, json.dumps({"error": "feedback pendente não encontrado"}), "application/json; charset=utf-8")
            action = payload.get("action")
            if action not in {"approve", "reject"}: return self.send(400, json.dumps({"error": "ação inválida"}), "application/json; charset=utf-8")
            item["status"] = "APPROVED" if action == "approve" else "REJECTED"; item["relevant"] = action == "approve"; item["decided_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds"); write(feedback_path, rows)
            return self.send(200, json.dumps({"ok": True, "id": item["id"], "status": item["status"]}), "application/json; charset=utf-8")
        if path == "/api/training":
            result = subprocess.run([sys.executable, str(ROOT / "scripts/aghuse_rag_queue.py"), "enqueue"], cwd=ROOT, text=True, capture_output=True)
            return self.send(200 if result.returncode == 0 else 500, result.stdout or result.stderr, "application/json; charset=utf-8")
        return self.send(404, "Not found")
    def log_message(self, *_): pass

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=8765); p.add_argument('--telemetry-db',type=Path,default=ROOT/'.jarvis/telemetry/jarvis.db'); a=p.parse_args(); Handler.db=a.telemetry_db.resolve(); server=ThreadingHTTPServer((a.host,a.port),Handler); print(f'Jarvis Observability: http://{a.host}:{a.port}'); server.serve_forever()
if __name__ == '__main__': main()
