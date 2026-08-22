import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import readline from "node:readline";

import { handleMessage } from "./protocol.mjs";

function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function audit(event) {
  process.stderr.write(`${JSON.stringify({ component: "redmine-agent", ...event })}\n`);
}

function runSelfTest() {
  const testFiles = [
    fileURLToPath(new URL("../tests/client.test.mjs", import.meta.url)),
    fileURLToPath(new URL("../tests/tools.test.mjs", import.meta.url)),
    fileURLToPath(new URL("../tests/protocol.test.mjs", import.meta.url)),
  ];
  const result = spawnSync(process.execPath, ["--test", ...testFiles], { stdio: "inherit" });
  if (result.error) {
    process.stderr.write(`redmine-agent self-test: falhou: ${result.error.message}\n`);
    return 1;
  }
  if (result.status === 0) process.stderr.write("redmine-agent self-test: ok\n");
  return result.status ?? 1;
}

async function serve() {
  const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of input) {
    if (!line.trim()) continue;
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      send({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "JSON inválido" } });
      continue;
    }
    const response = await handleMessage(message, { audit });
    if (response !== undefined) send(response);
  }
  return 0;
}

export async function main(args = process.argv) {
  return args.includes("--self-test") ? runSelfTest() : await serve();
}
