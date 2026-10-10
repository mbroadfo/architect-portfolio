import { useEffect, useState, type FormEvent } from "react";
import { fetchArtifact, fetchSnapshot, setWorkspace } from "./api.ts";
import type { ArtifactDocument } from "./api.ts";
import type { ArtifactLink, Snapshot } from "../shared/types.ts";
import { Dashboard } from "./ui.tsx";

export function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intent, setIntent] = useState("");
  const [auto, setAuto] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [filter, setFilter] = useState<"milestones" | "decisions" | "all">("milestones");
  const [stage, setStage] = useState<string | null>(null);
  const [workspaceInput, setWorkspaceInput] = useState("");
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<ArtifactLink | null>(null);
  const [document, setDocument] = useState<ArtifactDocument | null>(null);
  const [documentError, setDocumentError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const run = async (): Promise<void> => {
      try {
        const next = await fetchSnapshot(intent);
        if (cancelled) return;
        setSnapshot(next);
        setError(null);
        setWorkspaceInput((current) => current || next.workspace);
      } catch (caught) {
        if (cancelled) return;
        setError(caught instanceof Error ? caught.message : "Could not read the workflow.");
      }
    };
    void run();
    if (!auto) return () => {
      cancelled = true;
    };
    const timer = window.setInterval(() => {
      void run();
    }, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [intent, auto, reloadKey]);

  useEffect(() => {
    if (!artifact || !snapshot?.space || !snapshot.intent) return;
    let cancelled = false;
    setDocument(null);
    setDocumentError(null);
    void fetchArtifact(snapshot.space, snapshot.intent.dirName, artifact.path)
      .then((next) => {
        if (!cancelled) setDocument(next);
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setDocumentError(caught instanceof Error ? caught.message : "Could not open that artifact.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [artifact, snapshot?.space, snapshot?.intent]);

  useEffect(() => {
    if (!artifact) return;
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === "Escape") setArtifact(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [artifact]);

  async function watchWorkspace(event: FormEvent): Promise<void> {
    event.preventDefault();
    setWorkspaceError(null);
    try {
      const next = await setWorkspace(workspaceInput);
      setWorkspaceInput(next);
      setIntent("");
      setStage(null);
      setArtifact(null);
      setReloadKey((value) => value + 1);
    } catch (caught) {
      setWorkspaceError(caught instanceof Error ? caught.message : "Could not change the workspace.");
    }
  }

  return (
    <Dashboard
      snapshot={snapshot}
      error={error}
      intent={intent}
      auto={auto}
      filter={filter}
      stage={stage}
      workspaceInput={workspaceInput}
      workspaceError={workspaceError}
      artifact={artifact}
      document={document}
      documentError={documentError}
      onIntent={(value) => {
        setIntent(value);
        setStage(null);
        setArtifact(null);
      }}
      onAuto={setAuto}
      onFilter={setFilter}
      onStage={(value) => setStage((current) => current === value ? null : value)}
      onWorkspaceInput={setWorkspaceInput}
      onWatch={(event) => {
        void watchWorkspace(event);
      }}
      onRefresh={() => setReloadKey((value) => value + 1)}
      onOpenArtifact={setArtifact}
      onCloseArtifact={() => setArtifact(null)}
    />
  );
}
