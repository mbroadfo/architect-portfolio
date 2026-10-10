import type { Snapshot } from "../shared/types.ts";

export interface ArtifactDocument {
  ok: boolean;
  path: string;
  title: string;
  markdown: string;
  truncated: boolean;
  error?: string;
}

export async function fetchSnapshot(intent: string, cli: "skip" | "refresh"): Promise<Snapshot> {
  const params = new URLSearchParams();
  params.set("cli", cli);
  if (intent) params.set("intent", intent);
  const queryText = params.toString();
  const query = queryText ? `?${queryText}` : "";
  const response = await fetch(`/api/snapshot${query}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { error?: string };
    throw new Error(body.error ?? `The observer returned ${response.status}.`);
  }
  return await response.json() as Snapshot;
}

export async function setWorkspace(target: string): Promise<string> {
  const response = await fetch("/api/workspace", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: target }),
  });
  const body = await response.json() as { ok?: boolean; workspace?: string; error?: string };
  if (!response.ok || !body.workspace) {
    throw new Error(body.error ?? "Could not change the workspace.");
  }
  return body.workspace;
}

export async function fetchArtifact(space: string, intent: string, artifactPath: string): Promise<ArtifactDocument> {
  const params = new URLSearchParams({ space, intent, path: artifactPath });
  const response = await fetch(`/api/artifact?${params}`, { cache: "no-store" });
  const body = await response.json() as ArtifactDocument;
  if (!response.ok || !body.markdown) {
    throw new Error(body.error ?? "Could not open that artifact.");
  }
  return body;
}
