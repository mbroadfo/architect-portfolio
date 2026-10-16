// Preview (FR6): the draft rendered by the shared renderer in preview mode, inside a sandboxed
// frame with no scripts. Every preview page is marked "Preview — not public" by the renderer.
import { useEffect, useState } from "react";
import { describe } from "./api";

type Page = "exhibit" | "home";

export function previewAddress(id: string, page: Page): string {
  return `/preview/${encodeURIComponent(id)}/${page}`;
}

async function check(address: string): Promise<string | null> {
  const response = await fetch(address, { credentials: "same-origin" });
  if (response.ok) return null;
  try {
    const body = (await response.json()) as { message?: unknown };
    return typeof body.message === "string" ? body.message : response.statusText;
  } catch {
    return response.statusText || "The preview could not be rendered.";
  }
}

export function PreviewView({ id }: { id: string }) {
  const [page, setPage] = useState<Page>("exhibit");
  const [checked, setChecked] = useState<{ address: string; problem: string | null } | null>(null);
  const address = previewAddress(id, page);
  const current = checked?.address === address ? checked : null;
  const problem = current?.problem ?? null;
  const ready = current !== null && current.problem === null;

  useEffect(() => {
    let live = true;
    check(address).then(
      (message) => live && setChecked({ address, problem: message }),
      (failure: unknown) => live && setChecked({ address, problem: describe(failure) }),
    );
    return () => {
      live = false;
    };
  }, [address]);

  return (
    <>
      <div className="preview-banner" role="note">
        Preview — not public
      </div>
      <header className="studio-head">
        <div>
          <a className="back-link" href={`#edit/${encodeURIComponent(id)}`}>
            Back to editor
          </a>
          <h1>Preview</h1>
          <p className="studio-head__sub">
            The saved draft, rendered by the same renderer as the public site. Unsaved changes are
            not shown.
          </p>
        </div>
        <div className="studio-head__actions" role="group" aria-label="Preview page">
          <button
            className={`btn btn--sm ${page === "exhibit" ? "btn--primary" : "btn--ghost"}`}
            type="button"
            aria-pressed={page === "exhibit"}
            onClick={() => setPage("exhibit")}
          >
            Exhibit page
          </button>
          <button
            className={`btn btn--sm ${page === "home" ? "btn--primary" : "btn--ghost"}`}
            type="button"
            aria-pressed={page === "home"}
            onClick={() => setPage("home")}
          >
            Home page with its card
          </button>
        </div>
      </header>
      {problem && (
        <p className="notice notice--error" role="alert">
          {problem}
        </p>
      )}
      {ready && (
        <iframe
          className="preview-frame"
          title={page === "exhibit" ? "Exhibit page preview" : "Home page preview"}
          src={address}
          sandbox="allow-same-origin"
          referrerPolicy="no-referrer"
        />
      )}
    </>
  );
}
