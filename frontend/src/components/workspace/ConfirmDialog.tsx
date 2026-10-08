import { useEffect, useRef } from 'react';
type Props = { action: string; pending?: boolean; onCancel: () => void; onConfirm: () => void };

export function ConfirmDialog({ action, pending, onCancel, onConfirm }: Props) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { confirmRef.current?.focus(); }, []);
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/30 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !pending) onCancel(); }}><div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="confirm-title"><h2 id="confirm-title" className="text-lg font-bold text-slate-900">Confirmar ação</h2><p className="mt-2 text-sm leading-6 text-slate-500">Você está solicitando <strong className="text-slate-700">{action}</strong> para a execução atual. A ação será registrada na auditoria.</p><div className="mt-6 flex justify-end gap-2"><button type="button" disabled={pending} onClick={onCancel} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50">Cancelar</button><button ref={confirmRef} type="button" disabled={pending} onClick={onConfirm} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{pending ? 'Enviando…' : 'Confirmar'}</button></div></div></div>;
}
