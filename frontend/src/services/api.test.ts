import { describe, expect, it, vi } from 'vitest';
import { api } from './api';

describe('project-scoped API', () => {
  it('adds project_id to dashboard requests', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ project_id: 'aghuse' }), { status: 200 }));
    await api.dashboard('aghuse');
    expect(fetchMock.mock.calls[0][0]).toBe('/api/dashboard?project_id=aghuse');
    fetchMock.mockRestore();
  });

  it('sends project_id when creating a chat session', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ session_id: 'chat-1', project_id: 'aghuse' }), { status: 201 }));
    await api.createSession('aghuse');
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ project_id: 'aghuse' });
    fetchMock.mockRestore();
  });

  it('scopes session listing and messages to the project', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => new Response(String(input).includes('/messages') ? JSON.stringify({ session_id: 'chat-1', message: { role: 'assistant', project_id: 'aghuse' } }) : JSON.stringify({ sessions: [], project_id: 'aghuse' }), { status: 200 }));
    await api.sessions('aghuse');
    await api.sendMessage('chat-1', 'aghuse', 'Analise o contexto');
    expect(fetchMock.mock.calls[0][0]).toBe('/api/chat/sessions?project_id=aghuse');
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({ project_id: 'aghuse', message: 'Analise o contexto' });
    fetchMock.mockRestore();
  });

  it('preserves HTTP status and sanitized backend code', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ code: 'PROJECT_NOT_FOUND', error: 'Projeto não encontrado' }), { status: 404 }));
    await expect(api.dashboard('missing')).rejects.toMatchObject({ status: 404, code: 'PROJECT_NOT_FOUND', message: 'Projeto não encontrado' });
    expect(fetchMock).toHaveBeenCalledOnce();
    fetchMock.mockRestore();
  });

  it('sends RAG feedback and training requests', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response('{}', { status: 200 }));
    await api.ragFeedback('feedback-1', 'approve');
    await api.ragTraining();
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ id: 'feedback-1', action: 'approve' });
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({});
    expect(fetchMock.mock.calls[0][0]).toBe('/api/feedback');
    expect(fetchMock.mock.calls[1][0]).toBe('/api/training');
    fetchMock.mockRestore();
  });

  it('sends an idempotent project-scoped run action', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 200 }));
    await api.runAction('aghuse', 'run-1', 'PAUSE', 'pause requested');
    const payload = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(payload).toMatchObject({ project_id: 'aghuse', action: 'PAUSE', confirm: true, reason: 'pause requested' });
    expect(payload.idempotency_key).toContain('aghuse:run-1:PAUSE:pause requested');
    fetchMock.mockRestore();
  });

  it('creates a task with project context and safe query payload', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 201 }));
    await api.createTask('aghuse', 'workspace-1', 'Analise o fluxo de autenticação');
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ project_id: 'aghuse', task_id: 'workspace-1', query: 'Analise o fluxo de autenticação' });
    fetchMock.mockRestore();
  });

  it('associates task creation with the active chat session', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ok: true, session_id: 'chat-1' }), { status: 201 }));
    await api.createTask('aghuse', 'workspace-2', 'Iniciar análise', 'chat-1');
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ project_id: 'aghuse', task_id: 'workspace-2', query: 'Iniciar análise', session_id: 'chat-1' });
    fetchMock.mockRestore();
  });

  it('polls chat events with the project and session context', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ events: [], project_id: 'aghuse', session_id: 'chat-1' }), { status: 200 }));
    await api.chatEvents('chat-1', 'aghuse');
    expect(fetchMock.mock.calls[0][0]).toBe('/api/chat/sessions/chat-1/events?project_id=aghuse&poll=1');
    fetchMock.mockRestore();
  });

  it('streams chat deltas with the project context', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('data: {"event":"message.delta","delta":"Olá"}\n\ndata: {"event":"message.completed","summary":"Olá"}\n\n', { status: 200, headers: { 'Content-Type': 'text/event-stream' } }));
    const events: string[] = [];
    await api.streamMessage('chat-1', 'aghuse', 'oi', undefined, (event) => events.push(event.event));
    expect(events).toEqual(['message.delta', 'message.completed']);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/chat/sessions/chat-1/messages/stream');
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ project_id: 'aghuse', message: 'oi' });
    fetchMock.mockRestore();
  });
});
