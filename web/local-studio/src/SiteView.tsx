// Public site: build the static site from published versions only, scan it, and view it on
// the local site server. Building never reads drafts.
import { useEffect, useState } from "react";
import { describe, type BuildResult } from "./api";
import { useApi } from "./App";

export function SiteView() {
  const client = useApi();
  const [site, setSite] = useState<{ output: string; url: string | null } | null>(null);
  const [result, setResult] = useState<BuildResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    client.site().then(
      (value) => live && setSite(value),
      (failure: unknown) => live && setError(describe(failure)),
    );
    return () => {
      live = false;
    };
  }, [client]);

  async function build() {
    setBusy(true);
    setError(null);
    try {
      setResult(await client.build());
    } catch (failure) {
      setResult(null);
      setError(describe(failure));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="studio-head">
        <div>
          <h1>Public site</h1>
          <p className="studio-head__sub">
            Generated only from published versions, then checked by the public-output scan. A failed
            build leaves the previous site in place.
          </p>
        </div>
        <div className="studio-head__actions">
          <button
            className="btn btn--primary"
            type="button"
            disabled={busy}
            onClick={() => void build()}
          >
            {busy ? "Building…" : "Build the public site"}
          </button>
          {site?.url && (
            <a className="btn btn--ghost" href={site.url} target="_blank" rel="noreferrer">
              View the generated site
            </a>
          )}
        </div>
      </header>
      {site && (
        <p className="field__hint">
          Output folder: <code>{site.output}</code>
        </p>
      )}
      {error && (
        <pre className="notice notice--error" role="alert">
          {error}
        </pre>
      )}
      {result && (
        <section className="panel" aria-label="Build result">
          <h2>Built</h2>
          <p>
            {result.exhibits} {result.exhibits === 1 ? "exhibit" : "exhibits"}, {result.pages}{" "}
            pages, {result.files} files.
          </p>
          <p className="field__hint">{result.scan}</p>
        </section>
      )}
    </>
  );
}
