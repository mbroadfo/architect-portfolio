// Projects: every project with its status in words (FR3.2), New project (title only, FR3.1)
// and Take down for public exhibits (FR8.1).
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { describe, type ProjectSummary } from "./api";
import { useApi } from "./App";
import { Dialog } from "./Dialog";
import { StatusPill } from "./StatusPill";
import { TakeDownDialog } from "./TakeDownDialog";

const isPublic = (p: ProjectSummary) =>
  p.status === "Published" || p.status === "Changes since last publish";

export function ProjectsView({ announce }: { announce: (text: string) => void }) {
  const client = useApi();
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [takingDown, setTakingDown] = useState<ProjectSummary | null>(null);
  const [version, setVersion] = useState(0);
  const load = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let live = true;
    client.list().then(
      (result) => {
        if (!live) return;
        setProjects(result);
        setError(null);
      },
      (failure: unknown) => live && setError(describe(failure)),
    );
    return () => {
      live = false;
    };
  }, [client, version]);

  const count = projects?.length ?? 0;
  return (
    <>
      <header className="studio-head">
        <div>
          <h1>Projects</h1>
          <p className="studio-head__sub">
            {count} {count === 1 ? "project" : "projects"} · nothing changes on the public site
            until you publish and build it
          </p>
        </div>
        <div className="studio-head__actions">
          <button className="btn btn--primary" type="button" onClick={() => setCreating(true)}>
            New project
          </button>
        </div>
      </header>
      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}
      {projects && projects.length === 0 && (
        <div className="empty">
          <h2>No projects yet</h2>
          <p>Start from a title — images, text and links can be added later.</p>
        </div>
      )}
      {projects && projects.length > 0 && (
        <div className="ptable" role="table" aria-label="Projects">
          <div className="ptable__row ptable__row--head" role="row">
            <span role="columnheader">Project</span>
            <span role="columnheader">Category</span>
            <span role="columnheader">Status</span>
            <span role="columnheader">Featured</span>
            <span role="columnheader">Source</span>
            <span role="columnheader">
              <span className="visually-hidden">Actions</span>
            </span>
          </div>
          {projects.map((p) => (
            <div className="ptable__row" role="row" key={p.id} data-testid={`project-${p.id}`}>
              <span role="cell" className="ptable__title">
                <a href={`#edit/${encodeURIComponent(p.id)}`}>{p.title || "Untitled"}</a>
              </span>
              <span role="cell" data-label="Category">
                {p.category ?? "—"}
              </span>
              <span role="cell" data-label="Status">
                <StatusPill status={p.status} />
              </span>
              <span role="cell" data-label="Featured">
                {p.featured ? (p.featuredPosition ? `Yes · ${p.featuredPosition}` : "Yes") : "—"}
              </span>
              <span role="cell" data-label="Source">
                {p.repositories === 0
                  ? "No repository"
                  : `${p.repositories} ${p.repositories === 1 ? "repository" : "repositories"}`}
              </span>
              <span role="cell" className="ptable__actions">
                <a className="btn btn--sm btn--ghost" href={`#edit/${encodeURIComponent(p.id)}`}>
                  Edit
                </a>
                <a className="btn btn--sm btn--ghost" href={`#preview/${encodeURIComponent(p.id)}`}>
                  Preview
                </a>
                {isPublic(p) && (
                  <button
                    className="btn btn--sm btn--danger"
                    type="button"
                    onClick={() => setTakingDown(p)}
                  >
                    Take down
                  </button>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
      {creating && (
        <NewProjectDialog
          onClose={() => setCreating(false)}
          onCreated={(id, title) => {
            setCreating(false);
            announce(`${title} created as a draft.`);
            window.location.hash = `#edit/${encodeURIComponent(id)}`;
          }}
        />
      )}
      {takingDown && (
        <TakeDownDialog
          id={takingDown.id}
          title={takingDown.title}
          featured={takingDown.featured}
          category={takingDown.category}
          onClose={() => setTakingDown(null)}
          onDone={() => {
            announce(`${takingDown.title} taken down. Build the site to remove it.`);
            setTakingDown(null);
            load();
          }}
        />
      )}
    </>
  );
}

function NewProjectDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (id: string, title: string) => void;
}) {
  const client = useApi();
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) {
      setError("Give the project a title.");
      return;
    }
    setBusy(true);
    try {
      const created = await client.create(title.trim());
      onCreated(created.id, created.title);
    } catch (failure) {
      setError(describe(failure));
      setBusy(false);
    }
  }

  return (
    <Dialog title="New project" onClose={onClose}>
      <form onSubmit={(event) => void submit(event)} noValidate>
        <p className="sdialog__lede">
          A project can start with just a title. Everything else can be added later.
        </p>
        <label className="field">
          <span className="field__label">
            Title <span className="req">required</span>
          </span>
          <input
            name="title"
            value={title}
            maxLength={120}
            autoComplete="off"
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        {error && (
          <p className="field__error" role="alert">
            {error}
          </p>
        )}
        <div className="sdialog__actions">
          <button className="btn btn--ghost" type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn--primary" type="submit" disabled={busy}>
            Create draft
          </button>
        </div>
      </form>
    </Dialog>
  );
}
