import { useQuery } from '@tanstack/react-query';
import { api } from '../../services/api';
import type { Project } from '../../types/api';

type Kind = 'agents' | 'logs' | 'evidence' | 'models' | 'integrations' | 'settings';
type Props = { kind: Kind; title: string; description: string; project?: Project; projectId: string };
const labels: Record<Kind, string[]> = { agents: ['agents', 'items', 'total'], logs: ['series', 'events', 'items'], evidence: ['items', 'findings', 'references'], models: ['models', 'series', 'items'], integrations: ['integrations', 'items', 'capabilities'], settings: ['revisions', 'drafts', 'items'] };

export function ObservedModulePage({ kind, title, description, project, projectId }: Props) {
  const query = useQuery({ queryKey: [kind, projectId], queryFn: () => api[kind](projectId), enabled: Boolean(projectId) });
  const data = query.data || {};
  const cards = labels[kind].map((label) => { const value = data[label]; return [label, Array.isArray(value) ? value.length : typeof value === 'number' ? value : typeof value === 'object' && value ? Object.keys(value).length : value == null ? '—' : String(value)]; });
  return <section className="mx-auto grid max-w-5xl gap-5 px-4 pb-10 sm:px-6 lg:px-12"><div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel"><div className="text-[10px] font-bold uppercase tracking-[0.18em] text-blue-500">{project?.name || 'Projeto não selecionado'}</div><h2 className="mt-2 text-2xl font-bold text-slate-900">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-500">{description}</p></div>{query.isLoading && <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500">Carregando dados observados…</div>}{query.error && <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-8 text-sm text-red-700">Não foi possível carregar este módulo.</div>}{!query.isLoading && !query.error && <div className="grid gap-4 sm:grid-cols-3">{cards.map(([label, value]) => <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel"><span className="text-xs capitalize text-slate-400">{label}</span><strong className="mt-2 block text-2xl text-slate-900">{value}</strong></div>)}</div>}</section>;
}
