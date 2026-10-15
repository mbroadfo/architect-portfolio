// The editor (FR3, FR4, FR10.6, FR10.7): every draft field, images with alt text and one lead
// image, links and access, repositories and the rights review. Saving sends the revision the
// editor loaded; a save from elsewhere in between is refused, never overwritten (FR3.4).
import { useCallback, useEffect, useState, type ChangeEvent } from "react";
import {
  ApiError,
  CATEGORIES,
  SECTIONS,
  describe,
  thumbnail,
  type Access,
  type CategorySlug,
  type DraftFields,
  type ImageView,
  type LinkKind,
  type Phone,
  type ProjectView,
} from "./api";
import { useApi } from "./App";
import { PublishDialog } from "./PublishDialog";
import { StatusPill } from "./StatusPill";
import { TakeDownDialog } from "./TakeDownDialog";

type ImageEdit = Pick<ImageView, "assetRef" | "altText" | "caption" | "lead">;

const ACCEPT = "image/jpeg,image/png,image/webp";

export function fieldsOf(project: ProjectView): DraftFields {
  return {
    title: project.title,
    slug: project.slug,
    summary: project.summary,
    sections: { ...project.sections },
    primaryCategory: project.primaryCategory,
    featured: project.featured,
    links: project.links.map((link) => ({ ...link })),
    liveUrl: project.liveUrl,
    liveUrlIncluded: project.liveUrlIncluded,
    liveUrlAuthorized: project.liveUrlAuthorized,
    access: project.access,
    phone: project.phone,
    repositories: project.repositories.map((r) => ({ ...r })),
    rightsReviewRequired: project.rightsReviewRequired,
    rightsReviewComplete: project.rightsReviewComplete,
  };
}

const imagesOf = (project: ProjectView): ImageEdit[] =>
  project.images.map(({ assetRef, altText, caption, lead }) => ({
    assetRef,
    altText,
    caption,
    lead,
  }));

export function Editor({
  id,
  setDirty,
  announce,
}: {
  id: string;
  setDirty: (dirty: boolean) => void;
  announce: (text: string) => void;
}) {
  const client = useApi();
  const [project, setProject] = useState<ProjectView | null>(null);
  const [fields, setFields] = useState<DraftFields | null>(null);
  const [images, setImages] = useState<ImageEdit[]>([]);
  const [dirty, setLocalDirty] = useState(false);
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [takingDown, setTakingDown] = useState(false);

  const markDirty = useCallback(
    (value: boolean) => {
      setLocalDirty(value);
      setDirty(value);
    },
    [setDirty],
  );

  const adopt = useCallback(
    (view: ProjectView) => {
      setProject(view);
      setFields(fieldsOf(view));
      setImages(imagesOf(view));
      markDirty(false);
      setConflict(false);
    },
    [markDirty],
  );

  const [version, setVersion] = useState(0);
  const load = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let live = true;
    client.get(id).then(
      (view) => live && adopt(view),
      (failure: unknown) => live && setMessage({ text: describe(failure), error: true }),
    );
    return () => {
      live = false;
    };
  }, [adopt, client, id, version]);

  useEffect(() => () => setDirty(false), [setDirty]);

  if (!project || !fields) {
    return message ? (
      <p className="notice notice--error" role="alert">
        {message.text}
      </p>
    ) : (
      <p>Loading…</p>
    );
  }

  function update<K extends keyof DraftFields>(key: K, value: DraftFields[K]) {
    setFields((current) => (current ? { ...current, [key]: value } : current));
    markDirty(true);
    setMessage(null);
  }

  function updateImage(index: number, change: Partial<ImageEdit>) {
    setImages((current) =>
      current.map((image, k) => {
        if (change.lead) return { ...image, lead: k === index, ...(k === index ? change : {}) };
        return k === index ? { ...image, ...change } : image;
      }),
    );
    markDirty(true);
  }

  async function save() {
    if (!project || !fields) return;
    setBusy(true);
    try {
      const saved = await client.save(project.id, project.revision, fields, images);
      adopt(saved);
      setMessage({
        text: `Saved · revision ${saved.revision} · the public copy is unchanged`,
        error: false,
      });
      announce(`Saved revision ${saved.revision}. Nothing has been published.`);
    } catch (failure) {
      setConflict(failure instanceof ApiError && failure.code === "STALE_REVISION");
      setMessage({ text: describe(failure), error: true });
    } finally {
      setBusy(false);
    }
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!project || files.length === 0) return;
    setBusy(true);
    let current = project;
    try {
      for (const file of files) {
        current = await client.upload(current.id, current.revision, file);
      }
      adopt(current);
      setMessage({ text: "Uploaded. Add alt text to each new image.", error: false });
    } catch (failure) {
      adopt(current);
      setMessage({ text: describe(failure), error: true });
    } finally {
      setBusy(false);
    }
  }

  const isPublic =
    project.status === "Published" || project.status === "Changes since last publish";
  const sections = fields.sections;
  return (
    <>
      <header className="studio-head studio-head--editor">
        <div>
          <a className="back-link" href="#projects">
            Projects
          </a>
          <h1>{project.title || "Untitled"}</h1>
          <p className="studio-head__sub">
            <StatusPill status={project.status} />{" "}
            <span className="savestate" aria-live="polite">
              {dirty
                ? "Unsaved changes · the public copy is unchanged"
                : `Saved · revision ${project.revision}`}
            </span>
          </p>
        </div>
        <div className="studio-head__actions">
          <button
            className="btn btn--ghost"
            type="button"
            disabled={busy || !dirty}
            onClick={() => void save()}
          >
            Save
          </button>
          <a className="btn btn--ghost" href={`#preview/${encodeURIComponent(project.id)}`}>
            Preview
          </a>
          <button
            className="btn btn--primary"
            type="button"
            disabled={busy || dirty}
            title={dirty ? "Save first" : undefined}
            onClick={() => setPublishing(true)}
          >
            {isPublic ? "Review update" : "Review publication"}
          </button>
          {isPublic && (
            <button className="btn btn--danger" type="button" onClick={() => setTakingDown(true)}>
              Take down
            </button>
          )}
        </div>
      </header>

      {message && (
        <p
          className={`notice${message.error ? " notice--error" : ""}`}
          role={message.error ? "alert" : "status"}
        >
          {message.text}{" "}
          {conflict && (
            <button className="btn btn--sm btn--ghost" type="button" onClick={() => void load()}>
              Reload the saved version
            </button>
          )}
        </p>
      )}

      {project.blockers.length > 0 && !dirty && (
        <section className="inv inv--block" aria-label="Before you can publish">
          <h3>Before you can publish</h3>
          <ul>
            {project.blockers.map((blocker) => (
              <li key={blocker.field}>{blocker.message}</li>
            ))}
          </ul>
        </section>
      )}

      <div className="editor editor--single">
        <form className="editor__form" onSubmit={(e) => e.preventDefault()} noValidate>
          <fieldset className="fs">
            <legend>Basics</legend>
            <label className="field">
              <span className="field__label">
                Title <span className="req">required</span>
              </span>
              <input
                value={fields.title}
                maxLength={120}
                onChange={(e) => update("title", e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">Address</span>
              <input
                value={fields.slug}
                maxLength={60}
                pattern="[a-z0-9]+(-[a-z0-9]+)*"
                onChange={(e) => update("slug", e.target.value.toLowerCase())}
              />
              <span className="field__hint">The public page is /work/{fields.slug}</span>
            </label>
            <label className="field">
              <span className="field__label">Summary</span>
              <textarea
                rows={2}
                maxLength={1200}
                value={fields.summary}
                onChange={(e) => update("summary", e.target.value)}
              />
            </label>
            <div className="field-row">
              <label className="field">
                <span className="field__label">Primary category</span>
                <select
                  value={fields.primaryCategory ?? ""}
                  onChange={(e) =>
                    update("primaryCategory", (e.target.value || null) as CategorySlug | null)
                  }
                >
                  <option value="">No category</option>
                  {CATEGORIES.map(([slug, name]) => (
                    <option key={slug} value={slug}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="field">
                <span className="field__label">Home page</span>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={fields.featured}
                    onChange={(e) => update("featured", e.target.checked)}
                  />{" "}
                  Feature in the carousel
                </label>
                <span className="field__hint">
                  Goes public with this project&apos;s Publish or Update. Up to 5 projects.
                </span>
              </div>
            </div>
          </fieldset>

          <fieldset className="fs">
            <legend>Story</legend>
            <p className="field__hint">Empty sections are left off the public page.</p>
            {SECTIONS.map(([key, label]) => (
              <label className="field" key={key}>
                <span className="field__label">{label}</span>
                <textarea
                  rows={4}
                  maxLength={8000}
                  value={sections[key]}
                  onChange={(e) => update("sections", { ...sections, [key]: e.target.value })}
                />
              </label>
            ))}
          </fieldset>

          <fieldset className="fs">
            <legend>Images</legend>
            <p className="field__hint">
              JPEG, PNG or WebP, up to 10 MB each, checked by content. Only re-encoded copies
              without metadata are ever published; originals stay private. Every image needs alt
              text, and one is the lead image.
            </p>
            <ul className="assets">
              {images.length === 0 && <li className="asset asset--empty">No images yet.</li>}
              {images.map((image, index) => (
                <li className="asset" key={image.assetRef}>
                  <img src={thumbnail(image.assetRef)} alt="" />
                  <label className="field">
                    <span className="field__label">Alt text for image {index + 1}</span>
                    <input
                      value={image.altText}
                      maxLength={300}
                      onChange={(e) => updateImage(index, { altText: e.target.value })}
                    />
                  </label>
                  <label className="field">
                    <span className="field__label">Caption for image {index + 1}</span>
                    <input
                      value={image.caption}
                      maxLength={300}
                      onChange={(e) => updateImage(index, { caption: e.target.value })}
                    />
                  </label>
                  <label className="check">
                    <input
                      type="radio"
                      name="lead"
                      checked={image.lead}
                      onChange={() => updateImage(index, { lead: true })}
                    />{" "}
                    Lead image
                  </label>
                  <button
                    className="btn btn--sm btn--ghost"
                    type="button"
                    onClick={() => {
                      setImages((current) => current.filter((_, k) => k !== index));
                      markDirty(true);
                    }}
                  >
                    Remove image {index + 1}
                  </button>
                </li>
              ))}
            </ul>
            <label className={`btn btn--ghost btn--sm${dirty || busy ? " btn--disabled" : ""}`}>
              Add images
              <input
                className="visually-hidden"
                type="file"
                accept={ACCEPT}
                multiple
                disabled={dirty || busy}
                onChange={(e) => void upload(e)}
              />
            </label>
            {dirty && <span className="field__hint"> Save your changes before adding images.</span>}
          </fieldset>

          <fieldset className="fs">
            <legend>Links and access</legend>
            <label className="field">
              <span className="field__label">
                Live app URL <span className="opt">optional</span>
              </span>
              <input
                type="url"
                placeholder="https://"
                value={fields.liveUrl}
                onChange={(e) => update("liveUrl", e.target.value)}
              />
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={fields.liveUrlAuthorized}
                onChange={(e) => update("liveUrlAuthorized", e.target.checked)}
              />{" "}
              Live URL authorized for publication (after a privacy and security review)
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={fields.liveUrlIncluded}
                onChange={(e) => update("liveUrlIncluded", e.target.checked)}
              />{" "}
              Include the live URL at Publish
            </label>
            <div className="field-row">
              <label className="field">
                <span className="field__label">Access to the linked app</span>
                <select
                  value={fields.access}
                  onChange={(e) => update("access", e.target.value as Access)}
                >
                  <option value="open">Open — no account</option>
                  <option value="sign-in">Sign-in required</option>
                  <option value="invitation">By invitation</option>
                </select>
              </label>
              <label className="field">
                <span className="field__label">Phone suitability</span>
                <select
                  value={fields.phone}
                  onChange={(e) => update("phone", e.target.value as Phone)}
                >
                  <option value="suitable">Works on phones</option>
                  <option value="desktop">Desktop only</option>
                  <option value="unknown">Not yet tested</option>
                </select>
              </label>
            </div>
            <RepositoriesField
              repositories={fields.repositories}
              onChange={(repositories) => update("repositories", repositories)}
            />
            <LinksField links={fields.links} onChange={(links) => update("links", links)} />
          </fieldset>

          <fieldset className="fs">
            <legend>Rights review</legend>
            <label className="check">
              <input
                type="checkbox"
                checked={fields.rightsReviewRequired}
                onChange={(e) => update("rightsReviewRequired", e.target.checked)}
              />{" "}
              This project needs a rights review (names or artwork of others)
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={fields.rightsReviewComplete}
                onChange={(e) => update("rightsReviewComplete", e.target.checked)}
              />{" "}
              Rights review complete — names and artwork cleared
            </label>
          </fieldset>
        </form>
      </div>

      {publishing && (
        <PublishDialog
          id={project.id}
          onClose={() => setPublishing(false)}
          onPublished={(text) => {
            setPublishing(false);
            announce(text);
            setMessage({ text, error: false });
            load();
          }}
        />
      )}
      {takingDown && (
        <TakeDownDialog
          id={project.id}
          title={project.title}
          featured={project.featured}
          category={CATEGORIES.find(([slug]) => slug === project.primaryCategory)?.[1] ?? null}
          onClose={() => setTakingDown(false)}
          onDone={() => {
            setTakingDown(false);
            setMessage({
              text: "Taken down. Build the site to remove it from the output.",
              error: false,
            });
            load();
          }}
        />
      )}
    </>
  );
}

function RepositoriesField({
  repositories,
  onChange,
}: {
  repositories: { url: string }[];
  onChange: (value: { url: string }[]) => void;
}) {
  return (
    <div className="field">
      <span className="field__label">
        Repositories <span className="opt">optional</span>
      </span>
      <span className="field__hint">
        https://github.com/owner/name. Visibility and licence are read from GitHub when you preview
        or review a publication; a repository that can&apos;t be confirmed public is treated as
        private and never named or linked.
      </span>
      {repositories.map((repository, index) => (
        <div className="field-inline" key={index}>
          <input
            aria-label={`Repository ${index + 1}`}
            value={repository.url}
            onChange={(e) =>
              onChange(repositories.map((r, k) => (k === index ? { url: e.target.value } : r)))
            }
          />
          <button
            className="btn btn--sm btn--ghost"
            type="button"
            onClick={() => onChange(repositories.filter((_, k) => k !== index))}
          >
            Remove repository {index + 1}
          </button>
        </div>
      ))}
      <button
        className="btn btn--sm btn--ghost"
        type="button"
        onClick={() => onChange([...repositories, { url: "https://github.com/" }])}
      >
        Add a repository
      </button>
    </div>
  );
}

function LinksField({
  links,
  onChange,
}: {
  links: DraftFields["links"];
  onChange: (value: DraftFields["links"]) => void;
}) {
  const set = (index: number, change: Partial<DraftFields["links"][number]>) =>
    onChange(links.map((link, k) => (k === index ? { ...link, ...change } : link)));
  return (
    <div className="field">
      <span className="field__label">
        Other links <span className="opt">optional</span>
      </span>
      {links.map((link, index) => (
        <div className="field-inline" key={index}>
          <select
            aria-label={`Link ${index + 1} kind`}
            value={link.kind}
            onChange={(e) => set(index, { kind: e.target.value as LinkKind })}
          >
            <option value="demo">Demo</option>
            <option value="documentation">Documentation</option>
            <option value="other">Other</option>
          </select>
          <input
            aria-label={`Link ${index + 1} label`}
            value={link.label}
            maxLength={80}
            onChange={(e) => set(index, { label: e.target.value })}
          />
          <input
            aria-label={`Link ${index + 1} address`}
            value={link.url}
            onChange={(e) => set(index, { url: e.target.value })}
          />
          <button
            className="btn btn--sm btn--ghost"
            type="button"
            onClick={() => onChange(links.filter((_, k) => k !== index))}
          >
            Remove link {index + 1}
          </button>
        </div>
      ))}
      <button
        className="btn btn--sm btn--ghost"
        type="button"
        onClick={() => onChange([...links, { kind: "demo", label: "", url: "https://" }])}
      >
        Add a link
      </button>
    </div>
  );
}
