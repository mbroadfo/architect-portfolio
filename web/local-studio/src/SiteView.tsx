// Public site: build the static site from published versions only, scan it, and view it on
// the local site server. Building never reads drafts.
import { useEffect, useState } from "react";
import { describe, type BuildResult, type PackageResult } from "./api";
import { useApi } from "./App";

export function SiteView() {
  const client = useApi();
  const [site, setSite] = useState<{ output: string; url: string | null } | null>(null);
  const [result, setResult] = useState<BuildResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [packaged, setPackaged] = useState<PackageResult | null>(null);

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

  async function packagePages() {
    setBusy(true);
    setError(null);
    try {
      setPackaged(await client.packagePages());
    } catch (failure) {
      setPackaged(null);
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
          <button
            className="btn btn--ghost"
            type="button"
            disabled={busy}
            onClick={() => void packagePages()}
          >
            Package for Pages (staging)
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
      {packaged && (
        <section className="panel" aria-label="Pages package">
          <h2>Packaged for Cloudflare Pages ({packaged.mode})</h2>
          <p>
            {packaged.files} files, {packaged.bytes} bytes, from {packaged.buildId}. Exhibits:{" "}
            {packaged.exhibits.length
              ? packaged.exhibits
                  .map((e) => `${e.projectId} (revision ${e.sourceRevision})`)
                  .join(", ")
              : "none"}
            .
          </p>
          <p className="field__hint">{packaged.scan}</p>
          <p className="field__hint">
            Registered in the content repository: manifest <code>{packaged.manifestSha256}</code>
          </p>
          <p className="field__hint">
            Nothing was uploaded. Check it with a dry run: <code>{packaged.dryRun}</code>
          </p>
        </section>
      )}
    </>
  );
}
