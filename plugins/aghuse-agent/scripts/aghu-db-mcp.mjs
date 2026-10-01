#!/usr/bin/env node

import { spawn } from "node:child_process";
import readline from "node:readline";
import fs from "node:fs";
import path from "node:path";

const SERVER_INFO = { name: "aghuse-db-readonly", version: "0.1.0" };
const MAX_QUERY_LENGTH = 12000;
const MAX_OUTPUT_LENGTH = 200000;

function loadEnvFile() {
  const file = process.env.AGHU_MCP_ENV_FILE || path.join(process.cwd(), ".mcp.env");
  if (!fs.existsSync(file)) return;
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (match && !process.env[match[1]]) process.env[match[1]] = match[2].replace(/^['"]|['"]$/g, "");
  }
}

loadEnvFile();

class DbError extends Error {}

function requiredEnv(name) {
  const value = process.env[name];
  if (!value || !value.trim()) throw new DbError(`${name} não configurada.`);
  return value.trim();
}

function validateQuery(query) {
  if (typeof query !== "string" || !query.trim()) throw new DbError("query é obrigatória.");
  const sql = query.trim();
  if (sql.length > MAX_QUERY_LENGTH) throw new DbError("query excede o limite permitido.");
  if (!/^select\b/i.test(sql) && !/^with\b/i.test(sql)) {
    throw new DbError("Somente consultas SELECT/WITH são permitidas.");
  }
  if (/[;]|\b(insert|update|delete|merge|alter|drop|truncate|create|grant|revoke|execute|call|begin|declare|commit|rollback)\b/i.test(sql)) {
    throw new DbError("A consulta contém operação não permitida.");
  }
  return sql;
}

function connectionString() {
  return `//${requiredEnv("AGHU_DB_HOST")}:${process.env.AGHU_DB_PORT || "1521"}/${requiredEnv("AGHU_DB_SERVICE")}`;
}

async function queryReadonly(query) {
  const sql = validateQuery(query);
  const user = requiredEnv("AGHU_DB_USER");
  const password = requiredEnv("AGHU_DB_PASSWORD");
  const input = [
    "set heading on",
    "set feedback on",
    "set pagesize 500",
    "set linesize 32767",
    "set trimspool on",
    "set long 10000",
    `connect ${user}/\"${password.replaceAll('"', '""')}\"@${connectionString()}`,
    `${sql};`,
    "exit",
    "",
  ].join("\n");

  const client = process.env.AGHU_SQLPLUS || (process.platform === "win32" ? "sql" : "sqlplus");
  const clientArgs = client.toLowerCase().endsWith("sqlplus") ? ["-S", "/nolog"] : ["-nolog"];

  return await new Promise((resolve, reject) => {
    const child = spawn(client, clientArgs, {
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", (error) => reject(new DbError(`Não foi possível iniciar sqlplus: ${error.message}`)));
    child.on("close", (code) => {
      const output = `${stdout}${stderr}`.replaceAll(password, "<redacted>");
      if (code !== 0 || /ORA-|SP2-|ERROR/i.test(output)) {
        reject(new DbError(output.slice(0, 5000) || `sqlplus terminou com código ${code}.`));
        return;
      }
      resolve({ readOnly: true, output: output.slice(0, MAX_OUTPUT_LENGTH) });
    });
    child.stdin.end(input);
  });
}

const tools = [{
  name: "query_readonly",
  title: "Consultar Oracle AGHUse (somente leitura)",
  description: "Executa somente SELECT/WITH no banco de desenvolvimento AGHUse. INSERT, UPDATE, DELETE, DDL, procedures e múltiplas instruções são bloqueados.",
  inputSchema: {
    type: "object",
    required: ["query"],
    properties: { query: { type: "string", minLength: 1, maxLength: MAX_QUERY_LENGTH } },
    additionalProperties: false,
  },
  annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
}];

function result(data) {
  return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }], structuredContent: data };
}

async function handle(message) {
  if (!message || message.jsonrpc !== "2.0") return;
  const response = { jsonrpc: "2.0", id: message.id };
  try {
    if (message.method === "initialize") {
      response.result = { protocolVersion: message.params?.protocolVersion || "2024-11-05", capabilities: { tools: { listChanged: false } }, serverInfo: SERVER_INFO, instructions: "Banco AGHUse de desenvolvimento, somente leitura. Nunca executar mutações." };
    } else if (message.method === "ping") {
      response.result = {};
    } else if (message.method === "tools/list") {
      response.result = { tools };
    } else if (message.method === "tools/call") {
      if (message.params?.name !== "query_readonly") throw new DbError("Ferramenta desconhecida.");
      response.result = result(await queryReadonly(message.params.arguments?.query));
    } else if (message.method === "notifications/initialized" || message.method === "notifications/cancelled") {
      return;
    } else {
      response.error = { code: -32601, message: `Método não suportado: ${message.method}` };
    }
  } catch (error) {
    response.result = { content: [{ type: "text", text: error instanceof DbError ? error.message : "Falha inesperada no MCP." }], isError: true };
  }
  if (message.id !== undefined) process.stdout.write(`${JSON.stringify(response)}\n`);
}

const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
input.on("line", (line) => { if (line.trim()) void handle(JSON.parse(line)); });
