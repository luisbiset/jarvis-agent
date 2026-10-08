import type { ChatSession } from '../../types/api';

type Props = { sessions: ChatSession[]; activeSessionId?: string; collapsed: boolean; onSelect: (session: ChatSession) => void; onNew: () => void };

export function SessionList({ sessions, activeSessionId, collapsed, onSelect, onNew }: Props) {
  if (collapsed) return null;
  return <div className="mt-5 border-t border-slate-100 pt-4"><div className="mb-2 flex items-center justify-between px-2.5"><span className="text-[10px] font-bold tracking-wider text-slate-400">CONVERSAS</span><button className="text-xs font-bold text-blue-600 hover:text-blue-700" onClick={onNew} aria-label="Nova conversa">+</button></div><div className="grid max-h-36 gap-1 overflow-y-auto">{sessions.slice(0, 8).map((session) => <button className={`truncate rounded-lg px-2.5 py-2 text-left text-xs ${session.session_id === activeSessionId ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:bg-slate-50'}`} key={session.session_id} onClick={() => onSelect(session)}>{session.messages?.find((message) => message.role === 'user')?.summary || 'Nova conversa'}</button>)}</div></div>;
}
