import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../services/api';
import type { Project, WorkspaceAction } from '../../types/api';
import { useRunEvents } from '../../hooks/useRunEvents';
import { ConfirmDialog } from './ConfirmDialog';
import { ExecutionTimeline } from './ExecutionTimeline';

type Props = { project?: Project; projectId: string; runId: string };

export function TaskDetailPage({ project, projectId, runId }: Props) {
  const detail = useQuery({ queryKey: ['run', projectId, runId], queryFn: () => api.run(projectId, runId), enabled: Boolean(projectId && runId) });
  const diff = useQuery({ queryKey: ['run-diff', projectId, runId], queryFn: () => api.diff(projectId, runId), enabled: Boolean(projectId && runId) });
  const events = useRunEvents(projectId, runId);
  const [pendingAction, setPendingAction] = useState<WorkspaceAction>();
  const [actionError, setActionError] = useState<string>();
  const confirmAction = async () => {
    if (!pendingAction) return;
    try {
      await api.runAction(projectId, runId, pendingAction, `Ação solicitada no detalhe da tarefa: ${pendingAction}`);
      setPendingAction(undefined);
      setActionError(undefined);
      await detail.refetch();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Não foi possível executar a ação.');
    }
  };
  const run = detail.data?.run || {};
  const checkpoint = detail.data?.checkpoint;
  const diffLines = diff.data?.diff?.split('\n') || [];
  return <section className="mx-auto grid max-w-5xl gap-5 px-4 pb-10 sm:px-6 lg:px-12">
    <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel">
      <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-blue-500">{project?.name || 'Projeto não selecionado'}</div>
      <h2 className="mt-2 text-2xl font-bold text-slate-900">Detalhe da tarefa</h2>
      <p className="mt-2 text-sm text-slate-500">Run: <code>{runId}</code></p>
    </header>
    {detail.isLoading && <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500">Carregando execução…</div>}
    {detail.error && <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-8 text-sm text-red-700">Não foi possível carregar esta execução.</div>}
    {actionError && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{actionError}</div>}
    {detail.data && <>
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel">
        <div className="grid gap-4 sm:grid-cols-4">
          <Stat label="Status" value={String(run.status || 'UNKNOWN')} />
          <Stat label="Risco" value={String(run.risk_class || 'UNKNOWN')} />
          <Stat label="Task" value={String(run.task_id || runId)} />
          <Stat label="Findings" value={String(detail.data.findings?.length ?? 0)} />
        </div>
      </div>
      <section className="rounded-2xl border border-violet-100 bg-violet-50 p-5 shadow-panel" aria-labelledby="checkpoint-title">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h3 id="checkpoint-title" className="font-bold text-violet-900">Checkpoint</h3><p className="mt-1 text-sm text-violet-700">{checkpoint ? `Snapshot ${checkpoint.created_at || 'sem data'} · estado ${String(checkpoint.state?.current_state || run.status || 'UNKNOWN')}` : 'Nenhum snapshot disponível para esta execução.'}</p></div>
          {checkpoint && <button className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-bold text-white hover:bg-violet-700" onClick={() => setPendingAction('RESUME')}>Retomar checkpoint</button>}
        </div>
      </section>
      <ExecutionTimeline events={events.length ? events : detail.data.timeline || []} pending={detail.isFetching} onAction={setPendingAction} />
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel" aria-labelledby="diff-title">
        <h3 id="diff-title" className="font-bold text-slate-800">Diff da execução</h3>
        {diff.isLoading && <p className="mt-3 text-sm text-slate-500">Carregando diff…</p>}
        {!diff.isLoading && diff.data?.available && <pre className="mt-3 max-h-96 overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-5 text-slate-200">{diffLines.length ? diffLines.join('\n') : 'Nenhuma alteração registrada.'}</pre>}
        {!diff.isLoading && !diff.data?.available && <p className="mt-3 text-sm text-slate-500">Diff não disponível.</p>}
      </section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel" aria-labelledby="findings-title">
        <h3 id="findings-title" className="font-bold text-slate-800">Findings</h3>
        {detail.data.findings?.length ? <div className="mt-3 grid gap-2">{detail.data.findings.map((finding, index) => <div className="rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-900" key={String(finding.id || index)}>{String(finding.summary || finding.title || finding.message || 'Finding registrado')}</div>)}</div> : <p className="mt-3 text-sm text-slate-500">Nenhum finding registrado.</p>}
      </section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel" aria-labelledby="tests-title">
        <h3 id="tests-title" className="font-bold text-slate-800">Testes executados</h3>
        {detail.data.tests?.length ? <div className="mt-3 grid gap-2">{detail.data.tests.map((test, index) => <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm" key={String(test.execution_id || index)}><span className="text-slate-700">{String(test.agent_type || 'Agent')} · tentativa {String(test.attempt_number || 1)}</span><span className={Number(test.tests_failed || 0) ? 'font-bold text-red-700' : 'font-bold text-emerald-700'}>{String(test.tests_passed || 0)} aprovados · {String(test.tests_failed || 0)} falhos</span></div>)}</div> : <p className="mt-3 text-sm text-slate-500">Nenhum teste observado para esta execução.</p>}
      </section>
    </>}
    {pendingAction && <ConfirmDialog action={pendingAction} onCancel={() => setPendingAction(undefined)} onConfirm={confirmAction} />}
  </section>;
}

function Stat({ label, value }: { label: string; value: string }) { return <div><span className="text-xs text-slate-400">{label}</span><strong className="block truncate text-slate-800">{value}</strong></div>; }
