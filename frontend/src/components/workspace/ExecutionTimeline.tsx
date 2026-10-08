import type { RunEvent, WorkspaceAction } from '../../types/api';

type Props = { events: RunEvent[]; pending?: boolean; onAction?: (action: WorkspaceAction) => void };

const actions: WorkspaceAction[] = ['PAUSE', 'RESUME', 'APPROVE', 'RETRY'];

export function ExecutionTimeline({ events, pending, onAction }: Props) {
  if (!events.length && !onAction) return null;
  return <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-panel" aria-label="Timeline da execução"><div className="mb-3 flex items-center justify-between"><h3 className="text-sm font-bold text-slate-800">Execução</h3>{pending && <span className="text-xs text-blue-600">Atualizando…</span>}</div>{events.length ? <ol className="grid gap-2">{events.map((event, index) => <li key={`${event.at || 'event'}-${event.event || index}-${index}`} className="flex gap-3 text-xs"><span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-blue-500" /><span><strong className="text-slate-700">{event.event || event.target || event.status || 'EVENTO'}</strong><span className="ml-2 text-slate-400">{event.at || 'agora'}</span>{event.reason && <span className="block text-slate-500">{event.reason}</span>}</span></li>)}</ol> : <p className="text-xs text-slate-500">A execução foi criada; aguardando os primeiros eventos.</p>}{onAction && <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-3">{actions.map((action) => <button key={action} type="button" disabled={pending} onClick={() => onAction(action)} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50">{action}</button>)}</div>}</section>;
}
