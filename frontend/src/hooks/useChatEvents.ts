import { useEffect, useState } from 'react';
import type { ChatEvent } from '../types/api';
import { api } from '../services/api';

export function useChatEvents(projectId: string, sessionId?: string) {
  const [events, setEvents] = useState<ChatEvent[]>([]);
  useEffect(() => {
    if (!projectId || !sessionId) { setEvents([]); return; }
    let active = true;
    let source: EventSource | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = () => api.chatEvents(sessionId, projectId).then((result) => { if (active) setEvents(result.events || []); }).catch(() => undefined).finally(() => { if (active && !source) timer = setTimeout(load, 2500); });
    load();
    if (typeof EventSource !== 'undefined') {
      source = new EventSource(`/api/chat/sessions/${encodeURIComponent(sessionId)}/events?project_id=${encodeURIComponent(projectId)}`);
      source.onmessage = (message) => { try { const event = JSON.parse(message.data) as ChatEvent; if (active) setEvents((current) => current.some((item) => item.event_id === event.event_id) ? current : [...current, event]); } catch { /* evento inválido é ignorado */ } };
      source.onerror = () => { source?.close(); source = undefined; load(); };
    }
    return () => { active = false; source?.close(); if (timer) clearTimeout(timer); };
  }, [projectId, sessionId]);
  return events;
}
