import http from "node:http";
import https from "node:https";

export const DEFAULT_URL = "https://redmine.saude.ba.gov.br/";
export const MAX_PAGE_SIZE = 100;
const DEFAULT_TIMEOUT_MS = 30_000;
const MAX_RESPONSE_BYTES = 5 * 1024 * 1024;

export class RedmineError extends Error {
  constructor(message, status, { uncertain = false } = {}) {
    super(message);
    this.name = "RedmineError";
    this.status = status;
    this.uncertain = uncertain;
  }
}

export function validateBaseUrl(value) {
  const url = new URL(value || DEFAULT_URL);
  const localHttp = url.protocol === "http:" && ["127.0.0.1", "localhost"].includes(url.hostname);
  if (url.protocol !== "https:" && !localHttp) throw new RedmineError("REDMINE_URL deve usar HTTPS.");
  url.pathname = url.pathname.replace(/\/+$/, "") + "/";
  url.search = "";
  url.hash = "";
  return url;
}

export function redact(text, secret) {
  if (!text) return text;
  return secret ? String(text).split(secret).join("<redacted>") : String(text);
}

export function queryString(params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    query.set(key, String(value));
  }
  return query.toString();
}

export function positiveInteger(value, field) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) throw new RedmineError(`${field} deve ser um inteiro positivo.`);
  return parsed;
}

export function nonNegativeInteger(value, field) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) throw new RedmineError(`${field} deve ser um inteiro não negativo.`);
  return parsed;
}

export function boundedLimit(value) {
  if (value === undefined) return 25;
  return Math.min(positiveInteger(value, "limit"), MAX_PAGE_SIZE);
}

export function boundedOffset(value) {
  return value === undefined ? 0 : nonNegativeInteger(value, "offset");
}

export function requiredText(value, field) {
  if (typeof value !== "string" || !value.trim()) throw new RedmineError(`${field} é obrigatório.`);
  return value.trim();
}

export function compactIssue(issue) {
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

export function compactCurrentUser(user) {
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

export class RedmineClient {
  constructor({ baseUrl, apiKey, timeoutMs = DEFAULT_TIMEOUT_MS }) {
    this.baseUrl = validateBaseUrl(baseUrl);
    this.apiKey = requiredText(apiKey, "REDMINE_API_KEY");
    this.timeoutMs = positiveInteger(timeoutMs, "timeoutMs");
  }

  async request(method, path, { query, body } = {}) {
    const normalizedMethod = requiredText(method, "method").toUpperCase();
    const url = new URL(String(path).replace(/^\/+/, ""), this.baseUrl);
    if (url.origin !== this.baseUrl.origin) throw new RedmineError("Destino da requisição Redmine inválido.");
    const encodedQuery = queryString(query);
    if (encodedQuery) url.search = encodedQuery;
    const payload = body === undefined ? undefined : JSON.stringify(body);
    const transport = url.protocol === "https:" ? https : http;
    const writeMayBeUncertain = normalizedMethod !== "GET" && normalizedMethod !== "HEAD";

    return await new Promise((resolve, reject) => {
      const request = transport.request(
        url,
        {
          method: normalizedMethod,
          headers: {
            Accept: "application/json",
            "X-Redmine-API-Key": this.apiKey,
            ...(payload
              ? { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(payload) }
              : {}),
          },
          timeout: this.timeoutMs,
        },
        (response) => {
          const chunks = [];
          let received = 0;
          response.on("data", (chunk) => {
            received += chunk.length;
            if (received > MAX_RESPONSE_BYTES) {
              response.destroy(new RedmineError("Resposta do Redmine excedeu o limite permitido."));
              return;
            }
            chunks.push(chunk);
          });
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
          response.on("error", (error) => {
            reject(new RedmineError(redact(error.message, this.apiKey), undefined, { uncertain: writeMayBeUncertain }));
          });
        },
      );
      request.on("timeout", () => {
        const suffix = writeMayBeUncertain
          ? " O resultado da escrita é incerto; não repita automaticamente."
          : "";
        request.destroy(
          new RedmineError(`Tempo limite ao acessar o Redmine.${suffix}`, undefined, {
            uncertain: writeMayBeUncertain,
          }),
        );
      });
      request.on("error", (error) => {
        if (error instanceof RedmineError) {
          reject(error);
        } else {
          reject(
            new RedmineError(redact(error.message, this.apiKey), undefined, {
              uncertain: writeMayBeUncertain,
            }),
          );
        }
      });
      if (payload) request.write(payload);
      request.end();
    });
  }
}
