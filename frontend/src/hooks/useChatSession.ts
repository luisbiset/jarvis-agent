import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';

export function useChatSession(projectId: string) {
  const queryClient = useQueryClient();
  const sessions = useQuery({ queryKey: ['chat-sessions', projectId], queryFn: () => api.sessions(projectId), enabled: Boolean(projectId) });
  const create = useMutation({ mutationFn: () => api.createSession(projectId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat-sessions', projectId] }) });
  const send = useMutation({ mutationFn: ({ sessionId, message }: { sessionId: string; message: string }) => api.sendMessage(sessionId, projectId, message) });
  return { sessions, create, send };
}
