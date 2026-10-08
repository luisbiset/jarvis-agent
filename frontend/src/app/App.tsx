import { FormEvent, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { ContextPanel } from '../components/context/ContextPanel';
import { Composer } from '../components/workspace/Composer';
import { WorkspaceHeader } from '../components/workspace/WorkspaceHeader';
import { WorkspaceSidebar } from '../components/workspace/WorkspaceSidebar';
import { ExecutionTimeline } from '../components/workspace/ExecutionTimeline';
import { DataModulePage } from '../components/workspace/DataModulePage';
import { ObservedModulePage } from '../components/workspace/ObservedModulePage';
import { CheckpointPage } from '../components/workspace/CheckpointPage';
import { TaskDetailPage } from '../components/workspace/TaskDetailPage';
import { ConfirmDialog } from '../components/workspace/ConfirmDialog';
import { CommandPalette } from '../components/workspace/CommandPalette';
import { useChatSession } from '../hooks/useChatSession';
import { useRunEvents } from '../hooks/useRunEvents';
import { useChatEvents } from '../hooks/useChatEvents';
import { api } from '../services/api';
import type { ChatMessage, ChatSession } from '../types/api';

function displayMessages(messages: ChatMessage[] = []): ChatMessage[] {
  return messages.flatMap((message) => {
    if (!message.response || message.role !== 'user') return [message];
    return [
      { ...message, response: undefined },
      {
        role: 'assistant',
        project_id: message.project_id,
        summary: message.response.summary || 'Resposta recebida.',
        response: message.response,
      },
    ];
  });
}

export function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [message, setMessage] = useState('');
  const [streaming, setStreaming] = useState(false);
  const streamAbort = useRef<AbortController>();
  const [sessionId, setSessionId] = useState<string>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeProjectId, setActiveProjectId] = useState('');
  const [runId, setRunId] = useState<string>();
  const [pendingAction, setPendingAction] = useState<import('../types/api').WorkspaceAction>();
  const [taskProposal, setTaskProposal] = useState(false);
  const [taskPending, setTaskPending] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string>();
  const [commandsOpen, setCommandsOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects });
  const active = projects.data?.projects.find((project) => project.project_id === activeProjectId);
  const summary = useQuery({ queryKey: ['dashboard', activeProjectId], queryFn: () => api.dashboard(activeProjectId), enabled: Boolean(activeProjectId) });
  const chat = useChatSession(activeProjectId);
  const select = useMutation({ mutationFn: api.selectProject, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }) });

  useEffect(() => { if (!activeProjectId && projects.data?.active_project_id) setActiveProjectId(projects.data.active_project_id); }, [activeProjectId, projects.data?.active_project_id]);
  useEffect(() => { setSessionId(undefined); setMessages([]); setMessage(''); setRunId(undefined); }, [activeProjectId]);
  useEffect(() => { const latest = chat.sessions.data?.sessions?.[0]; if (!sessionId && latest) { setSessionId(latest.session_id); setMessages(displayMessages(latest.messages)); setRunId(latest.run_id || latest.messages?.find((item) => item.response?.run_id)?.response?.run_id); } }, [chat.sessions.data, sessionId]);
  useEffect(() => { const listener = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setCommandsOpen(true); } }; window.addEventListener('keydown', listener); return () => window.removeEventListener('keydown', listener); }, []);

  const selectProject = (projectId: string) => { streamAbort.current?.abort(); setStreaming(false); setActiveProjectId(projectId); setSessionId(undefined); setMessages([]); setMessage(''); select.mutate(projectId); navigate('/workspace'); };
  const newSession = () => { streamAbort.current?.abort(); setStreaming(false); setSessionId(undefined); setMessages([]); setMessage(''); setRunId(undefined); setWorkspaceError(undefined); };
  const selectSession = (session: ChatSession) => { setSessionId(session.session_id); setMessages(displayMessages(session.messages)); setMessage(''); setRunId(session.messages?.find((item) => item.response?.run_id)?.response?.run_id); };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const text = message.trim();
    if (!text || !activeProjectId || chat.send.isPending || streaming) return;
    const projectIdAtStart = activeProjectId;
    setWorkspaceError(undefined);
    try {
      let currentSession = sessionId;
      if (!currentSession) { const created = await chat.create.mutateAsync(); currentSession = created.session_id; setSessionId(currentSession); }
      setMessages((current) => [...current, { role: 'user', project_id: activeProjectId, summary: text }, { role: 'assistant', project_id: activeProjectId, summary: 'Gerando resposta…' }]);
      setMessage('');
      setStreaming(true); const controller = new AbortController(); streamAbort.current = controller; let streamError: string | undefined;
      await api.streamMessage(currentSession, projectIdAtStart, text, controller.signal, (event) => {
        if (activeProjectId !== projectIdAtStart || (sessionId && sessionId !== currentSession)) { controller.abort(); return; }
        if (event.event === 'message.delta') setMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, summary: `${item.summary === 'Gerando resposta…' ? '' : item.summary || ''}${event.delta || ''}` } : item));
        if (event.event === 'message.completed') setMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, summary: event.summary || item.summary, response: { status: 'READY', project_id: projectIdAtStart, summary: event.summary, rag: event.rag, metrics: event.metrics, provider: event.provider, model_requested: event.model_requested, model_effective: event.model_effective, registry_version: event.registry_version } } : item));
        if (event.event === 'message.error') { streamError = event.message || 'Não foi possível gerar a resposta.'; setMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, summary: streamError } : item)); }
      });
      if (streamError) setWorkspaceError(streamError);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      setWorkspaceError(error instanceof Error ? error.message : 'Não foi possível concluir a mensagem.');
      setMessages((current) => [...current, { role: 'assistant', project_id: activeProjectId, summary: 'Não foi possível concluir a mensagem. Tente novamente.' }]);
    } finally { setStreaming(false); streamAbort.current = undefined; }
  };

  const sessions = chat.sessions.data?.sessions || [];
  const module = ({
    '/tasks': ['Tarefas', 'Consulte e filtre as execuções do projeto ativo.'],
    '/agents': ['Agents', 'Acompanhe agents, saúde, histórico e consumo.'],
    '/checkpoints': ['Checkpoints', 'Retome estados consistentes de tarefas interrompidas.'],
    '/rag': ['RAG', 'Consulte fontes, ranking, feedback e versões do contexto.'],
    '/logs': ['Logs', 'Acompanhe eventos correlacionados da execução.'],
    '/evidence': ['Evidências', 'Explore provenance, findings e referências seguras.'],
    '/models': ['Modelos e custos', 'Visualize métricas observadas, tokens e budgets.'],
    '/integrations': ['Integrações', 'Verifique capabilities, saúde e auditoria de MCPs.'],
    '/settings': ['Configurações', 'Gerencie drafts revisionados, aprovação e rollback.'],
  } as Record<string, [string, string]>)[location.pathname];
  const section = module?.[0] || 'Workspace';
  const events = useRunEvents(activeProjectId, runId);
  const chatEvents = useChatEvents(activeProjectId, sessionId);
  if (location.pathname === '/') return <Navigate to="/workspace" replace />;
  const runAction = (action: import('../types/api').WorkspaceAction) => { setPendingAction(action); };
  const confirmRunAction = async () => { if (runId && pendingAction) { try { await api.runAction(activeProjectId, runId, pendingAction, `Ação solicitada no Workspace: ${pendingAction}`); setPendingAction(undefined); setWorkspaceError(undefined); } catch (error) { setWorkspaceError(error instanceof Error ? error.message : 'Não foi possível executar a ação.'); } } };
  const requestTask = () => { if (message.trim()) setTaskProposal(true); };
  const confirmTask = async () => { if (!activeProjectId || !message.trim()) return; setTaskPending(true); setWorkspaceError(undefined); try { const query = message.trim(); let currentSession = sessionId; if (!currentSession) { const createdSession = await chat.create.mutateAsync(); currentSession = createdSession.session_id; setSessionId(currentSession); } const created = await api.createTask(activeProjectId, `workspace-${Date.now()}`, query, currentSession); const createdRunId = created.state?.run_id; if (createdRunId) setRunId(createdRunId); setMessages((current) => [...current, { role: 'user', project_id: activeProjectId, summary: query }, { role: 'assistant', project_id: activeProjectId, summary: 'Tarefa criada e associada à conversa. O Runtime V3 está pronto para executar o plano.', response: { status: String(created.state?.current_state || 'CREATED'), project_id: activeProjectId, task_id: created.state?.task_id, run_id: createdRunId, plan: (created.state?.execution_plan as { [key: string]: unknown } | undefined) } }]); setMessage(''); setTaskProposal(false); } catch (error) { setWorkspaceError(error instanceof Error ? error.message : 'Não foi possível iniciar a tarefa.'); } finally { setTaskPending(false); } };
  const latestChatEvent = chatEvents.length ? chatEvents[chatEvents.length - 1] : undefined;
  const activeSession = sessions.find((session) => session.session_id === sessionId);
  const activeTaskId = [...messages].reverse().find((item) => item.response?.task_id)?.response?.task_id || activeSession?.task_id;
  return <div className="flex min-h-screen bg-[radial-gradient(circle_at_50%_-20%,#e8efff,transparent_42%),#f5f7fb] font-sans antialiased text-slate-900">{workspaceError && <div role="alert" className="fixed right-4 top-4 z-50 max-w-sm rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 shadow-lg">{workspaceError}<button className="ml-3 font-bold" onClick={() => setWorkspaceError(undefined)} aria-label="Fechar aviso">×</button></div>}<WorkspaceSidebar projects={projects.data?.projects || []} projectId={activeProjectId} collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} onProjectChange={selectProject} /><main className="min-w-0 flex-1"><WorkspaceHeader projectName={active?.name} section={section} onOpenCommands={() => setCommandsOpen(true)} /><Routes><Route path="/workspace" element={<section className="grid min-w-0 grid-cols-1 gap-5 px-4 pb-8 sm:px-6 lg:grid-cols-[minmax(0,1fr)_310px] lg:px-12"><div className="min-w-0"><div className="flex gap-4 rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 to-white p-5 shadow-panel"><span className="text-3xl text-violet-500">✦</span><div><h2 className="m-0 text-base font-bold tracking-tight text-slate-900">Workspace de operações</h2><p className="mt-1.5 text-sm leading-6 text-slate-500">Escolha Analisar, Planejar, Implementar ou Validar para iniciar um fluxo controlado.</p></div></div><div className="px-2 py-6"><Composer /><ExecutionTimeline events={events} pending={Boolean(runId)} onAction={runId ? runAction : undefined} /></div></div><ContextPanel project={active} summary={summary.data} loading={summary.isLoading} runId={runId} taskId={activeTaskId} events={events} /></section>} /><Route path="/tasks" element={<DataModulePage kind="tasks" project={active} projectId={activeProjectId} />} /><Route path="/tasks/:runId" element={<TaskDetailPage project={active} projectId={activeProjectId} runId={decodeURIComponent(location.pathname.split('/').pop() || '')} />} /><Route path="/rag" element={<DataModulePage kind="rag" project={active} projectId={activeProjectId} />} /><Route path="/agents" element={<ObservedModulePage kind="agents" title="Agents" description="Acompanhe agents, saúde, histórico e consumo." project={active} projectId={activeProjectId} />} /><Route path="/logs" element={<ObservedModulePage kind="logs" title="Logs" description="Acompanhe eventos correlacionados da execução." project={active} projectId={activeProjectId} />} /><Route path="/evidence" element={<ObservedModulePage kind="evidence" title="Evidências" description="Explore provenance, findings e referências seguras." project={active} projectId={activeProjectId} />} /><Route path="/models" element={<ObservedModulePage kind="models" title="Modelos e custos" description="Visualize métricas observadas, tokens e budgets." project={active} projectId={activeProjectId} />} /><Route path="/integrations" element={<ObservedModulePage kind="integrations" title="Integrações" description="Verifique capabilities, saúde e auditoria de MCPs." project={active} projectId={activeProjectId} />} /><Route path="/settings" element={<ObservedModulePage kind="settings" title="Configurações" description="Gerencie drafts revisionados, aprovação e rollback." project={active} projectId={activeProjectId} />} /><Route path="/checkpoints" element={<CheckpointPage project={active} projectId={activeProjectId} />} /></Routes></main>{pendingAction && <ConfirmDialog action={pendingAction} onCancel={() => setPendingAction(undefined)} onConfirm={confirmRunAction} />}<CommandPalette open={commandsOpen} onClose={() => setCommandsOpen(false)} onNewSession={newSession} /></div>;
}
