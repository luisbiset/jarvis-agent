import { RedmineError } from "./client.mjs";
import { callTool, getClient, tools } from "./tools.mjs";

export const SERVER_INFO = { name: "redmine-sesab", version: "0.1.0" };

export function toolResult(data) {
  return {
    content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    structuredContent: data && typeof data === "object" && !Array.isArray(data) ? data : { result: data },
  };
}

export function errorResult(error) {
  const message = error instanceof RedmineError ? error.message : "Falha inesperada no agente Redmine.";
  return { content: [{ type: "text", text: message }], isError: true };
}

export async function handleMessage(message, { clientFactory = getClient, audit = () => {} } = {}) {
  if (!message || message.jsonrpc !== "2.0") return undefined;
  if (message.method === "notifications/initialized" || message.method === "notifications/cancelled") {
    return undefined;
  }
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
      const tool = message.params?.name;
      const started = Date.now();
      try {
        response.result = toolResult(
          await callTool(tool, message.params?.arguments || {}, clientFactory()),
        );
        audit({ event: "tool_call", tool, status: "ok", duration_ms: Date.now() - started });
      } catch (error) {
        audit({ event: "tool_call", tool, status: "error", duration_ms: Date.now() - started });
        throw error;
      }
    } else {
      response.error = { code: -32601, message: `Método não suportado: ${message.method}` };
    }
  } catch (error) {
    response.result = errorResult(error);
  }
  return message.id === undefined ? undefined : response;
}
