import type { ChatMessage, ChatSession } from './api';

export type WorkspaceStatus = 'EMPTY' | 'READY' | 'SENDING' | 'ERROR';
export type ChatSessionSummary = Pick<ChatSession, 'session_id' | 'project_id' | 'task_id' | 'messages'>;
export type WorkspaceMessage = ChatMessage & { id: string; createdAt: string };
