import type { ChatMessage } from '../../types/api';
import { usePreservedScroll } from '../../hooks/usePreservedScroll';
import { ResponseCard } from './ResponseCard';

type Props = { messages: ChatMessage[]; section: string; onSuggestion: (value: string) => void };

export function ConversationView({ messages, section, onSuggestion }: Props) {
  const scroll = usePreservedScroll<HTMLDivElement>();
  if (messages.length) return <div ref={scroll.ref} onScroll={scroll.onScroll} className="max-h-[min(58vh,680px)] space-y-4 overflow-y-auto pr-2" aria-live="polite">{messages.map((message, index) => <div className={`flex gap-3 rounded-2xl border p-5 shadow-panel ${message.role === 'user' ? 'ml-auto max-w-2xl border-blue-100 bg-blue-50' : 'mx-auto max-w-3xl border-slate-200 bg-white'}`} key={`${message.project_id}-${index}`}><div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-blue-600 to-violet-600 font-extrabold text-white">{message.role === 'user' ? 'Você' : 'A'}</div><div className="min-w-0"><b className="text-sm text-slate-900">{message.role === 'user' ? 'Você' : 'AGHUse Assistant'}</b><p className="mt-2 whitespace-pre-wrap leading-7 text-slate-600">{message.summary || message.response?.summary || 'Mensagem recebida.'}</p>{message.response && <ResponseCard response={message.response} />}</div></div>)}</div>;
  const suggestions = ['Analise o projeto', 'Mostre minhas tarefas recentes', 'Consulte o RAG'];
  return <div className="mx-auto max-w-2xl py-14 text-center text-slate-500" aria-live="polite"><div className="mb-3 text-4xl text-violet-600">✦</div><h2 className="m-0 text-xl font-bold text-slate-900">{section === 'Workspace' ? 'Comece uma conversa' : section}</h2><p className="mt-2">Peça uma análise, crie um plano ou retome uma tarefa.</p><div className="mt-6 flex flex-wrap justify-center gap-2">{suggestions.map((suggestion) => <button className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-sm text-slate-600 transition hover:border-blue-300 hover:text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500" key={suggestion} onClick={() => onSuggestion(suggestion)}>{suggestion}</button>)}</div></div>;
}
