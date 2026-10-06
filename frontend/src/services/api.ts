import type { ChatMessage, ChatSession, DashboardSummary, Project, ProjectsResponse } from '../types/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> { const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init }); if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || `HTTP ${response.status}`); return response.json(); }
export const api = {
  projects: () => request<ProjectsResponse>('/api/projects'),
  selectProject: (id: string) => request<{ project: Project; active_project_id: string }>(`/api/projects/${encodeURIComponent(id)}/select`, { method: 'POST', body: '{}' }),
  dashboard: (projectId: string) => request<DashboardSummary>(`/api/dashboard?project_id=${encodeURIComponent(projectId)}`),
  sessions: (projectId: string) => request<{ sessions: ChatSession[]; project_id: string }>(`/api/chat/sessions?project_id=${encodeURIComponent(projectId)}`),
  createSession: (projectId: string) => request<ChatSession>('/api/chat/sessions', { method: 'POST', body: JSON.stringify({ project_id: projectId }) }),
  sendMessage: (id: string, projectId: string, message: string) => request<{ session_id: string; message: ChatMessage }>(`/api/chat/sessions/${encodeURIComponent(id)}/messages`, { method: 'POST', body: JSON.stringify({ project_id: projectId, message }) }),
};
