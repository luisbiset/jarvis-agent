import type { ChatEvent, ChatMessage, ChatSession, ChatStreamEvent, DashboardSummary, Operation, OperationProposal, Project, ProjectsResponse, RagControl, RunDetail, RunDiff, RunSummary, TaskCreation, WorkspaceAction } from '../types/api';

export class ApiError extends Error { constructor(public readonly status: number, public readonly code: string | undefined, message: string) { super(message); this.name = 'ApiError'; } }
async function request<T>(path: string, init?: RequestInit): Promise<T> { const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init }); if (!response.ok) { const body = await response.json().catch(() => ({})); throw new ApiError(response.status, body.code, body.error || `HTTP ${response.status}`); } return response.json(); }
export const api = {
  projects: () => request<ProjectsResponse>('/api/projects'),
  selectProject: (id: string) => request<{ project: Project; active_project_id: string }>(`/api/projects/${encodeURIComponent(id)}/select`, { method: 'POST', body: '{}' }),
  dashboard: (projectId: string) => request<DashboardSummary>(`/api/dashboard?project_id=${encodeURIComponent(projectId)}`),
  runs: (projectId: string) => request<{ runs: RunSummary[] }>(`/api/runs?project_id=${encodeURIComponent(projectId)}`),
  createTask: (projectId: string, taskId: string, query: string, sessionId?: string) => request<TaskCreation>('/api/tasks', { method: 'POST', body: JSON.stringify({ project_id: projectId, task_id: taskId, query, ...(sessionId ? { session_id: sessionId } : {}) }) }),
  ragControl: (projectId: string) => request<RagControl>(`/api/control?project_id=${encodeURIComponent(projectId)}`),
  agents: (projectId: string) => request<Record<string, unknown>>(`/api/agents?project_id=${encodeURIComponent(projectId)}`),
  evidence: (projectId: string) => request<Record<string, unknown>>(`/api/evidence?project_id=${encodeURIComponent(projectId)}`),
  models: (projectId: string) => request<Record<string, unknown>>(`/api/models/usage?project_id=${encodeURIComponent(projectId)}`),
  integrations: (projectId: string) => request<Record<string, unknown>>(`/api/integrations?project_id=${encodeURIComponent(projectId)}`),
  settings: (projectId: string) => request<Record<string, unknown>>(`/api/settings?project_id=${encodeURIComponent(projectId)}`),
  logs: (projectId: string) => request<Record<string, unknown>>(`/api/metrics/series?project_id=${encodeURIComponent(projectId)}`),
  ragFeedback: (id: string, action: 'approve' | 'reject') => request<Record<string, unknown>>('/api/feedback', { method: 'POST', body: JSON.stringify({ id, action }) }),
  ragTraining: () => request<Record<string, unknown>>('/api/training', { method: 'POST', body: '{}' }),
  sessions: (projectId: string) => request<{ sessions: ChatSession[]; project_id: string }>(`/api/chat/sessions?project_id=${encodeURIComponent(projectId)}`),
  createSession: (projectId: string) => request<ChatSession>('/api/chat/sessions', { method: 'POST', body: JSON.stringify({ project_id: projectId }) }),
  sendMessage: (id: string, projectId: string, message: string) => request<{ session_id: string; message: ChatMessage }>(`/api/chat/sessions/${encodeURIComponent(id)}/messages`, { method: 'POST', body: JSON.stringify({ project_id: projectId, message }) }),
  streamMessage: async (id: string, projectId: string, message: string, signal: AbortSignal | undefined, onEvent: (event: ChatStreamEvent) => void) => {
    const response = await fetch(`/api/chat/sessions/${encodeURIComponent(id)}/messages/stream`, { method: 'POST', signal, headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' }, body: JSON.stringify({ project_id: projectId, message }) });
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw new ApiError(response.status, body.code, body.error || `HTTP ${response.status}`); }
    if (!response.body) throw new ApiError(502, 'STREAM_UNAVAILABLE', 'Streaming indisponível.');
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
    for (;;) { const chunk = await reader.read(); if (chunk.done) break; buffer += decoder.decode(chunk.value, { stream: true }); const frames = buffer.split('\n\n'); buffer = frames.pop() || ''; for (const frame of frames) { const data = frame.split('\n').find((line) => line.startsWith('data:')); if (data) onEvent(JSON.parse(data.slice(5).trim()) as ChatStreamEvent); } }
  },
  chatEvents: (id: string, projectId: string) => request<{ events: ChatEvent[] }>(`/api/chat/sessions/${encodeURIComponent(id)}/events?project_id=${encodeURIComponent(projectId)}&poll=1`),
  run: (projectId: string, runId: string) => request<RunDetail>(`/api/runs/${encodeURIComponent(runId)}?project_id=${encodeURIComponent(projectId)}`),
  diff: (projectId: string, runId: string) => request<RunDiff>(`/api/runs/${encodeURIComponent(runId)}/diff?project_id=${encodeURIComponent(projectId)}`),
  runAction: (projectId: string, runId: string, action: WorkspaceAction, reason: string) => request<Record<string, unknown>>(`/api/runs/${encodeURIComponent(runId)}/actions`, { method: 'POST', body: JSON.stringify({ project_id: projectId, action, reason, confirm: true, idempotency_key: `${projectId}:${runId}:${action}:${reason}` }) }),
  operations: () => request<{ operations: Operation[] }>('/api/operations'),
  previewOperation: (operationId: string, projectId: string, parameters: Record<string, string>) => request<OperationProposal>(`/api/operations/${encodeURIComponent(operationId)}/preview`, { method: 'POST', body: JSON.stringify({ project_id: projectId, parameters }) }),
  executeOperation: (proposal: OperationProposal, actor = 'dashboard-local') => request<OperationProposal & { state?: Record<string, unknown> }>(`/api/operations/${encodeURIComponent(proposal.operation_id)}/execute`, { method: 'POST', body: JSON.stringify({ project_id: proposal.project_id, proposal_id: proposal.proposal_id, confirm: true, actor, idempotency_key: `${proposal.project_id}:${proposal.proposal_id}` }) }),
  approveOperation: (projectId: string, runId: string, reason: string) => request<OperationProposal>(`/api/operations/runs/${encodeURIComponent(runId)}/approve`, { method: 'POST', body: JSON.stringify({ project_id: projectId, confirm: true, reason, actor: 'dashboard-local' }) }),
  rejectOperation: (projectId: string, runId: string, reason: string) => request<OperationProposal>(`/api/operations/runs/${encodeURIComponent(runId)}/reject`, { method: 'POST', body: JSON.stringify({ project_id: projectId, confirm: true, reason, actor: 'dashboard-local' }) }),
};
