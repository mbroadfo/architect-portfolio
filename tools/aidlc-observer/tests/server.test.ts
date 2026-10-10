import http from "node:http";
import type { AddressInfo } from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";
import type { Server } from "node:http";
import { startServer } from "../server/index.ts";

const fixtures = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "fixtures");
const servers: Server[] = [];

afterEach(async () => {
  await Promise.all(servers.splice(0).map((server) => new Promise<void>((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  })));
});

describe("local API", () => {
  it("binds to 127.0.0.1 and serves a read-only snapshot", async () => {
    const server = await listen(path.join(fixtures, "sample"));
    const address = server.address() as AddressInfo;
    expect(address.address).toBe("127.0.0.1");

    const health = await fetch(`http://127.0.0.1:${address.port}/api/health`);
    expect(await health.json()).toMatchObject({ ok: true, readOnly: true });

    const snapshot = await fetch(`http://127.0.0.1:${address.port}/api/snapshot`);
    const body = await snapshot.json() as { intent: { approval: { code: string }; currentStage: string } };
    expect(body.intent.currentStage).toBe("refined-mockups");
    expect(body.intent.approval.code).toBe("awaiting-approval");
  });

  it("rejects a non-local Host header", async () => {
    const server = await listen(path.join(fixtures, "sample"));
    const address = server.address() as AddressInfo;
    const status = await new Promise<number>((resolve, reject) => {
      const request = http.request({
        hostname: "127.0.0.1",
        port: address.port,
        path: "/api/health",
        headers: { host: "evil.example" },
      }, (response) => {
        response.resume();
        resolve(response.statusCode ?? 0);
      });
      request.on("error", reject);
      request.end();
    });
    expect(status).toBe(403);
  });

  it("serves an artifact inside the workflow and refuses paths outside it", async () => {
    const server = await listen(path.join(fixtures, "sample"));
    const address = server.address() as AddressInfo;
    const base = `http://127.0.0.1:${address.port}`;
    const artifactPath = "aidlc/spaces/default/intents/261010-sample-workflow/ideation/intent-capture/intent-statement.md";
    const allowed = await fetch(`${base}/api/artifact?${new URLSearchParams({
      space: "default",
      intent: "261010-sample-workflow",
      path: artifactPath,
    })}`);
    const document = await allowed.json() as { markdown?: string; title?: string };
    expect(allowed.status).toBe(200);
    expect(document.title).toBe("Intent statement");
    expect(document.markdown).toMatch(/three exhibits/);

    const escaped = await fetch(`${base}/api/artifact?${new URLSearchParams({
      space: "default",
      intent: "261010-sample-workflow",
      path: "../package.json",
    })}`);
    expect(escaped.status).toBe(404);

    const otherIntent = await fetch(`${base}/api/artifact?${new URLSearchParams({
      space: "default",
      intent: "261009-older-note",
      path: artifactPath,
    })}`);
    expect(otherIntent.status).toBe(404);
  });

  it("changes the watched directory only in memory", async () => {
    const server = await listen(path.join(fixtures, "sample"));
    const address = server.address() as AddressInfo;
    const base = `http://127.0.0.1:${address.port}`;
    const missing = await fetch(`${base}/api/workspace`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path.join(fixtures, "sample", "aidlc", "active-space") }),
    });
    expect(missing.status).toBe(400);

    const moved = await fetch(`${base}/api/workspace`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path.join(fixtures, "partial") }),
    });
    expect(moved.status).toBe(200);
    const snapshot = await fetch(`${base}/api/snapshot`);
    const body = await snapshot.json() as { intent: { currentStage: string } };
    expect(body.intent.currentStage).toBe("mystery-stage");
  });
});

async function listen(workspace: string): Promise<Server> {
  const server = await startServer({ workspace, port: 0, dev: false, cli: false });
  servers.push(server);
  return server;
}
