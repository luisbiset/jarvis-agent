import { describe, expect, it, vi } from 'vitest';
import { api } from './api';

describe('project-scoped API', () => {
  it('adds project_id to dashboard requests', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ project_id: 'jarvis' }), { status: 200 }));
    await api.dashboard('jarvis');
    expect(fetchMock.mock.calls[0][0]).toBe('/api/dashboard?project_id=jarvis');
    fetchMock.mockRestore();
  });

  it('sends project_id when creating a chat session', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ session_id: 'chat-1', project_id: 'aghuse' }), { status: 201 }));
    await api.createSession('aghuse');
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ project_id: 'aghuse' });
    fetchMock.mockRestore();
  });
});
