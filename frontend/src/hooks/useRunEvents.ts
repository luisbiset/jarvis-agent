import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { RunEvent } from '../types/api';

export function useRunEvents(projectId?: string, runId?: string) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  useEffect(() => {
    if (!projectId || !runId) { setEvents([]); return; }
    let cancelled = false;
    let source: EventSource | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const merge = (incoming: RunEvent[]) => setEvents((current) => {
      const all = [...current, ...incoming];
      return all.filter((event, index) => all.findIndex((item) => `${item.at}:${item.event}:${item.reason}` === `${event.at}:${event.event}:${event.reason}`) === index);
    });
    const poll = async () => {
      try { const result = await api.run(projectId, runId); if (!cancelled) merge(result.timeline || []); }
      finally { if (!cancelled) timer = setTimeout(poll, 3000); }
    };
    try {
      source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events?project_id=${encodeURIComponent(projectId)}`);
      source.onmessage = (event) => { try { merge([JSON.parse(event.data) as RunEvent]); } catch { /* evento inválido é ignorado */ } };
      source.onerror = () => { source?.close(); source = undefined; poll(); };
    } catch { poll(); }
    return () => { cancelled = true; source?.close(); if (timer) clearTimeout(timer); };
  }, [projectId, runId]);
  return events;
}
