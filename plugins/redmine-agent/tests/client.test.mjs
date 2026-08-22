import assert from "node:assert/strict";
import http from "node:http";
import { afterEach, test } from "node:test";

import {
  RedmineClient,
  boundedLimit,
  boundedOffset,
  queryString,
  validateBaseUrl,
} from "../src/client.mjs";

let activeServer;

afterEach(async () => {
  if (!activeServer) return;
  await new Promise((resolve) => activeServer.close(resolve));
  activeServer = undefined;
});

async function mockServer(handler) {
  activeServer = http.createServer(handler);
  await new Promise((resolve) => activeServer.listen(0, "127.0.0.1", resolve));
  const address = activeServer.address();
  return `http://127.0.0.1:${address.port}/`;
}

test("normaliza URL e rejeita HTTP remoto", () => {
  assert.equal(validateBaseUrl("https://example.test///").href, "https://example.test/");
  assert.throws(() => validateBaseUrl("http://example.test"), /HTTPS/);
});

test("normaliza paginação e query string", () => {
  assert.equal(queryString({ a: 1, b: undefined, c: "" }), "a=1");
  assert.equal(boundedLimit(500), 100);
  assert.equal(boundedOffset(undefined), 0);
  assert.throws(() => boundedOffset(-1), /não negativo/);
});

test("envia chave somente no header e interpreta JSON", async () => {
  const baseUrl = await mockServer((request, response) => {
    assert.equal(request.headers["x-redmine-api-key"], "test-key"); // secret-scan: allow-test-fixture
    assert.equal(request.url, "/projects.json?limit=10");
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ projects: [{ id: 1 }] }));
  });
  const client = new RedmineClient({ baseUrl, apiKey: "test-key" }); // secret-scan: allow-test-fixture
  const result = await client.request("GET", "projects.json", { query: { limit: 10 } });
  assert.equal(result.projects[0].id, 1);
});

for (const status of [401, 403, 404, 429, 500]) {
  test(`trata HTTP ${status} sem expor a chave`, async () => {
    const baseUrl = await mockServer((_request, response) => {
      response.writeHead(status, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ errors: ["falha test-key"] })); // secret-scan: allow-test-fixture
    });
    const client = new RedmineClient({ baseUrl, apiKey: "test-key" }); // secret-scan: allow-test-fixture
    await assert.rejects(
      () => client.request("GET", "issues.json"),
      (error) => error.status === status && !error.message.includes("test-key") && error.message.includes("<redacted>"),
    );
  });
}

test("marca escrita com timeout como resultado incerto", async () => {
  const baseUrl = await mockServer((_request, response) => {
    setTimeout(() => response.end("{}"), 100);
  });
  const client = new RedmineClient({ baseUrl, apiKey: "test-key", timeoutMs: 20 }); // secret-scan: allow-test-fixture
  await assert.rejects(
    () => client.request("POST", "issues.json", { body: { issue: { subject: "Teste" } } }),
    (error) => error.uncertain === true && /não repita automaticamente/.test(error.message),
  );
});
