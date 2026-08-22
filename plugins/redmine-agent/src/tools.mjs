import {
  DEFAULT_URL,
  MAX_PAGE_SIZE,
  RedmineClient,
  RedmineError,
  boundedLimit,
  boundedOffset,
  compactCurrentUser,
  compactIssue,
  positiveInteger,
  requiredText,
} from "./client.mjs";

const readAnnotations = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: true,
};

const writeAnnotations = {
  readOnlyHint: false,
  destructiveHint: false,
  idempotentHint: false,
  openWorldHint: true,
};

export const tools = [
  {
    name: "get_current_user",
    title: "Obter usuário atual do Redmine",
    description: "Obtém a identidade associada à chave de API. Use antes de consultar 'meus chamados'.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: readAnnotations,
  },
  {
    name: "list_projects",
    title: "Listar projetos do Redmine",
    description: "Lista projetos visíveis para localizar o ID ou identificador correto.",
    inputSchema: {
      type: "object",
      properties: {
        limit: { type: "integer", minimum: 1, maximum: MAX_PAGE_SIZE, default: 25 },
        offset: { type: "integer", minimum: 0, default: 0 },
      },
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "list_project_memberships",
    title: "Listar membros de um projeto",
    description: "Lista membros e papéis para resolver responsáveis sem adivinhar IDs.",
    inputSchema: {
      type: "object",
      required: ["project_id"],
      properties: {
        project_id: { oneOf: [{ type: "integer", minimum: 1 }, { type: "string", minLength: 1 }] },
        limit: { type: "integer", minimum: 1, maximum: MAX_PAGE_SIZE, default: 100 },
        offset: { type: "integer", minimum: 0, default: 0 },
      },
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "list_issues",
    title: "Listar chamados do Redmine",
    description: "Pesquisa chamados por projeto, responsável, status, tracker, prioridade ou consulta salva.",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { oneOf: [{ type: "integer", minimum: 1 }, { type: "string", minLength: 1 }] },
        assigned_to_id: { oneOf: [{ type: "integer", minimum: 1 }, { type: "string", enum: ["me"] }] },
        status_id: { oneOf: [{ type: "integer", minimum: 1 }, { type: "string", enum: ["open", "closed", "*"] }] },
        tracker_id: { type: "integer", minimum: 1 },
        priority_id: { type: "integer", minimum: 1 },
        query_id: { type: "integer", minimum: 1 },
        sort: { type: "string", maxLength: 100, default: "updated_on:desc" },
        limit: { type: "integer", minimum: 1, maximum: MAX_PAGE_SIZE, default: 25 },
        offset: { type: "integer", minimum: 0, default: 0 },
      },
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "get_issue",
    title: "Obter detalhes de um chamado",
    description: "Obtém descrição, campos e histórico de um chamado pelo ID.",
    inputSchema: {
      type: "object",
      required: ["issue_id"],
      properties: { issue_id: { type: "integer", minimum: 1 } },
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "list_metadata",
    title: "Listar metadados do Redmine",
    description: "Lista status, trackers, prioridades e atividades de horas para resolver IDs antes de escrever.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: readAnnotations,
  },
  {
    name: "list_time_entries",
    title: "Listar horas registradas",
    description: "Lista registros de horas por chamado, projeto, usuário ou intervalo de datas.",
    inputSchema: {
      type: "object",
      properties: {
        issue_id: { type: "integer", minimum: 1 },
        project_id: { oneOf: [{ type: "integer", minimum: 1 }, { type: "string", minLength: 1 }] },
        user_id: { oneOf: [{ type: "integer", minimum: 1 }, { type: "string", enum: ["me"] }] },
        from: { type: "string", format: "date" },
        to: { type: "string", format: "date" },
        limit: { type: "integer", minimum: 1, maximum: MAX_PAGE_SIZE, default: 25 },
        offset: { type: "integer", minimum: 0, default: 0 },
      },
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "create_issue",
    title: "Criar chamado no Redmine",
    description: "Cria um chamado depois de o usuário confirmar projeto, tracker, assunto e conteúdo.",
    inputSchema: {
      type: "object",
      required: ["project_id", "subject", "description"],
      properties: {
        project_id: { oneOf: [{ type: "integer", minimum: 1 }, { type: "string", minLength: 1 }] },
        subject: { type: "string", minLength: 1, maxLength: 255 },
        description: { type: "string", minLength: 1 },
        tracker_id: { type: "integer", minimum: 1 },
        priority_id: { type: "integer", minimum: 1 },
        assigned_to_id: { type: "integer", minimum: 1 },
        parent_issue_id: { type: "integer", minimum: 1 },
        estimated_hours: { type: "number", minimum: 0 },
        due_date: { type: "string", format: "date" },
        custom_fields: {
          type: "array",
          items: {
            type: "object",
            required: ["id", "value"],
            properties: { id: { type: "integer", minimum: 1 }, value: {} },
            additionalProperties: false,
          },
        },
      },
      additionalProperties: false,
    },
    annotations: writeAnnotations,
  },
  {
    name: "add_issue_note",
    title: "Comentar em chamado",
    description: "Adiciona uma nota a um chamado depois de o usuário confirmar o texto final.",
    inputSchema: {
      type: "object",
      required: ["issue_id", "notes"],
      properties: {
        issue_id: { type: "integer", minimum: 1 },
        notes: { type: "string", minLength: 1 },
        private_notes: { type: "boolean", default: false },
      },
      additionalProperties: false,
    },
    annotations: writeAnnotations,
  },
  {
    name: "update_issue",
    title: "Atualizar chamado no Redmine",
    description: "Atualiza campos de um chamado depois de mostrar e confirmar todas as mudanças.",
    inputSchema: {
      type: "object",
      required: ["issue_id"],
      properties: {
        issue_id: { type: "integer", minimum: 1 },
        subject: { type: "string", minLength: 1, maxLength: 255 },
        description: { type: "string" },
        status_id: { type: "integer", minimum: 1 },
        tracker_id: { type: "integer", minimum: 1 },
        priority_id: { type: "integer", minimum: 1 },
        assigned_to_id: { type: "integer", minimum: 1 },
        done_ratio: { type: "integer", minimum: 0, maximum: 100 },
        estimated_hours: { type: "number", minimum: 0 },
        due_date: { type: ["string", "null"], format: "date" },
        notes: { type: "string" },
        private_notes: { type: "boolean" },
        custom_fields: {
          type: "array",
          items: {
            type: "object",
            required: ["id", "value"],
            properties: { id: { type: "integer", minimum: 1 }, value: {} },
            additionalProperties: false,
          },
        },
      },
      additionalProperties: false,
    },
    annotations: writeAnnotations,
  },
  {
    name: "log_time",
    title: "Registrar horas no Redmine",
    description: "Registra horas no chamado ou projeto depois de confirmar data, quantidade, atividade e comentário.",
    inputSchema: {
      type: "object",
      required: ["hours", "activity_id", "comments"],
      properties: {
        issue_id: { type: "integer", minimum: 1 },
        project_id: { oneOf: [{ type: "integer", minimum: 1 }, { type: "string", minLength: 1 }] },
        spent_on: { type: "string", format: "date" },
        hours: { type: "number", exclusiveMinimum: 0 },
        activity_id: { type: "integer", minimum: 1 },
        comments: { type: "string", minLength: 1, maxLength: 255 },
      },
      oneOf: [{ required: ["issue_id"] }, { required: ["project_id"] }],
      additionalProperties: false,
    },
    annotations: writeAnnotations,
  },
];

export function getClient() {
  return new RedmineClient({
    baseUrl: process.env.REDMINE_URL || DEFAULT_URL,
    apiKey: process.env.REDMINE_API_KEY,
  });
}

function projectIdentifier(value) {
  if (typeof value === "number") return String(positiveInteger(value, "project_id"));
  return requiredText(value, "project_id");
}

export async function callTool(name, args = {}, client = getClient()) {
  switch (name) {
    case "get_current_user": {
      const result = await client.request("GET", "users/current.json");
      return { user: compactCurrentUser(result.user || {}) };
    }
    case "list_projects":
      return await client.request("GET", "projects.json", {
        query: { limit: boundedLimit(args.limit), offset: boundedOffset(args.offset) },
      });
    case "list_project_memberships": {
      const project = encodeURIComponent(projectIdentifier(args.project_id));
      return await client.request("GET", `projects/${project}/memberships.json`, {
        query: { limit: boundedLimit(args.limit ?? 100), offset: boundedOffset(args.offset) },
      });
    }
    case "list_issues": {
      const result = await client.request("GET", "issues.json", {
        query: {
          project_id: args.project_id,
          assigned_to_id: args.assigned_to_id,
          status_id: args.status_id ?? "open",
          tracker_id: args.tracker_id,
          priority_id: args.priority_id,
          query_id: args.query_id,
          sort: args.sort || "updated_on:desc",
          limit: boundedLimit(args.limit),
          offset: boundedOffset(args.offset),
        },
      });
      return { ...result, issues: (result.issues || []).map(compactIssue) };
    }
    case "get_issue": {
      const issueId = positiveInteger(args.issue_id, "issue_id");
      return await client.request("GET", `issues/${issueId}.json`, {
        query: { include: "journals,relations,attachments" },
      });
    }
    case "list_metadata": {
      const [statuses, trackers, priorities, activities] = await Promise.all([
        client.request("GET", "issue_statuses.json"),
        client.request("GET", "trackers.json"),
        client.request("GET", "enumerations/issue_priorities.json"),
        client.request("GET", "enumerations/time_entry_activities.json"),
      ]);
      return { ...statuses, ...trackers, ...priorities, ...activities };
    }
    case "list_time_entries":
      return await client.request("GET", "time_entries.json", {
        query: {
          issue_id: args.issue_id,
          project_id: args.project_id,
          user_id: args.user_id,
          from: args.from,
          to: args.to,
          limit: boundedLimit(args.limit),
          offset: boundedOffset(args.offset),
        },
      });
    case "create_issue": {
      requiredText(args.subject, "subject");
      requiredText(args.description, "description");
      projectIdentifier(args.project_id);
      const issue = Object.fromEntries(Object.entries(args).filter(([, value]) => value !== undefined));
      return await client.request("POST", "issues.json", { body: { issue } });
    }
    case "add_issue_note": {
      const issueId = positiveInteger(args.issue_id, "issue_id");
      const notes = requiredText(args.notes, "notes");
      await client.request("PUT", `issues/${issueId}.json`, {
        body: { issue: { notes, private_notes: Boolean(args.private_notes) } },
      });
      return { ok: true, issue_id: issueId };
    }
    case "update_issue": {
      const issueId = positiveInteger(args.issue_id, "issue_id");
      const { issue_id: ignored, ...fields } = args;
      const issue = Object.fromEntries(Object.entries(fields).filter(([, value]) => value !== undefined));
      if (Object.keys(issue).length === 0) throw new RedmineError("Informe ao menos um campo para atualizar.");
      await client.request("PUT", `issues/${issueId}.json`, { body: { issue } });
      return { ok: true, issue_id: issueId, updated_fields: Object.keys(issue) };
    }
    case "log_time": {
      if (args.issue_id === undefined && args.project_id === undefined) {
        throw new RedmineError("Informe issue_id ou project_id.");
      }
      if (args.issue_id !== undefined && args.project_id !== undefined) {
        throw new RedmineError("Informe somente issue_id ou project_id.");
      }
      if (args.issue_id !== undefined) positiveInteger(args.issue_id, "issue_id");
      if (args.project_id !== undefined) projectIdentifier(args.project_id);
      if (!(Number(args.hours) > 0)) throw new RedmineError("hours deve ser maior que zero.");
      positiveInteger(args.activity_id, "activity_id");
      requiredText(args.comments, "comments");
      const timeEntry = Object.fromEntries(Object.entries(args).filter(([, value]) => value !== undefined));
      return await client.request("POST", "time_entries.json", { body: { time_entry: timeEntry } });
    }
    default:
      throw new RedmineError(`Ferramenta desconhecida: ${name}`);
  }
}
