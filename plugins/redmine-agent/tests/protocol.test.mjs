import assert from "node:assert/strict";
import { test } from "node:test";

import { handleMessage } from "../src/protocol.mjs";

const fakeClient = { request: async () => ({ projects: [] }) };

test("negocia initialize e lista ferramentas", async () => {
  const initialized = await handleMessage({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: { protocolVersion: "2024-11-05" },
  });
  assert.equal(initialized.result.serverInfo.name, "redmine-sesab");

  const listed = await handleMessage({ jsonrpc: "2.0", id: 2, method: "tools/list" });
  assert.equal(listed.result.tools.length, 11);
});

test("não responde notificações e retorna erro para método desconhecido", async () => {
  const notification = await handleMessage({ jsonrpc: "2.0", method: "notifications/initialized" });
  assert.equal(notification, undefined);
  const unknown = await handleMessage({ jsonrpc: "2.0", id: 3, method: "missing" });
  assert.equal(unknown.error.code, -32601);
});

test("audita chamada sem registrar argumentos", async () => {
  const events = [];
  const response = await handleMessage(
    {
      jsonrpc: "2.0",
      id: 4,
      method: "tools/call",
      params: { name: "list_projects", arguments: { limit: 10 } },
    },
    { clientFactory: () => fakeClient, audit: (event) => events.push(event) },
  );
  assert.equal(response.result.isError, undefined);
  assert.deepEqual(Object.keys(events[0]).sort(), ["duration_ms", "event", "status", "tool"]);
});

test("converte falha de ferramenta em resultado MCP seguro", async () => {
  const response = await handleMessage(
    {
      jsonrpc: "2.0",
      id: 5,
      method: "tools/call",
      params: { name: "get_issue", arguments: { issue_id: 0 } },
    },
    { clientFactory: () => fakeClient },
  );
  assert.equal(response.result.isError, true);
  assert.match(response.result.content[0].text, /inteiro positivo/);
});
