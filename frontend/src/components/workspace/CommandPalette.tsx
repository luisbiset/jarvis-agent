import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

type Props = { open: boolean; onClose: () => void; onNewSession: () => void };
const commands = [['Abrir Workspace', '/workspace'], ['Ver tarefas', '/tasks'], ['Abrir agents', '/agents'], ['Ver checkpoints', '/checkpoints'], ['Consultar RAG', '/rag'], ['Abrir logs', '/logs'], ['Ver evidências', '/evidence'], ['Modelos e custos', '/models'], ['Integrações', '/integrations'], ['Configurações', '/settings']] as const;

export function CommandPalette({ open, onClose, onNewSession }: Props) {
  const [query, setQuery] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const filtered = useMemo(() => commands.filter(([label]) => label.toLowerCase().includes(query.toLowerCase())), [query]);
  useEffect(() => { if (open) { setQuery(''); input.current?.focus(); } }, [open]);
  useEffect(() => { const listener = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); if (!open) input.current?.focus(); } if (event.key === 'Escape' && open) onClose(); }; window.addEventListener('keydown', listener); return () => window.removeEventListener('keydown', listener); }, [open, onClose]);
  if (!open) return null;
  return <div className="fixed inset-0 z-40 bg-slate-950/20 p-4 pt-[12vh]" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><div className="mx-auto max-w-xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl" role="dialog" aria-modal="true" aria-label="Command Palette"><div className="border-b border-slate-100 p-3"><input ref={input} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar uma ação…" aria-label="Buscar comando" className="w-full rounded-lg bg-slate-50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500" /></div><div className="max-h-80 overflow-y-auto p-2"><button type="button" className="mb-1 w-full rounded-lg px-3 py-2 text-left text-sm font-semibold text-blue-600 hover:bg-blue-50" onClick={() => { onNewSession(); onClose(); navigate('/workspace'); }}>＋ Nova sessão</button>{filtered.map(([label, path]) => <button type="button" key={path} className="block w-full rounded-lg px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-50 hover:text-blue-600" onClick={() => { navigate(path); onClose(); }}>{label}</button>)}{!filtered.length && <p className="px-3 py-5 text-center text-sm text-slate-500">Nenhum comando encontrado.</p>}</div><div className="border-t border-slate-100 px-3 py-2 text-[11px] text-slate-400">Enter para abrir · Esc para fechar</div></div></div>;
}
