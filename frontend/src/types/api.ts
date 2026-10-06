export type Project = { project_id: string; name: string; repository_root: string; default_branch: string; rag_scope: string[]; allowed_agents: string[]; allowed_integrations: string[]; policy_ref: string };
export type ProjectsResponse = { projects: Project[]; active_project_id: string | null };
export type ChatResponse = { status: string; summary?: string; project_id: string; rag?: { retrieved: boolean; query_id?: string }; metrics?: Record<string, unknown> };
export type ChatMessage = { role: string; project_id: string; summary?: string; response?: ChatResponse };
export type ChatSession = { session_id: string; project_id: string; task_id?: string; messages?: ChatMessage[] };
export type ProjectContext = { project_id: string; name: string; default_branch: string };
export type DashboardSummary = { total_runs: number; successful_runs: number; failed_runs: number; average_duration_ms: number; average_agent_invocations: number };
