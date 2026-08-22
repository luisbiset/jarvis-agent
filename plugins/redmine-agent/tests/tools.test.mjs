import assert from "node:assert/strict";
import { test } from "node:test";

import { callTool, tools } from "../src/tools.mjs";

class FakeClient {
  constructor() {
    this.requests = [];
  }

  async request(method, path, options = {}) {
    this.requests.push({ method, path, options });
    if (path === "users/current.json") {
      return { user: { id: 7, login: "tester", api_key: "server-secret" } }; // secret-scan: allow-test-fixture
    }
    if (path === "issues.json" && method === "GET") {
      return { issues: [{ id: 10, subject: "Teste", description: "não retornar" }] };
    }
    if (path === "issues.json" && method === "POST") return { issue: { id: 42 } };
    if (path === "issue_statuses.json") return { issue_statuses: [] };
    if (path === "trackers.json") return { trackers: [] };
    if (path === "enumerations/issue_priorities.json") return { issue_priorities: [] };
    if (path === "enumerations/time_entry_activities.json") return { time_entry_activities: [] };
    return {};
  }
}

test("mantém contrato das 11 ferramentas e suas anotações", () => {
  assert.deepEqual(
    tools.map((tool) => tool.name),
    [
      "get_current_user",
      "list_projects",
      "list_project_memberships",
      "list_issues",
      "get_issue",
      "list_metadata",
      "list_time_entries",
      "create_issue",
      "add_issue_note",
      "update_issue",
      "log_time",
    ],
  );
  assert.equal(tools.filter((tool) => tool.annotations.readOnlyHint).length, 7);
  assert.equal(tools.filter((tool) => !tool.annotations.readOnlyHint).length, 4);
});

test("remove api_key do usuário atual", async () => {
  const user = await callTool("get_current_user", {}, new FakeClient());
  assert.equal(user.user.id, 7);
  assert.equal("api_key" in user.user, false);
});

test("despacha todas as ferramentas de leitura", async () => {
  const client = new FakeClient();
  await callTool("list_projects", { limit: 10 }, client);
  await callTool("list_project_memberships", { project_id: "sfa" }, client);
  const issues = await callTool("list_issues", {}, client);
  await callTool("get_issue", { issue_id: 10 }, client);
  await callTool("list_metadata", {}, client);
  await callTool("list_time_entries", { user_id: "me" }, client);
  assert.equal(issues.issues[0].description, undefined);
  assert.equal(client.requests.length, 9);
});

test("despacha todas as ferramentas de escrita com payload esperado", async () => {
  const client = new FakeClient();
  const created = await callTool(
    "create_issue",
    { project_id: "sfa", subject: "Teste", description: "Descrição" },
    client,
  );
  await callTool("add_issue_note", { issue_id: 42, notes: "Nota" }, client);
  await callTool("update_issue", { issue_id: 42, status_id: 3 }, client);
  await callTool(
    "log_time",
    { issue_id: 42, hours: 1.5, activity_id: 9, comments: "Teste" },
    client,
  );
  assert.equal(created.issue.id, 42);
  assert.deepEqual(client.requests[0].options.body.issue, {
    project_id: "sfa",
    subject: "Teste",
    description: "Descrição",
  });
  assert.equal(client.requests[3].options.body.time_entry.hours, 1.5);
});

test("rejeita argumentos de escrita inválidos", async () => {
  const client = new FakeClient();
  await assert.rejects(() => callTool("update_issue", { issue_id: 42 }, client), /ao menos um campo/);
  await assert.rejects(
    () => callTool("log_time", { issue_id: 42, project_id: "sfa", hours: 1, activity_id: 9, comments: "x" }, client),
    /somente issue_id/,
  );
  await assert.rejects(() => callTool("create_issue", { project_id: "sfa" }, client), /subject/);
});
