import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import type { Project } from '../../types/api';

type Props = { project?: Project; projectId: string };

export function CheckpointPage({ project, projectId }: Props) {
  const query = useQuery({ queryKey: ['checkpoints', projectId], queryFn: () => api.runs(projectId), enabled: Boolean(projectId) });
  return <section className="mx-auto grid max-w-5xl gap-5 px-4 pb-10 sm:px-6 lg:px-12"><div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel"><div className="text-[10px] font-bold uppercase tracking-[0.18em] text-blue-500">{project?.name || 'Projeto não selecionado'}</div><h2 className="mt-2 text-2xl font-bold text-slate-900">Checkpoints</h2><p className="mt-2 text-sm leading-6 text-slate-500">Execuções recentes que podem ser inspecionadas ou retomadas pelo Runtime V3.</p></div>{query.isLoading && <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500">Carregando checkpoints…</div>}{query.error && <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-8 text-sm text-red-700">Não foi possível carregar os checkpoints.</div>}{!query.isLoading && !query.error && <div className="grid gap-3">{query.data?.runs?.length ? query.data.runs.map((run) => <article key={run.run_id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-panel"><div><strong className="block text-sm text-slate-800">{run.task_id || run.run_id}</strong><span className="text-xs text-slate-500">{run.status || 'UNKNOWN'} · {run.started_at || 'data não informada'}</span></div><Link to={`/tasks/${encodeURIComponent(run.run_id)}`} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100">Abrir checkpoint</Link></article>) : <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">Nenhuma execução com checkpoint encontrada.</div>}</div>}</section>;
}
