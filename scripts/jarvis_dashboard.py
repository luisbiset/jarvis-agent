#!/usr/bin/env python3
"""Painel local somente leitura para a telemetria do Jarvis."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "scripts" / "jarvis_runtime.py"
UNKNOWN = "UNKNOWN/NOT_OBSERVED"
CHAT_STORE = ROOT / ".jarvis" / "dashboard" / "chat-sessions.jsonl"
AUDIT_STORE = ROOT / ".jarvis" / "dashboard" / "audit.jsonl"
SETTINGS_STORE = ROOT / ".jarvis" / "dashboard" / "settings-revisions.jsonl"
INTEGRATIONS_STORE = ROOT / ".jarvis" / "dashboard" / "integrations.json"
REDMINE_MCP = ROOT / "plugins" / "redmine-agent" / "scripts" / "server.mjs"
PROJECTS_CONFIG = ROOT / "config" / "projects.json"
ACTIVE_PROJECT_STORE = ROOT / ".jarvis" / "dashboard" / "active-project.json"

HTML = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jarvis Observability</title>
<style>body{font:15px system-ui;background:#0f172a;color:#e2e8f0;margin:0}main{max-width:1180px;margin:auto;padding:28px}h1{margin:0 0 6px}.muted{color:#94a3b8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:24px 0}.card,table{background:#1e293b;border:1px solid #334155;border-radius:10px}.card{padding:16px}.value{font-size:26px;font-weight:700;margin-top:7px}table{width:100%;border-collapse:collapse;overflow:hidden}th,td{text-align:left;padding:11px;border-bottom:1px solid #334155}th{color:#94a3b8;font-size:12px;text-transform:uppercase}tr:hover{background:#263449}a{color:#7dd3fc;text-decoration:none}.ok{color:#86efac}.bad{color:#fca5a5}.section{margin-top:28px}button{background:#2563eb;color:white;border:0;border-radius:6px;padding:8px 12px;cursor:pointer}@media(max-width:600px){main{padding:16px}th:nth-child(n+4),td:nth-child(n+4){display:none}}</style></head><body><main>
<header style="display:flex;justify-content:space-between;align-items:center;gap:12px"><div><div class="muted" style="text-transform:uppercase;letter-spacing:.08em;font-size:11px">Central de execução</div><h1>Jarvis Control Center</h1><div class="muted"><span class="ok">● Runtime local ativo</span> · atualização automática</div></div><button onclick="load();loadControl()">↻ Atualizar</button></header><form onsubmit="return startTask(event)" style="display:flex;gap:8px;flex-wrap:wrap;margin:18px 0"><input id="new-task-id" required placeholder="ID da tarefa" style="padding:9px;border:1px solid #334155;border-radius:7px"><input id="new-task-query" required placeholder="Descreva o que precisa ser feito" style="padding:9px;min-width:300px;flex:1;border:1px solid #334155;border-radius:7px"><button type="submit">Iniciar tarefa</button></form><div id="app">Carregando…</div><div id="run-detail" class="section" style="display:none"></div>
<script>
const fmtMs=v=>v?`${Math.round(v)} ms`:'—'; const pct=v=>`${Math.round((v||0)*100)}%`; const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function load(){const r=await fetch('/api/dashboard');const d=await r.json();if(d.error){app.innerHTML=`<p class="bad">${esc(d.error)}</p>`;return}app.innerHTML=`<div class="grid">${[['Execuções',d.total_runs],['Sucesso',d.successful_runs],['Bloqueadas',d.failed_runs],['Duração média',fmtMs(d.average_duration_ms)],['Primeira tentativa',pct(d.first_pass_success_rate)],['Retries médios',d.average_rework_cycles?.toFixed(2)||'0'],['Agentes/execução',d.average_agent_invocations?.toFixed(1)||'0'],['Escaladas',d.escalation_count||0]].map(x=>`<div class="card"><div class="muted">${x[0]}</div><div class="value">${x[1]}</div></div>`).join('')}</div><div class="section"><h2>Execuções recentes</h2><table><thead><tr><th>ID da tarefa</th><th>Tarefa</th><th>Status</th><th>Complexidade</th><th>Risco</th><th>Início</th><th>Duração</th></tr></thead><tbody>${(d.recent_runs||[]).map(x=>`<tr><td>${esc(x.task_id||'UNKNOWN')}</td><td><a href="#" onclick="showRun('${encodeURIComponent(x.run_id)}');return false">${esc(x.task_id||x.run_id)}</a></td><td class="${x.status==='DONE'?'ok':'bad'}">${esc(x.status)}</td><td>${esc(x.complexity)}</td><td>${esc(x.risk_class)}</td><td>${esc((x.started_at||'').replace('T',' ').replace('Z',''))}</td><td>${fmtMs(x.duration_ms)}</td></tr>`).join('')||'<tr><td colspan="7">Nenhuma execução registrada.</td></tr>'}</tbody></table></div><div class="section"><h2>Agentes</h2><table><thead><tr><th>Agente</th><th>Chamadas</th><th>Com findings</th><th>Findings acionáveis</th><th>Créditos observados</th></tr></thead><tbody>${Object.entries(d.agent_metrics||{}).map(([n,x])=>`<tr><td>${esc(n)}</td><td>${x.invocations}</td><td>${pct(x.finding_rate)}</td><td>${x.actionable_findings}</td><td>${x.credits}</td></tr>`).join('')||'<tr><td colspan="5">Sem chamadas.</td></tr>'}</tbody></table></div><p class="muted section">Banco: ${esc(d.telemetry_db)}</p>`}
async function startTask(event){event.preventDefault();const response=await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:document.getElementById('new-task-id').value,query:document.getElementById('new-task-query').value})});const data=await response.json();if(!response.ok){alert(data.error||'Falha ao iniciar tarefa');return false}event.target.reset();alert('Tarefa criada; o plano está disponível no Runtime V3');load();return false}
async function showRun(runId){const response=await fetch('/api/runs/'+encodeURIComponent(runId));const data=await response.json();const panel=document.getElementById('run-detail');panel.style.display='block';if(data.error){panel.innerHTML='<p class="bad">'+esc(data.error)+'</p>';return}const safeRunId=encodeURIComponent(runId);panel.innerHTML=`<h2>${esc(data.run.task_id||data.run.run_id)}</h2><p>Status: <b>${esc(data.run.status)}</b> · risco: ${esc(data.run.risk_class)}</p><p><button onclick="runAction('${safeRunId}','PAUSE')">Pausar</button> <button onclick="runAction('${safeRunId}','RESUME')">Retomar</button> <button onclick="runAction('${safeRunId}','APPROVE')">Aprovar</button> <button onclick="runAction('${safeRunId}','RETRY')">Refazer</button> <a href="/api/runs/${safeRunId}/diff" target="_blank">Abrir diff</a></p><h3>Checkpoint</h3><p>${esc(data.checkpoint?.created_at||'Não disponível')}</p><h3>Timeline</h3><table><thead><tr><th>Estado</th><th>Data</th><th>Motivo</th></tr></thead><tbody>${data.timeline.map(function(item){return '<tr><td>'+esc(item.target||item.status)+'</td><td>'+esc(item.at)+'</td><td>'+esc(item.reason)+'</td></tr>'}).join('')}</tbody></table><h3>Invocações</h3><p>${data.invocations.length} chamadas de agentes · findings: ${data.findings.length}</p>`;streamRun(runId)}
let activeEvents; function streamRun(runId){if(activeEvents)activeEvents.close();if(!window.EventSource)return;activeEvents=new EventSource('/api/runs/'+encodeURIComponent(runId)+'/events');activeEvents.onmessage=function(event){const item=JSON.parse(event.data);const panel=document.getElementById('run-detail');const node=document.createElement('p');node.className='muted';node.textContent=(item.event||'EVENT')+' · '+(item.at||'');panel.appendChild(node)};activeEvents.onerror=function(){activeEvents.close()}}
async function sendChat(event){event.preventDefault();const input=document.getElementById('chat-message');const out=document.getElementById('chat-output');const message=input.value.trim();if(!message)return false;if(!window.chatSession){const r=await fetch('/api/chat/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});window.chatSession=await r.json()}const r=await fetch('/api/chat/sessions/'+encodeURIComponent(window.chatSession.session_id)+'/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message})});const d=await r.json();out.innerHTML='<p><b>Você:</b> '+esc(message)+'</p><p><b>Jarvis:</b> '+esc(d.message?.response?.summary||d.error||'sem resposta')+'</p>';input.value='';return false}
async function runAction(runId,action){if(!confirm('Confirmar ação '+action+'?'))return;const r=await fetch('/api/runs/'+encodeURIComponent(runId)+'/actions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,confirm:true,reason:'ação confirmada na Dashboard'})});const d=await r.json();alert(d.error||('Estado: '+d.state));showRun(runId)}
async function searchGlobal(event){event.preventDefault();const q=document.getElementById('global-search').value.trim();const r=await fetch('/api/search?q='+encodeURIComponent(q));const d=await r.json();document.getElementById('search-output').innerHTML=(d.items||[]).map(x=>'<p><b>'+esc(x.type)+'</b> · '+esc(x.title||x.id)+'</p>').join('')||'<p class="muted">Nenhum resultado</p>';return false}
async function commandPalette(){const r=await fetch('/api/commands');const d=await r.json();const choice=prompt((d.commands||[]).map((x,i)=>i+': '+x.label).join('\\n')+'\\nDigite o número');const item=d.commands?.[Number(choice)];if(item?.id==='search.global')document.getElementById('global-search')?.focus();}
const chat=document.createElement('section');chat.className='section';chat.innerHTML='<h2>Chat operacional</h2><p class="muted">Converse com o Jarvis; o RAG é consultado antes do planejamento.</p><form onsubmit="return sendChat(event)" style="display:flex;gap:8px"><input id="chat-message" required placeholder="O que você precisa fazer?" style="padding:9px;flex:1;border:1px solid #cbd5e1;border-radius:7px"><button type="submit">Enviar</button><button type="button" onclick="commandPalette()">Command Palette</button></form><div id="chat-output"></div>';document.querySelector('main').prepend(chat);
const search=document.createElement('section');search.className='section';search.innerHTML='<h2>Busca global</h2><form onsubmit="return searchGlobal(event)" style="display:flex;gap:8px"><input id="global-search" placeholder="Tarefas, chats e execuções" style="padding:9px;flex:1;border:1px solid #cbd5e1;border-radius:7px"><button type="submit">Buscar</button></form><div id="search-output"></div>';document.querySelector('main').prepend(search);
document.getElementById('chat-message').setAttribute('aria-label','Mensagem para o Jarvis');document.getElementById('chat-output').setAttribute('aria-live','polite');document.getElementById('global-search').setAttribute('aria-label','Busca global');document.getElementById('search-output').setAttribute('aria-live','polite');document.addEventListener('keydown',function(event){if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();commandPalette()}});
async function loadSeries(){const r=await fetch('/api/metrics/series');const d=await r.json();let box=document.getElementById('metrics-series');if(!box){box=document.createElement('section');box.id='metrics-series';box.className='section';document.querySelector('main').appendChild(box)}const rows=d.series||[];const max=Math.max(1,...rows.map(x=>Number(x.calls||0)));box.innerHTML='<h2>Séries de métricas</h2><p class="muted">Qualidade temporal: '+esc(d.date_quality||'UNKNOWN/NOT_OBSERVED')+'</p>'+ (rows.map(x=>'<div style="display:grid;grid-template-columns:120px 1fr 80px;gap:8px;align-items:center;margin:6px 0"><span>'+esc(x.date)+' · '+esc(x.model)+'</span><span style="background:#dbeafe;border-radius:4px;height:12px"><span style="display:block;width:'+Math.round((x.calls/max)*100)+'%;height:12px;background:#2563eb;border-radius:4px"></span></span><span>'+esc(x.calls)+' chamadas</span></div>').join('')||'<p class="muted">Sem dados observados.</p>')}
showRun=async function(runId){const response=await fetch('/api/runs/'+encodeURIComponent(runId));const data=await response.json();const panel=document.getElementById('run-detail');panel.style.display='block';if(data.error){panel.innerHTML='<p class="bad">'+esc(data.error)+'</p>';return}const safeRunId=encodeURIComponent(runId);panel.innerHTML=`<h2>${esc(data.run.task_id||data.run.run_id)}</h2><p>Status: <b>${esc(data.run.status)}</b> · risco: ${esc(data.run.risk_class)}</p><p><button onclick="runAction('${safeRunId}','PAUSE')">Pausar</button> <button onclick="runAction('${safeRunId}','RESUME')">Retomar</button> <button onclick="runAction('${safeRunId}','APPROVE')">Aprovar</button> <button onclick="runAction('${safeRunId}','RETRY')">Refazer</button></p><h3>Checkpoint</h3><p>${esc(data.checkpoint?.created_at||'Não disponível')}</p><h3>Timeline</h3><p>${data.timeline.length} eventos</p>`;streamRun(runId)};
load(); loadSeries(); setInterval(load, 15000); setInterval(loadSeries, 15000);
async function loadControl(){const r=await fetch('/api/control');const d=await r.json();let box=document.getElementById('rag-control');if(!box){box=document.createElement('div');box.id='rag-control';box.className='section';document.querySelector('main').appendChild(box)}box.innerHTML=`<h2>Controle do RAG</h2><p class="muted">Feedback pendente: ${d.feedback.pending.length} · Fila: ${d.queue.pending} · Modelos ativos: ${Object.values(d.models.active).filter(x=>x.status==='ACTIVE').length}</p><table><thead><tr><th>Consulta</th><th>Arquivo</th><th>Ação</th></tr></thead><tbody>${d.feedback.pending.map(x=>`<tr><td>${esc(x.query)}</td><td>${esc(x.candidate?.path)}</td><td><button onclick="decide('${x.id}',true)">Relevante</button> <button onclick="decide('${x.id}',false)">Irrelevante</button></td></tr>`).join('')||'<tr><td colspan="3">Nenhum feedback pendente.</td></tr>'}</tbody></table><p><button onclick="enqueue()">Enfileirar treinamento</button> <button onclick="loadControl()">Atualizar</button></p>`}
async function refreshControlPreservingScroll(){const y=window.scrollY;await loadControl();window.scrollTo({top:y,left:0,behavior:'instant'})}
async function decide(id,relevant){const response=await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,action:relevant?'approve':'reject'})});if(!response.ok){alert('Não foi possível registrar o feedback.');return}await refreshControlPreservingScroll()}
async function enqueue(){const response=await fetch('/api/training',{method:'POST'});if(!response.ok){alert('Não foi possível enfileirar o treinamento.');return}await refreshControlPreservingScroll()}
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
        checkpoint = load_checkpoint(run_id)
        return {"run": dict(run), "invocations": invocations, "timeline": timeline, "findings": findings, "logs": logs, "checkpoint": checkpoint}
    finally:
        connection.close()


def agents_summary(db: Path) -> dict:
    data = _runtime_dashboard(db)
    return {"agents": data.get("agent_metrics", {}), "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

def agent_detail(db: Path, agent: str) -> dict:
    if not db.is_file(): return {"agent": agent, "invocations": [], "runs": [], "findings": [], "usage": {"credits": UNKNOWN}}
    connection = sqlite3.connect(db); connection.row_factory = sqlite3.Row
    try:
        invocations = [dict(row) for row in connection.execute("SELECT * FROM agent_invocations WHERE agent=? ORDER BY started_at DESC LIMIT 200", (agent,))]
        run_ids = [row.get("run_id") for row in invocations if row.get("run_id")]
        runs = []
        if run_ids:
            marks = ",".join("?" for _ in run_ids)
            runs = [dict(row) for row in connection.execute(f"SELECT run_id,task_id,status,complexity,risk_class,started_at FROM runs WHERE run_id IN ({marks}) ORDER BY started_at DESC", run_ids)]
        findings = []
        if run_ids:
            marks = ",".join("?" for _ in run_ids)
            finding_columns = {row[1] for row in connection.execute("PRAGMA table_info(findings)")}
            order = "created_at DESC" if "created_at" in finding_columns else "rowid DESC"
            findings = [dict(row) for row in connection.execute(f"SELECT * FROM findings WHERE run_id IN ({marks}) ORDER BY {order} LIMIT 200", run_ids)]
        usage = {"calls": len(invocations), "input_tokens": sum(row.get("input_tokens", 0) or 0 for row in invocations), "output_tokens": sum(row.get("output_tokens", 0) or 0 for row in invocations), "credits": sum(row.get("credits", 0) or 0 for row in invocations)}
        return {"agent": agent, "invocations": invocations, "runs": runs, "findings": findings, "usage": usage, "content_policy": "observed_telemetry_only"}
    finally: connection.close()


def models_usage(db: Path, query: dict[str, list[str]] | None = None) -> dict:
    if not db.is_file():
        return {"models": [], "calls": 0, "input_tokens": 0, "output_tokens": 0, "credits": UNKNOWN}
    connection = sqlite3.connect(db)
    try:
        connection.row_factory = sqlite3.Row
        columns = {row[1] for row in connection.execute("PRAGMA table_info(execution_attempts)")}
        clauses, values = [], []
        query = query or {}
        for key, column in (("model", "model_effective"), ("reasoning", "effective_reasoning")):
            if query.get(key) and column in columns: clauses.append(column + "=?"); values.append(query[key][0])
        if query.get("from") and "created_at" in columns: clauses.append("created_at>=?"); values.append(query["from"][0])
        if query.get("to") and "created_at" in columns: clauses.append("created_at<=?"); values.append(query["to"][0])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = [dict(row) for row in connection.execute("SELECT model_effective AS model, effective_reasoning AS reasoning, COUNT(*) AS calls, COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens, COALESCE(SUM(credits),0) AS credits FROM execution_attempts" + where + " GROUP BY model_effective, effective_reasoning ORDER BY credits DESC", values)]
    finally:
        connection.close()
    return {"models": rows, "calls": sum(row["calls"] for row in rows), "input_tokens": sum(row["input_tokens"] for row in rows), "output_tokens": sum(row["output_tokens"] for row in rows), "credits": sum(row["credits"] for row in rows)}

def metrics_series(db: Path, query: dict[str, list[str]] | None = None) -> dict:
    if not db.is_file(): return {"series": [], "date_quality": UNKNOWN}
    connection = sqlite3.connect(db); connection.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(execution_attempts)")}
        date_column = "created_at" if "created_at" in columns else None
        rows = [dict(row) for row in connection.execute("SELECT * FROM execution_attempts")]
        grouped = {}
        for row in rows:
            date = str(row.get(date_column))[:10] if date_column and row.get(date_column) else UNKNOWN
            key = (date, row.get("model_effective", UNKNOWN), row.get("effective_reasoning", UNKNOWN))
            item = grouped.setdefault(key, {"date": date, "model": key[1], "reasoning": key[2], "calls": 0, "input_tokens": 0, "output_tokens": 0, "credits": 0})
            item["calls"] += 1; item["input_tokens"] += row.get("input_tokens", 0) or 0; item["output_tokens"] += row.get("output_tokens", 0) or 0; item["credits"] += row.get("credits", 0) or 0
        return {"series": list(grouped.values()), "date_quality": "OBSERVED" if date_column else UNKNOWN}
    finally: connection.close()

def _append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")

def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file(): return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if line.strip():
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: continue
    return rows

def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    temporary.replace(path)

def _safe_summary(value: str, limit: int = 500) -> str:
    text = " ".join(str(value).split())
    return text[:limit]

def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _require_project(project_id: str | None) -> dict:
    project = project_by_id(str(project_id or ""))
    if not project:
        raise ValueError("projeto inválido")
    return project

def create_session(project_id: str, task_id: str | None = None) -> dict:
    _require_project(project_id)
    session = {"session_id": "chat-" + uuid.uuid4().hex, "project_id": project_id, "task_id": _safe_summary(task_id or "", 120), "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "messages": [], "run_id": None}
    _append_jsonl(CHAT_STORE, session)
    return session

def chat_sessions(session_id: str | None = None, project_id: str | None = None) -> list[dict]:
    rows = _read_jsonl(CHAT_STORE)
    return [row for row in rows if (not session_id or row.get("session_id") == session_id) and (not project_id or row.get("project_id") == project_id)]

def save_checkpoint(run_id: str, state: dict) -> dict:
    root = ROOT / ".jarvis" / "runs" / run_id / "checkpoints"
    root.mkdir(parents=True, exist_ok=True)
    safe = {"schema_version": "1.0.0", "run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "state": state}
    path = root / (safe["created_at"].replace(":", "-") + ".json")
    path.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "latest.json").write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    return safe

def load_checkpoint(run_id: str) -> dict | None:
    path = ROOT / ".jarvis" / "runs" / run_id / "checkpoints" / "latest.json"
    if not path.is_file(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return {"status": "INVALID"}

def audit_action(action: str, run_id: str | None, payload: dict, result: dict) -> dict:
    entry = {"audit_id": "audit-" + uuid.uuid4().hex, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "action": action, "run_id": run_id, "actor": "dashboard-local", "idempotency_key": payload.get("idempotency_key"), "request_hash": _hash(json.dumps(payload, sort_keys=True, ensure_ascii=False)), "result": result}
    _append_jsonl(AUDIT_STORE, entry)
    return entry

def global_search(query: str, db: Path) -> dict:
    term = query.strip().lower()
    if not term: return {"items": [], "query_hash": _hash(query)}
    items = []
    for row in filtered_runs(db, {"q": [query]}):
        items.append({"type": "run", "id": row.get("run_id"), "title": row.get("task_id"), "status": row.get("status"), "source": "telemetry"})
    for session in chat_sessions():
        if term in json.dumps(session, ensure_ascii=False).lower():
            items.append({"type": "chat", "id": session.get("session_id"), "title": session.get("task_id") or session.get("session_id"), "source": "chat"})
    return {"items": items[:100], "query_hash": _hash(query), "count": len(items)}

def available_commands() -> list[dict]:
    return [
        {"id": "chat.send", "label": "Enviar mensagem ao Jarvis", "mutating": False},
        {"id": "task.create", "label": "Criar tarefa", "mutating": True, "requires_confirmation": True},
        {"id": "run.pause", "label": "Pausar execução", "mutating": True, "requires_confirmation": True},
        {"id": "run.resume", "label": "Retomar execução", "mutating": True, "requires_confirmation": True},
        {"id": "run.approve", "label": "Aprovar gate humano", "mutating": True, "requires_confirmation": True},
        {"id": "run.retry", "label": "Refazer execução", "mutating": True, "requires_confirmation": True},
        {"id": "search.global", "label": "Buscar no projeto", "mutating": False},
    ]

def run_diff(run_id: str) -> dict:
    """Exibe somente diff local; não executa comandos fornecidos pelo usuário."""
    result = subprocess.run(["git", "diff", "--no-ext-diff", "--unified=3"], cwd=ROOT, text=True, capture_output=True, timeout=30)
    return {"run_id": run_id, "available": result.returncode == 0, "diff": result.stdout[-200000:] if result.returncode == 0 else "", "error": _safe_summary(result.stderr) if result.returncode else None, "content_policy": "local_diff_only"}

def settings_view() -> dict:
    rows = _read_jsonl(SETTINGS_STORE)
    current = next((row for row in reversed(rows) if row.get("status") == "APPLIED"), None)
    return {"schema_version": "1.0.0", "current": current, "revisions": [{"revision_id": row.get("revision_id"), "status": row.get("status"), "created_at": row.get("created_at"), "content_hash": row.get("content_hash")} for row in rows[-50:]]}

def projects_view() -> dict:
    if not PROJECTS_CONFIG.is_file():
        return {"projects": [], "active_project_id": None}
    try:
        data = json.loads(PROJECTS_CONFIG.read_text(encoding="utf-8"))
        projects = data.get("projects", [])
        active = None
        if ACTIVE_PROJECT_STORE.is_file():
            active = json.loads(ACTIVE_PROJECT_STORE.read_text(encoding="utf-8")).get("project_id")
        if not active and projects:
            active = projects[0].get("project_id")
        safe = [{key: item.get(key) for key in ("project_id", "name", "repository_root", "default_branch", "rag_scope", "allowed_agents", "allowed_integrations", "policy_ref")} for item in projects]
        return {"projects": safe, "active_project_id": active}
    except (OSError, json.JSONDecodeError):
        return {"projects": [], "active_project_id": None, "error": "registro de projetos inválido"}


def project_by_id(project_id: str) -> dict | None:
    return next((item for item in projects_view().get("projects", []) if item.get("project_id") == project_id), None)


def select_project(project_id: str) -> dict:
    project = project_by_id(project_id)
    if not project:
        raise ValueError("projeto não encontrado")
    ACTIVE_PROJECT_STORE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_PROJECT_STORE.write_text(json.dumps({"project_id": project_id, "selected_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit_action("PROJECT_SELECTED", None, {"project_id": project_id}, {"status": "SELECTED", "project_id": project_id})
    return {"project": project, "active_project_id": project_id}


def integrations_view() -> dict:
    if not INTEGRATIONS_STORE.is_file(): return {"integrations": []}
    try:
        data = json.loads(INTEGRATIONS_STORE.read_text(encoding="utf-8"))
        return {"integrations": [{"id": item.get("id"), "type": item.get("type"), "enabled": bool(item.get("enabled", False)), "endpoint_ref": item.get("endpoint_ref"), "capabilities": item.get("capabilities", []), "health": "NOT_CHECKED"} for item in data.get("integrations", [])]}
    except (OSError, json.JSONDecodeError): return {"integrations": [], "error": "registro de integrações inválido"}

def integration_by_id(integration_id: str) -> dict | None:
    return next((item for item in integrations_view().get("integrations", []) if item.get("id") == integration_id), None)

def integration_health(integration_id: str) -> dict:
    item = integration_by_id(integration_id)
    if not item: raise ValueError("integração não encontrada")
    result = {"integration_id": integration_id, "status": "DISABLED" if not item.get("enabled") else "NOT_CONFIGURED", "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "external_call": False}
    if item.get("enabled") and item.get("type") == "MCP" and item.get("endpoint_ref") == "redmine":
        try:
            mcp = _redmine_mcp_call("ping")
            result.update({"status": "HEALTHY", "external_call": False, "protocol": "MCP", "server": mcp.get("server")})
        except (OSError, RuntimeError, ValueError) as exc:
            result.update({"status": "UNAVAILABLE", "error": _safe_summary(str(exc)), "protocol": "MCP"})
    audit_action("INTEGRATION_HEALTH_CHECK", None, {"integration_id": integration_id}, result)
    return result

def integration_call(integration_id: str, payload: dict) -> dict:
    item = integration_by_id(integration_id)
    if not item: raise ValueError("integração não encontrada")
    capability = str(payload.get("capability", "")).strip()
    if not capability or capability not in set(item.get("capabilities", [])): raise ValueError("capability não autorizada")
    if payload.get("confirm") is not True: raise ValueError("chamada exige confirmação explícita")
    result = {"integration_id": integration_id, "capability": capability, "status": "NOT_IMPLEMENTED", "external_call": False, "reason": "nenhum adaptador externo habilitado"}
    if item.get("type") == "MCP" and item.get("endpoint_ref") == "redmine":
        if not capability.startswith("redmine.read."):
            raise ValueError("somente capabilities redmine.read.* são permitidas pela Dashboard")
        tool = capability.removeprefix("redmine.read.")
        if tool not in {"get_issue", "list_issues", "get_current_user", "list_projects", "list_metadata"}:
            raise ValueError("ferramenta Redmine não autorizada")
        result = {"integration_id": integration_id, "capability": capability, "status": "OK", "external_call": True, "data": _redmine_mcp_call("tools/call", {"name": tool, "arguments": payload.get("arguments", {})})}
    audit_action("INTEGRATION_CALL_ATTEMPT", None, {"integration_id": integration_id, "capability": capability}, result)
    return result

def _redmine_mcp_call(method: str, params: dict | None = None) -> dict:
    if not REDMINE_MCP.is_file():
        raise RuntimeError("servidor MCP Redmine não encontrado")
    if not os.environ.get("REDMINE_API_KEY"):
        raise RuntimeError("REDMINE_API_KEY não disponível no processo da Dashboard")
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "jarvis-dashboard", "version": "1.0.0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": method, "params": params or {}},
    ]
    process = subprocess.run(["node", str(REDMINE_MCP)], input="\n".join(json.dumps(item) for item in messages) + "\n", text=True, capture_output=True, timeout=30, env=os.environ.copy(), cwd=str(ROOT))
    if process.returncode != 0:
        raise RuntimeError(_safe_summary(process.stderr or "MCP Redmine encerrou com erro"))
    responses = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
    response = next((item for item in reversed(responses) if item.get("id") == 2), None)
    if not response or "error" in response:
        raise RuntimeError(_safe_summary(json.dumps(response or {}, ensure_ascii=False)))
    if method == "ping":
        return {"server": "redmine-sesab", "protocol": "MCP"}
    return response.get("result", {})

def register_integration(payload: dict) -> dict:
    required = ("id", "type", "capabilities", "authorization", "timeout_ms")
    if any(key not in payload for key in required): raise ValueError("integração incompleta")
    integration = dict(payload); integration.setdefault("schema_version", "1.0.0"); integration.setdefault("enabled", False); integration.setdefault("audit", True)
    if integration["type"] not in {"MCP", "LOCAL_ADAPTER"} or not isinstance(integration["capabilities"], list) or integration["authorization"].get("mode") == "APPROVED" and integration["enabled"] is not True:
        raise ValueError("integração inválida ou autorização inconsistente")
    if integration["audit"] is not True or not 100 <= int(integration["timeout_ms"]) <= 120000: raise ValueError("integração exige auditoria e timeout válido")
    current = []
    if INTEGRATIONS_STORE.is_file():
        try: current = json.loads(INTEGRATIONS_STORE.read_text(encoding="utf-8")).get("integrations", [])
        except (OSError, json.JSONDecodeError): pass
    current = [item for item in current if item.get("id") != integration["id"]] + [integration]
    INTEGRATIONS_STORE.parent.mkdir(parents=True, exist_ok=True)
    INTEGRATIONS_STORE.write_text(json.dumps({"schema_version": "1.0.0", "integrations": current}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    safe = {key: integration.get(key) for key in ("id", "type", "enabled", "endpoint_ref", "capabilities", "authorization", "timeout_ms", "audit")}
    audit_action("INTEGRATION_REGISTERED", None, safe, {"status": "REGISTERED", "integration_id": integration["id"], "enabled": integration["enabled"]})
    return safe

def create_settings_draft(payload: dict) -> dict:
    allowed = {"policy", "rag", "models", "limits", "agents", "integrations"}
    values = {key: payload[key] for key in allowed if key in payload}
    if not values: raise ValueError("draft sem configurações")
    serialized = json.dumps(values, sort_keys=True, ensure_ascii=False)
    draft = {"revision_id": "settings-" + uuid.uuid4().hex, "status": "DRAFT", "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "content_hash": _hash(serialized), "content": values, "requires_approval": True}
    _append_jsonl(SETTINGS_STORE, draft)
    return {key: value for key, value in draft.items() if key != "content"} | {"content": values}

def _settings_revision(revision_id: str) -> dict | None:
    return next((row for row in _read_jsonl(SETTINGS_STORE) if row.get("revision_id") == revision_id), None)

def _update_revision(revision_id: str, status: str, reason: str | None = None) -> dict:
    rows = _read_jsonl(SETTINGS_STORE); found = None
    for row in rows:
        if row.get("revision_id") == revision_id:
            row["status"] = status; row["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            if reason: row["reason"] = _safe_summary(reason)
            found = row
    if not found: raise ValueError("revisão não encontrada")
    _write_jsonl(SETTINGS_STORE, rows)
    return found

def apply_settings_revision(revision_id: str, payload: dict) -> dict:
    if payload.get("confirm") is not True: raise ValueError("aplicação exige confirmação explícita")
    revision = _settings_revision(revision_id)
    if not revision or revision.get("status") not in {"DRAFT", "ROLLED_BACK"}: raise ValueError("revisão não está disponível para aplicação")
    active = ROOT / ".jarvis" / "dashboard" / "active-settings.json"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_text(json.dumps({"revision_id": revision_id, "content": revision.get("content", {})}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _update_revision(revision_id, "APPLIED", payload.get("reason"))

def rollback_settings_revision(revision_id: str, payload: dict) -> dict:
    if payload.get("confirm") is not True: raise ValueError("rollback exige confirmação explícita")
    revision = _settings_revision(revision_id)
    if not revision or revision.get("status") != "APPLIED": raise ValueError("somente revisão aplicada pode sofrer rollback")
    active = ROOT / ".jarvis" / "dashboard" / "active-settings.json"
    if active.exists(): active.unlink()
    return _update_revision(revision_id, "ROLLED_BACK", payload.get("reason"))


def evidence(db: Path, query: dict[str, list[str]]) -> dict:
    if not db.is_file():
        return {"items": []}
    connection = sqlite3.connect(db)
    try:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute("SELECT * FROM findings ORDER BY rowid DESC LIMIT 200")]
        invocations = {row["invocation_id"]: dict(row) for row in connection.execute("SELECT * FROM agent_invocations") if "invocation_id" in row.keys()}
    finally:
        connection.close()
    if query.get("q"):
        term = query["q"][0].lower()
        rows = [row for row in rows if term in json.dumps(row, ensure_ascii=False).lower()]
    nodes, edges = [], []
    for row in rows:
        finding_id = row.get("finding_id") or "finding-" + str(row.get("rowid", len(nodes)))
        producer = invocations.get(row.get("invocation_id"), {})
        producer_id = "agent:" + str(producer.get("agent", "UNKNOWN"))
        nodes.extend([{"id": finding_id, "type": "finding", "label": row.get("category", "finding"), "severity": row.get("severity", "UNKNOWN")}, {"id": producer_id, "type": "agent", "label": producer.get("agent", "UNKNOWN")}])
        edges.append({"from": producer_id, "to": finding_id, "relation": "PRODUCED"})
        if row.get("evidence_ref"):
            ref = str(row["evidence_ref"])[:500]; ref_id = "ref:" + _hash(ref)
            nodes.append({"id": ref_id, "type": "evidence_ref", "label": ref})
            edges.append({"from": finding_id, "to": ref_id, "relation": "SUPPORTED_BY"})
    unique_nodes = {node["id"]: node for node in nodes}
    return {"items": rows, "graph": {"nodes": list(unique_nodes.values()), "edges": edges, "content_policy": "references_and_metadata_only"}}


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
        if path == "/api/dashboard":
            project_id = parse_qs(urlparse(self.path).query).get("project_id", [None])[0]
            if not project_id: return self.send(400, json.dumps({"error": "project_id obrigatório"}, ensure_ascii=False), "application/json; charset=utf-8")
            try: _require_project(project_id)
            except ValueError as exc: return self.send(400, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            data = dashboard(self.db); data["project_id"] = project_id
            return self.send(200, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/projects": return self.send(200, json.dumps(projects_view(), ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/projects/"):
            project = project_by_id(path.rsplit("/", 1)[-1])
            return self.send(200 if project else 404, json.dumps(project or {"error": "projeto não encontrado"}, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/runs": return self.send(200, json.dumps({"runs": filtered_runs(self.db, parse_qs(urlparse(self.path).query))}, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/attention": return self.send(200, json.dumps(attention(self.db), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/agents": return self.send(200, json.dumps(agents_summary(self.db), ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/agents/"):
            agent = path.rsplit("/", 1)[-1]
            return self.send(200, json.dumps(agent_detail(self.db, agent), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/models/usage": return self.send(200, json.dumps(models_usage(self.db, query), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/metrics/series": return self.send(200, json.dumps(metrics_series(self.db, query), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/evidence": return self.send(200, json.dumps(evidence(self.db, query), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/search": return self.send(200, json.dumps(global_search(query.get("q", [""])[0], self.db), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/commands": return self.send(200, json.dumps({"commands": available_commands()}, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/settings": return self.send(200, json.dumps(settings_view(), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/integrations": return self.send(200, json.dumps(integrations_view(), ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/integrations/") and path.endswith("/health"):
            integration_id = path.split("/")[-2]
            try: result = integration_health(integration_id)
            except ValueError as exc: return self.send(404, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            return self.send(200, json.dumps(result, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/chat/sessions":
            project_id = parse_qs(urlparse(self.path).query).get("project_id", [None])[0]
            if not project_id: return self.send(400, json.dumps({"error": "project_id obrigatório"}, ensure_ascii=False), "application/json; charset=utf-8")
            try: _require_project(project_id)
            except ValueError as exc: return self.send(400, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            return self.send(200, json.dumps({"sessions": chat_sessions(project_id=project_id), "project_id": project_id}, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/chat/sessions/"):
            session_id = path.split("/")[-1]
            project_id = parse_qs(urlparse(self.path).query).get("project_id", [None])[0]
            if not project_id: return self.send(400, json.dumps({"error": "project_id obrigatório"}, ensure_ascii=False), "application/json; charset=utf-8")
            rows = chat_sessions(session_id, project_id)
            return self.send(200 if rows else 404, json.dumps(rows[0] if rows else {"error": "sessão não encontrada"}, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/audit": return self.send(200, json.dumps({"items": _read_jsonl(AUDIT_STORE)[-200:]}, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/runs/") and path.endswith("/diff"):
            run_id = path.split("/")[-2]
            return self.send(200, json.dumps(run_diff(run_id), ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/runs/") and path.endswith("/events"):
            run_id = path.split("/")[-2]
            events_path = ROOT / ".jarvis" / "runs" / run_id / "events.jsonl"
            if not events_path.is_file(): return self.send(404, json.dumps({"error": "eventos não encontrados"}, ensure_ascii=False), "application/json; charset=utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/event-stream; charset=utf-8"); self.send_header("Cache-Control", "no-cache"); self.send_header("Connection", "close"); self.end_headers()
            for index, line in enumerate(events_path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]):
                try:
                    event = json.loads(line)
                    safe = {key: event.get(key) for key in ("event", "at", "run_id", "state", "stage", "agent", "status", "termination_reason") if event.get(key) is not None}
                    self.wfile.write(f"id: {index}\ndata: {json.dumps(safe, ensure_ascii=False)}\n\n".encode("utf-8"))
                except (json.JSONDecodeError, BrokenPipeError): break
            return
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
        if path.startswith("/api/projects/") and path.endswith("/select"):
            project_id = path.split("/")[-2]
            try: result = select_project(project_id)
            except ValueError as exc: return self.send(404, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            return self.send(200, json.dumps(result, ensure_ascii=False), "application/json; charset=utf-8")
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
        if path == "/api/chat/sessions":
            try: session = create_session(str(payload.get("project_id") or ""), payload.get("task_id"))
            except ValueError as exc: return self.send(400, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            return self.send(201, json.dumps(session, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/settings/drafts":
            try: draft = create_settings_draft(payload)
            except ValueError as exc: return self.send(400, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            audit_action("SETTINGS_DRAFT_CREATED", None, payload, {"revision_id": draft["revision_id"], "status": draft["status"]})
            return self.send(201, json.dumps(draft, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/integrations":
            try: integration = register_integration(payload)
            except (ValueError, TypeError) as exc: return self.send(400, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            return self.send(201, json.dumps(integration, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/settings/revisions/") and path.endswith("/apply"):
            revision_id = path.split("/")[-2]
            try: revision = apply_settings_revision(revision_id, payload)
            except ValueError as exc: return self.send(409, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            audit_action("SETTINGS_APPLIED", None, payload, {"revision_id": revision_id, "status": revision["status"]})
            return self.send(200, json.dumps({"ok": True, "revision_id": revision_id, "status": revision["status"]}, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/settings/revisions/") and path.endswith("/rollback"):
            revision_id = path.split("/")[-2]
            try: revision = rollback_settings_revision(revision_id, payload)
            except ValueError as exc: return self.send(409, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            audit_action("SETTINGS_ROLLED_BACK", None, payload, {"revision_id": revision_id, "status": revision["status"]})
            return self.send(200, json.dumps({"ok": True, "revision_id": revision_id, "status": revision["status"]}, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/integrations/") and path.endswith("/health-check"):
            integration_id = path.split("/")[-2]
            try: result = integration_health(integration_id)
            except ValueError as exc: return self.send(404, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            return self.send(200, json.dumps(result, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/integrations/") and path.endswith("/calls"):
            integration_id = path.split("/")[-2]
            try: result = integration_call(integration_id, payload)
            except ValueError as exc: return self.send(403, json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json; charset=utf-8")
            return self.send(501, json.dumps(result, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/chat/sessions/") and path.endswith("/messages"):
            session_id = path.split("/")[-2]; project_id = str(payload.get("project_id") or ""); rows = chat_sessions(session_id, project_id)
            if not project_id: return self.send(400, json.dumps({"error": "project_id obrigatório"}, ensure_ascii=False), "application/json; charset=utf-8")
            if not rows: return self.send(404, json.dumps({"error": "sessão não encontrada"}, ensure_ascii=False), "application/json; charset=utf-8")
            message = str(payload.get("message", "")).strip()
            if not message or len(message) > 12000: return self.send(400, json.dumps({"error": "message inválida"}, ensure_ascii=False), "application/json; charset=utf-8")
            session = rows[0]; entry = {"role": "user", "project_id": project_id, "message_hash": _hash(message), "summary": _safe_summary(message), "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            command = [sys.executable, str(ROOT / "scripts" / "jarvis_chat.py"), message, "--database", str(ROOT / ".jarvis/rag/index.db"), "--context-budget", "SMALL"]
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=60)
            if result.returncode:
                response = {"status": "ERROR", "summary": _safe_summary(result.stderr or "falha no chat"), "message_hash": _hash(result.stderr or "")}
            else:
                try: data = json.loads(result.stdout); response = {"status": "READY", "summary": "RAG consultado antes do planejamento", "message_hash": _hash(result.stdout), "rag": {"retrieved": data.get("rag", {}).get("retrieved", False), "query_id": data.get("rag", {}).get("query_id")}, "metrics": data.get("metrics", {})}
                except json.JSONDecodeError: response = {"status": "READY", "summary": "resposta recebida", "message_hash": _hash(result.stdout)}
            response["project_id"] = project_id; entry["response"] = response; session.setdefault("messages", []).append(entry)
            _write_jsonl(CHAT_STORE, [session if row.get("session_id") == session_id else row for row in _read_jsonl(CHAT_STORE)])
            return self.send(200, json.dumps({"session_id": session_id, "message": entry}, ensure_ascii=False), "application/json; charset=utf-8")
        if path.startswith("/api/runs/") and path.endswith("/actions"):
            run_id = path.split("/")[-2]; action = str(payload.get("action", "")).upper(); allowed = {"PAUSE", "RESUME", "APPROVE", "RETRY"}
            if action not in allowed: return self.send(400, json.dumps({"error": "ação inválida"}, ensure_ascii=False), "application/json; charset=utf-8")
            if payload.get("confirm") is not True: return self.send(400, json.dumps({"error": "ação exige confirmação explícita"}, ensure_ascii=False), "application/json; charset=utf-8")
            payload.setdefault("idempotency_key", _hash(f"{run_id}:{action}:{payload.get('reason', '')}"))
            previous = next((row for row in reversed(_read_jsonl(AUDIT_STORE)) if row.get("action") == action and row.get("run_id") == run_id and row.get("idempotency_key") == payload["idempotency_key"]), None)
            if previous: return self.send(200, json.dumps(previous.get("result", {}), ensure_ascii=False), "application/json; charset=utf-8")
            run_dir = ROOT / ".jarvis" / "runs" / run_id
            state_path = run_dir / "state.json"
            if not state_path.is_file(): return self.send(404, json.dumps({"error": "execução não encontrada"}, ensure_ascii=False), "application/json; charset=utf-8")
            state = json.loads(state_path.read_text(encoding="utf-8")); current = state.get("current_state", "UNKNOWN")
            if action == "PAUSE": target = "PAUSED"
            elif action == "RESUME": target = state.get("pause_resume_state") or "IMPLEMENTING"
            elif action == "APPROVE": target = "HOMOLOGATION_READY" if current == "HUMAN_GATE" else "IMPLEMENTING"
            else: target = "IMPLEMENTING"
            command = [sys.executable, str(RUNTIME), "transition", "--run-dir", str(run_dir), "--to", target, "--reason", _safe_summary(payload.get("reason") or f"dashboard action {action}")]
            if action == "APPROVE" and current == "HUMAN_GATE": command.extend(["--gate-decision", "APPROVED", "--gate-reason-code", "APPROVED_AS_PLANNED"])
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=60)
            output = {"ok": result.returncode == 0, "action": action, "run_id": run_id, "state": target, "error": _safe_summary(result.stderr) if result.returncode else None}
            audit_action(action, run_id, payload, output)
            if result.returncode == 0:
                try: save_checkpoint(run_id, json.loads(state_path.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError): pass
            return self.send(200 if result.returncode == 0 else 409, json.dumps(output, ensure_ascii=False), "application/json; charset=utf-8")
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
