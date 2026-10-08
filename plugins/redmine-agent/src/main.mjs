import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import readline from "node:readline";

import { handleMessage } from "./protocol.mjs";

function loadLocalEnv() {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
  const envPath = resolve(root, ".mcp.env");
  let content;
  try {
    content = readFileSync(envPath, "utf8");
  } catch (error) {
    if (error.code === "ENOENT") return;
    throw new Error(`Não foi possível ler .mcp.env: ${error.message}`);
  }
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const separator = line.indexOf("=");
    if (separator <= 0) throw new Error("Linha inválida em .mcp.env; esperado NOME=VALOR.");
    const name = line.slice(0, separator).trim();
    let value = line.slice(separator + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) throw new Error(`Nome inválido em .mcp.env: ${name}`);
    if (process.env[name] === undefined) process.env[name] = value;
  }
}

loadLocalEnv();

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
