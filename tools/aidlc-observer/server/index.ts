import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createServer as createViteServer, type ViteDevServer } from "vite";
import { runAidlc, type CliName, type CliOutput } from "./cli.ts";
import { isDirectory, pathExists, readBytes, realPath } from "./read-only-fs.ts";
import { collectSnapshot } from "./snapshot.ts";
import { firstHeading } from "../shared/markdown.ts";
import { safeFileSlug, truncate } from "../shared/text.ts";

const HOST = "127.0.0.1";
const DEFAULT_PORT = 4317;
const TOOL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".webp": "image/webp",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
};

export interface ServerOptions {
  workspace: string;
  port: number;
  dev?: boolean;
  cli?: boolean;
  toolRoot?: string;
}

interface ServerContext {
  getWorkspace: () => string;
  setWorkspace: (value: string) => void;
  useCli: boolean;
  runCli: ((name: CliName, workspace: string) => Promise<CliOutput>) | null;
}

export async function startServer(options: ServerOptions): Promise<Server> {
  const toolRoot = options.toolRoot ?? TOOL_ROOT;
  const distDir = path.join(toolRoot, "dist");
  let workspace = path.resolve(options.workspace);
  const context: ServerContext = {
    getWorkspace: () => workspace,
    setWorkspace: (value) => {
      workspace = value;
    },
    useCli: options.cli !== false,
    runCli: options.cli === false ? null : runAidlc,
  };

  let vite: ViteDevServer | null = null;
  const server = createServer((req, res) => {
    void handleRequest(req, res, context, {
      dev: options.dev === true,
      getVite: () => vite,
      distDir,
    }).catch((error: unknown) => {
      const message = error instanceof Error ? error.message : "Request failed";
      if (!res.headersSent) sendJson(res, 500, { ok: false, error: truncate(message, 200) });
    });
  });

  if (options.dev) {
    vite = await createViteServer({
      root: toolRoot,
      configFile: path.join(toolRoot, "vite.config.ts"),
      server: {
        middlewareMode: true,
        host: HOST,
        hmr: { server },
      },
      appType: "spa",
    });
    server.on("close", () => {
      void vite?.close();
    });
  }

  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(options.port, HOST, () => {
      server.off("error", reject);
      resolve();
    });
  });
  return server;
}

async function handleRequest(
  req: IncomingMessage,
  res: ServerResponse,
  context: ServerContext,
  assets: { dev: boolean; getVite: () => ViteDevServer | null; distDir: string },
): Promise<void> {
  if (!isLocalRequest(req)) {
    sendJson(res, 403, { ok: false, error: "This observer only answers on localhost." });
    return;
  }

  const url = new URL(req.url ?? "/", `http://${HOST}`);
  if (url.pathname.startsWith("/api/")) {
    await handleApi(req, res, url, context);
    return;
  }

  const vite = assets.getVite();
  if (assets.dev && vite) {
    vite.middlewares(req, res, () => {
      sendText(res, 404, "Not found");
    });
    return;
  }

  serveStatic(res, assets.distDir, url.pathname);
}

async function handleApi(
  req: IncomingMessage,
  res: ServerResponse,
  url: URL,
  context: ServerContext,
): Promise<void> {
  if (req.method === "GET" && url.pathname === "/api/health") {
    sendJson(res, 200, { ok: true, readOnly: true, workspace: context.getWorkspace() });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/snapshot") {
    const intent = url.searchParams.get("intent");
    const space = url.searchParams.get("space");
    if (intent && !safeFileSlug(intent)) {
      sendJson(res, 400, { ok: false, error: "Workflow name contains unsupported characters." });
      return;
    }
    if (space && !safeFileSlug(space)) {
      sendJson(res, 400, { ok: false, error: "Space name contains unsupported characters." });
      return;
    }
    const snapshot = await collectSnapshot(context.getWorkspace(), {
      intent,
      space,
      runCli: context.runCli,
    });
    sendJson(res, 200, snapshot);
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/artifact") {
    const relativePath = url.searchParams.get("path") ?? "";
    const intent = url.searchParams.get("intent") ?? "";
    const space = url.searchParams.get("space") ?? "";
    if (!relativePath || !safeFileSlug(intent) || !safeFileSlug(space)) {
      sendJson(res, 400, { ok: false, error: "Artifact requests need a workflow, a space, and a path." });
      return;
    }
    const file = resolveArtifact(context.getWorkspace(), space, intent, relativePath);
    if (!file) {
      sendJson(res, 404, { ok: false, error: "That artifact is not in the selected workflow record." });
      return;
    }
    const bytes = readBytes(file);
    if (!bytes) {
      sendJson(res, 404, { ok: false, error: "That artifact is not in the selected workflow record." });
      return;
    }
    const markdown = bytes.toString("utf8");
    const truncated = markdown.length > 500_000;
    sendJson(res, 200, {
      ok: true,
      path: relativePath.replaceAll("\\", "/"),
      title: firstHeading(markdown) ?? path.basename(file),
      markdown: truncated ? markdown.slice(0, 500_000) : markdown,
      truncated,
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/workspace") {
    const body = await readJsonBody(req);
    const requested = body && typeof body.path === "string" ? body.path.trim() : "";
    if (!requested) {
      sendJson(res, 400, { ok: false, error: "Send a JSON object with a path." });
      return;
    }
    const resolved = path.resolve(requested);
    if (!isDirectory(resolved)) {
      sendJson(res, 400, { ok: false, error: "That path is not a directory." });
      return;
    }
    context.setWorkspace(realPath(resolved) ?? resolved);
    sendJson(res, 200, { ok: true, workspace: context.getWorkspace() });
    return;
  }

  sendJson(res, 404, { ok: false, error: "Unknown API route." });
}

function resolveArtifact(workspace: string, space: string, intent: string, relativePath: string): string | null {
  if (relativePath.includes("\0")) return null;
  const workspaceReal = realPath(workspace);
  if (!workspaceReal) return null;
  const intentRoot = path.resolve(workspaceReal, "aidlc", "spaces", space, "intents", intent);
  const intentReal = realPath(intentRoot);
  if (!intentReal || !isInside(workspaceReal, intentReal)) return null;
  const requested = path.resolve(workspaceReal, relativePath);
  if (!isInside(workspaceReal, requested)) return null;
  if (!pathExists(requested) || isDirectory(requested)) return null;
  const fileReal = realPath(requested);
  if (!fileReal || !isInside(intentReal, fileReal)) return null;
  if (!/\.(?:md|markdown)$/i.test(fileReal)) return null;
  return fileReal;
}

function isInside(root: string, target: string): boolean {
  const relative = path.relative(root, target);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function isLocalRequest(req: IncomingMessage): boolean {
  const host = String(req.headers.host ?? "").replace(/:\d+$/, "").replace(/^\[|\]$/g, "").toLowerCase();
  if (host !== "127.0.0.1" && host !== "localhost" && host !== "::1") return false;
  const origin = req.headers.origin;
  if (typeof origin === "string" && origin.length > 0) {
    try {
      const parsed = new URL(origin);
      const name = parsed.hostname.toLowerCase();
      if (name !== "127.0.0.1" && name !== "localhost" && name !== "::1") return false;
    } catch {
      return false;
    }
  }
  return true;
}

function serveStatic(res: ServerResponse, distDir: string, urlPath: string): void {
  const distReal = realPath(distDir);
  if (!distReal) {
    sendText(res, 404, "The UI has not been built. Run npm run dev, or npm run build and then npm start.");
    return;
  }
  const decoded = decodeURIComponent((urlPath.split("?")[0] ?? "/"));
  const relative = decoded === "/" ? "index.html" : decoded.replace(/^\/+/, "");
  const target = resolveInside(distReal, relative) ?? (!path.extname(relative) ? resolveInside(distReal, "index.html") : null);
  if (!target) {
    sendText(res, 404, "Not found");
    return;
  }
  const bytes = readBytes(target);
  if (!bytes) {
    sendText(res, 404, "Not found");
    return;
  }
  const type = MIME[path.extname(target).toLowerCase()] ?? "application/octet-stream";
  res.statusCode = 200;
  res.setHeader("Content-Type", type);
  res.setHeader("Cache-Control", "no-store");
  res.end(bytes);
}

function resolveInside(root: string, relative: string): string | null {
  if (relative.includes("\0")) return null;
  const target = path.resolve(root, relative);
  if (!isInside(root, target)) return null;
  const real = realPath(target);
  if (!real || !isInside(root, real) || isDirectory(real)) return null;
  return real;
}

async function readJsonBody(req: IncomingMessage): Promise<Record<string, unknown> | null> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.length;
    if (size > 8192) throw new Error("Request body is too large.");
    chunks.push(buffer);
  }
  const text = Buffer.concat(chunks).toString("utf8").trim();
  if (!text) return null;
  const parsed = JSON.parse(text) as unknown;
  return parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)
    ? parsed as Record<string, unknown>
    : null;
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(body));
}

function sendText(res: ServerResponse, status: number, body: string): void {
  res.statusCode = status;
  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(body);
}

function findWorkspace(start: string): string | null {
  let dir = path.resolve(start);
  for (let hop = 0; hop < 8; hop += 1) {
    if (isDirectory(path.join(dir, "aidlc"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
  return null;
}

function parseArgs(argv: string[]): { workspace?: string; port?: number; dev: boolean; cli: boolean } {
  let workspace: string | undefined;
  let port: number | undefined;
  let dev = false;
  let cli = true;
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--dev") dev = true;
    else if (arg === "--no-cli") cli = false;
    else if (arg === "--help" || arg === "-h") {
      process.stdout.write(`AI-DLC Observer\n\n  --workspace <path>   Project to watch (default: walk upward for an aidlc directory)\n  --port <number>      Port on 127.0.0.1 (default: ${DEFAULT_PORT})\n  --dev                Serve the Vite UI\n  --no-cli             Do not call AI-DLC; read record files only\n`);
      process.exit(0);
    } else if (arg === "--workspace") {
      workspace = argv[index + 1];
      index += 1;
      if (!workspace) throw new Error("--workspace needs a path.");
    } else if (arg === "--port") {
      port = Number(argv[index + 1]);
      index += 1;
      if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error("--port needs a whole number from 0 to 65535.");
    } else {
      throw new Error(`Unknown argument "${arg}". Run with --help.`);
    }
  }
  return { workspace, port, dev, cli };
}

function isDirectRun(): boolean {
  const entry = process.argv[1];
  if (!entry) return false;
  return path.resolve(entry).toLowerCase() === fileURLToPath(import.meta.url).toLowerCase();
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const envWorkspace = process.env.AIDLC_OBSERVER_WORKSPACE?.trim();
  const envPort = process.env.AIDLC_OBSERVER_PORT ? Number(process.env.AIDLC_OBSERVER_PORT) : undefined;
  const workspace = path.resolve(
    args.workspace
      ?? envWorkspace
      ?? findWorkspace(process.cwd())
      ?? findWorkspace(TOOL_ROOT)
      ?? process.cwd(),
  );
  const port = args.port ?? (Number.isInteger(envPort) ? envPort! : DEFAULT_PORT);
  if (!isDirectory(workspace)) {
    throw new Error(`Workspace is not a directory: ${workspace}`);
  }
  const server = await startServer({ workspace, port, dev: args.dev, cli: args.cli });
  const address = server.address();
  const bound = address && typeof address === "object" ? address.port : port;
  process.stdout.write(
    `AI-DLC Observer\n  http://${HOST}:${bound}\n  workspace: ${workspace}\n  mode: read-only\n`,
  );
}

if (isDirectRun()) {
  void main().catch((error: unknown) => {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`${message}\n`);
    process.exit(1);
  });
}
