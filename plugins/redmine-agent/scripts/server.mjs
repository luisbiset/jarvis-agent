#!/usr/bin/env node

import http from "node:http";
import https from "node:https";
import readline from "node:readline";
import assert from "node:assert/strict";

const SERVER_INFO = { name: "redmine-sesab", version: "0.1.0" };
const DEFAULT_URL = "https://redmine.saude.ba.gov.br/";
const MAX_PAGE_SIZE = 100;

class RedmineError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "RedmineError";
    this.status = status;
  }
}

function validateBaseUrl(value) {
  const url = new URL(value || DEFAULT_URL);
  const localHttp = url.protocol === "http:" && ["127.0.0.1", "localhost"].includes(url.hostname);
  if (url.protocol !== "https:" && !localHttp) throw new RedmineError("REDMINE_URL deve usar HTTPS.");
  url.pathname = url.pathname.replace(/\/+$/, "") + "/";
  url.search = "";
  url.hash = "";
  return url;
}

function redact(text, secret) {
  if (!text) return text;
  return secret ? String(text).split(secret).join("<redacted>") : String(text);
}

function queryString(params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    query.set(key, String(value));
  }
  return query.toString();
}

function positiveInteger(value, field) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) throw new RedmineError(`${field} deve ser um inteiro positivo.`);
  return parsed;
}

function boundedLimit(value) {
  if (value === undefined) return 25;
  return Math.min(positiveInteger(value, "limit"), MAX_PAGE_SIZE);
}

function requiredText(value, field) {
  if (typeof value !== "string" || !value.trim()) throw new RedmineError(`${field} é obrigatório.`);
  return value.trim();
}

function compactIssue(issue) {
  return {
    id: issue.id,
    project: issue.project,
    tracker: issue.tracker,
    status: issue.status,
    priority: issue.priority,
    subject: issue.subject,
    author: issue.author,
    assigned_to: issue.assigned_to,
    start_date: issue.start_date,
    due_date: issue.due_date,
    done_ratio: issue.done_ratio,
    estimated_hours: issue.estimated_hours,
    spent_hours: issue.spent_hours,
    created_on: issue.created_on,
    updated_on: issue.updated_on,
  };
}

function compactCurrentUser(user) {
  return {
    id: user.id,
    login: user.login,
    admin: user.admin,
    firstname: user.firstname,
    lastname: user.lastname,
    mail: user.mail,
    created_on: user.created_on,
    updated_on: user.updated_on,
    last_login_on: user.last_login_on,
    custom_fields: user.custom_fields,
  };
}

class RedmineClient {
  constructor({ baseUrl, apiKey }) {
    this.baseUrl = validateBaseUrl(baseUrl);
    this.apiKey = requiredText(apiKey, "REDMINE_API_KEY");
  }

  async request(method, path, { query, body } = {}) {
    const url = new URL(path.replace(/^\/+/, ""), this.baseUrl);
    if (url.origin !== this.baseUrl.origin) throw new RedmineError("Destino da requisição Redmine inválido.");
    const encodedQuery = queryString(query);
    if (encodedQuery) url.search = encodedQuery;
    const payload = body === undefined ? undefined : JSON.stringify(body);
    const transport = url.protocol === "https:" ? https : http;

    return await new Promise((resolve, reject) => {
      const request = transport.request(
        url,
        {
          method,
          headers: {
            Accept: "application/json",
            "X-Redmine-API-Key": this.apiKey,
            ...(payload
              ? { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(payload) }
              : {}),
          },
          timeout: 30_000,
        },
        (response) => {
          const chunks = [];
          response.on("data", (chunk) => chunks.push(chunk));
          response.on("end", () => {
            const raw = Buffer.concat(chunks).toString("utf8");
            const status = response.statusCode || 0;
            let data = {};
            if (raw) {
              try {
                data = JSON.parse(raw);
              } catch {
                data = { message: raw.slice(0, 500) };
              }
            }
            if (status < 200 || status >= 300) {
              const details = Array.isArray(data.errors)
                ? data.errors.join("; ")
                : data.message || response.statusMessage || "Falha na API";
              reject(new RedmineError(`Redmine respondeu HTTP ${status}: ${redact(details, this.apiKey)}`, status));
              return;
            }
            resolve(data);
          });
        },
      );
      request.on("timeout", () => request.destroy(new RedmineError("Tempo limite ao acessar o Redmine.")));
      request.on("error", (error) => reject(new RedmineError(redact(error.message, this.apiKey))));
      if (payload) request.write(payload);
      request.end();
    });
  }
}

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

const tools = [
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

function getClient() {
  return new RedmineClient({
    baseUrl: process.env.REDMINE_URL || DEFAULT_URL,
    apiKey: process.env.REDMINE_API_KEY,
  });
}

async function callTool(name, args = {}, client = getClient()) {
  switch (name) {
    case "get_current_user": {
      const result = await client.request("GET", "users/current.json");
      return { user: compactCurrentUser(result.user || {}) };
    }
    case "list_projects":
      return await client.request("GET", "projects.json", {
        query: { limit: boundedLimit(args.limit), offset: args.offset || 0 },
      });
    case "list_project_memberships": {
      const project = encodeURIComponent(requiredText(String(args.project_id ?? ""), "project_id"));
      return await client.request("GET", `projects/${project}/memberships.json`, {
        query: { limit: boundedLimit(args.limit ?? 100), offset: args.offset || 0 },
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
          offset: args.offset || 0,
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
          offset: args.offset || 0,
        },
      });
    case "create_issue": {
      requiredText(args.subject, "subject");
      requiredText(args.description, "description");
      if (args.project_id === undefined || args.project_id === null || args.project_id === "") {
        throw new RedmineError("project_id é obrigatório.");
      }
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
      if (args.issue_id === undefined && args.project_id === undefined) throw new RedmineError("Informe issue_id ou project_id.");
      if (args.issue_id !== undefined && args.project_id !== undefined) throw new RedmineError("Informe somente issue_id ou project_id.");
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

function toolResult(data) {
  return {
    content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    structuredContent: data && typeof data === "object" && !Array.isArray(data) ? data : { result: data },
  };
}

function errorResult(error) {
  const message = error instanceof RedmineError ? error.message : "Falha inesperada no agente Redmine.";
  return { content: [{ type: "text", text: message }], isError: true };
}

function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

async function handleMessage(message) {
  if (!message || message.jsonrpc !== "2.0") return;
  if (message.method === "notifications/initialized" || message.method === "notifications/cancelled") return;
  const response = { jsonrpc: "2.0", id: message.id };
  try {
    if (message.method === "initialize") {
      response.result = {
        protocolVersion: message.params?.protocolVersion || "2024-11-05",
        capabilities: { tools: { listChanged: false } },
        serverInfo: SERVER_INFO,
        instructions:
          "Consulte o estado atual antes de alterar chamados. Ferramentas de escrita atuam no Redmine de produção e exigem confirmação explícita. Nunca solicite nem exponha a chave da API.",
      };
    } else if (message.method === "ping") {
      response.result = {};
    } else if (message.method === "tools/list") {
      response.result = { tools };
    } else if (message.method === "tools/call") {
      response.result = toolResult(await callTool(message.params?.name, message.params?.arguments || {}));
    } else {
      response.error = { code: -32601, message: `Método não suportado: ${message.method}` };
    }
  } catch (error) {
    response.result = errorResult(error);
  }
  if (message.id !== undefined) send(response);
}

async function selfTest() {
  assert.equal(validateBaseUrl("https://example.test///").href, "https://example.test/");
  assert.throws(() => validateBaseUrl("http://example.test"), /HTTPS/);
  assert.equal(queryString({ a: 1, b: undefined, c: "" }), "a=1");
  assert.equal(boundedLimit(500), 100);

  const requests = [];
  const mock = http.createServer((request, response) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      requests.push({
        method: request.method,
        url: request.url,
        key: request.headers["x-redmine-api-key"],
        body: Buffer.concat(chunks).toString("utf8"),
      });
      response.writeHead(request.method === "POST" ? 201 : 200, { "Content-Type": "application/json" });
      const responseBody = request.url === "/users/current.json"
        ? { user: { id: 7, login: "tester", admin: false, firstname: "Test", lastname: "User", api_key: "server-secret" } }
        : request.method === "POST"
          ? { issue: { id: 42 } }
          : { projects: [{ id: 1, name: "Teste" }], total_count: 1 };
      response.end(JSON.stringify(responseBody));
    });
  });

  await new Promise((resolve) => mock.listen(0, "127.0.0.1", resolve));
  const address = mock.address();
  const client = new RedmineClient({ baseUrl: `http://127.0.0.1:${address.port}/`, apiKey: "test-key" });
  const currentUser = await callTool("get_current_user", {}, client);
  assert.deepEqual(currentUser.user, {
    id: 7,
    login: "tester",
    admin: false,
    firstname: "Test",
    lastname: "User",
    mail: undefined,
    created_on: undefined,
    updated_on: undefined,
    last_login_on: undefined,
    custom_fields: undefined,
  });
  assert.equal("api_key" in currentUser.user, false);
  const projects = await callTool("list_projects", { limit: 10 }, client);
  assert.equal(projects.projects[0].name, "Teste");
  const created = await callTool(
    "create_issue",
    { project_id: "sfa", subject: "Teste", description: "Descrição" },
    client,
  );
  assert.equal(created.issue.id, 42);
  assert.equal(requests[0].key, "test-key");
  assert.match(requests[1].url, /projects\.json\?limit=10&offset=0/);
  assert.deepEqual(JSON.parse(requests[2].body), {
    issue: { project_id: "sfa", subject: "Teste", description: "Descrição" },
  });
  await new Promise((resolve) => mock.close(resolve));
  process.stderr.write("redmine-agent self-test: ok\n");
}

if (process.argv.includes("--self-test")) {
  await selfTest();
} else {
  const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  input.on("line", (line) => {
    if (!line.trim()) return;
    try {
      void handleMessage(JSON.parse(line));
    } catch {
      send({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "JSON inválido" } });
    }
  });
}
