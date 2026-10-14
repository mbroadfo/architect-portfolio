// The walking slice Studio page (S3): one page in four states — signed out, the project list,
// the editor, and preview with the Publish confirmation. It holds no secrets and makes no
// authorization decision of its own; the token lives in React state only (NFR15.2).
import { useState, type FormEvent } from "react";
import { ApiError, createClient, fetchToken, type ProjectView, type StudioClient } from "./api";
import { LOCAL_ONLY_FAKE_IDP_MARKER } from "./config";
import { renderPreview } from "./preview";

interface Notice {
  text: string;
  action?: "signin" | "reload";
}

interface Preview {
  html: string;
  revision: number;
}

function describe(error: unknown): Notice {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) {
      return { text: "Sign in again.", action: "signin" };
    }
    if (error.status === 409 && error.code === "STALE_REVISION") {
      return { text: "Reload: this project changed.", action: "reload" };
    }
    if (error.status === 409 && error.code === "SLUG_TAKEN") {
      return { text: "That slug is already in use." };
    }
    if (error.status === 422) return { text: error.message };
    return { text: `Something went wrong (${error.status}): ${error.message}` };
  }
  return { text: error instanceof Error ? error.message : "Something went wrong." };
}

export function App() {
  const [token, setToken] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectView[]>([]);
  const [current, setCurrent] = useState<ProjectView | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);

  const client: StudioClient | null = token ? createClient(token) : null;

  async function run(task: () => Promise<void>): Promise<void> {
    setBusy(true);
    setNotice(null);
    try {
      await task();
    } catch (error) {
      const described = describe(error);
      if (described.action === "signin") setToken(null);
      setNotice(described);
    } finally {
      setBusy(false);
    }
  }

  function open(project: ProjectView): void {
    setCurrent(project);
    setTitle(project.title);
    setSummary(project.summary);
    setPreview(null);
    setConfirming(false);
  }

  function signIn(): Promise<void> {
    return run(async () => {
      const issued = await fetchToken();
      setToken(issued);
      setProjects(await createClient(issued).list());
    });
  }

  function signOut(): void {
    setToken(null);
    setProjects([]);
    setCurrent(null);
    setPreview(null);
    setConfirming(false);
    setNotice(null);
  }

  function createProject(event: FormEvent): Promise<void> {
    event.preventDefault();
    return run(async () => {
      if (!client) return;
      const created = await client.create(newTitle);
      setNewTitle("");
      setProjects(await client.list());
      open(created);
    });
  }

  function save(event: FormEvent): Promise<void> {
    event.preventDefault();
    return run(async () => {
      if (!client || !current) return;
      open(await client.save(current.projectId, current.revision, { title, summary }));
      setNotice({ text: "Saved." });
    });
  }

  function reload(): Promise<void> {
    return run(async () => {
      if (!client || !current) return;
      open(await client.get(current.projectId));
    });
  }

  function showPreview(): Promise<void> {
    return run(async () => {
      if (!client || !current) return;
      const candidate = await client.preview(current.projectId);
      setPreview({ html: renderPreview(candidate, current.slug), revision: candidate.revision });
      setConfirming(false);
    });
  }

  function publish(): Promise<void> {
    return run(async () => {
      if (!client || !current || !preview) return;
      const result = await client.publish(current.projectId, preview.revision);
      open(await client.get(current.projectId));
      setProjects(await client.list());
      setNotice({ text: `Published revision ${result.sourceRevision}.` });
    });
  }

  function backToList(): Promise<void> {
    return run(async () => {
      if (!client) return;
      setCurrent(null);
      setPreview(null);
      setProjects(await client.list());
    });
  }

  return (
    <div className="studio" data-testid="studio">
      <header className="studio-header">
        <h1>Studio (local walking slice)</h1>
        {token ? (
          <button type="button" data-testid="signout-button" onClick={signOut}>
            Sign out
          </button>
        ) : null}
      </header>

      {notice ? (
        <div className="notice" role="status" data-testid="notice">
          <span data-testid="notice-text">{notice.text}</span>
          {notice.action === "signin" ? (
            <button type="button" data-testid="notice-signin-button" onClick={() => void signIn()}>
              Sign in again
            </button>
          ) : null}
          {notice.action === "reload" ? (
            <button type="button" data-testid="notice-reload-button" onClick={() => void reload()}>
              Reload
            </button>
          ) : null}
        </div>
      ) : null}

      {!token ? (
        <section data-testid="signed-out" data-local-only={LOCAL_ONLY_FAKE_IDP_MARKER}>
          <p>Sign in with the local identity provider to edit projects.</p>
          <button
            type="button"
            data-testid="signin-button"
            disabled={busy}
            onClick={() => void signIn()}
          >
            Sign in
          </button>
        </section>
      ) : null}

      {token && !current ? (
        <section data-testid="project-list">
          <h2>Projects</h2>
          <ul>
            {projects.map((project) => (
              <li key={project.projectId}>
                <button
                  type="button"
                  data-testid="project-list-open-button"
                  onClick={() => open(project)}
                >
                  {project.title}
                </button>
                <span className="status" data-testid="project-list-status">
                  {project.status}
                </span>
              </li>
            ))}
          </ul>
          <form onSubmit={(event) => void createProject(event)} data-testid="new-project-form">
            <label htmlFor="new-project-title">New project title</label>
            <input
              id="new-project-title"
              data-testid="new-project-title-input"
              value={newTitle}
              onChange={(event) => setNewTitle(event.target.value)}
            />
            <button type="submit" data-testid="new-project-create-button" disabled={busy}>
              New project
            </button>
          </form>
        </section>
      ) : null}

      {token && current ? (
        <section data-testid="editor">
          <p>
            <button
              type="button"
              data-testid="editor-back-button"
              onClick={() => void backToList()}
            >
              All projects
            </button>
          </p>
          <p>
            <span data-testid="editor-status">{current.status}</span>
            {" · "}
            <span data-testid="editor-revision">{`Revision ${current.revision}`}</span>
            {" · "}
            <span data-testid="editor-slug">{`/work/${current.slug}`}</span>
          </p>
          <form onSubmit={(event) => void save(event)} data-testid="editor-form">
            <label htmlFor="editor-title">Title</label>
            <input
              id="editor-title"
              data-testid="editor-title-input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
            <label htmlFor="editor-summary">Summary</label>
            <textarea
              id="editor-summary"
              data-testid="editor-summary-input"
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
            />
            <button type="submit" data-testid="editor-save-button" disabled={busy}>
              Save
            </button>
            <button
              type="button"
              data-testid="editor-preview-button"
              disabled={busy}
              onClick={() => void showPreview()}
            >
              Preview
            </button>
          </form>
        </section>
      ) : null}

      {token && current && preview ? (
        <section data-testid="preview">
          <h2>{`Preview of revision ${preview.revision}`}</h2>
          <iframe
            title="Preview — not public"
            data-testid="preview-frame"
            sandbox=""
            srcDoc={preview.html}
          />
          {confirming ? (
            <div data-testid="publish-confirmation">
              <p data-testid="publish-confirmation-text">
                {`Publish revision ${preview.revision} to the public site?`}
              </p>
              <button
                type="button"
                data-testid="publish-confirm-button"
                disabled={busy}
                onClick={() => void publish()}
              >
                {`Publish revision ${preview.revision}`}
              </button>
              <button
                type="button"
                data-testid="publish-cancel-button"
                onClick={() => setConfirming(false)}
              >
                Cancel
              </button>
            </div>
          ) : (
            <button type="button" data-testid="publish-button" onClick={() => setConfirming(true)}>
              Publish
            </button>
          )}
        </section>
      ) : null}
    </div>
  );
}
