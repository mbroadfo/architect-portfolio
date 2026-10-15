// The Publish confirmation (FR7.2, FR7.3, ADR-012): everything that becomes public, prepared
// by the server and bound to the reviewed revision. Confirming publishes exactly that.
import { useEffect, useState } from "react";
import { badgeLabel, describe, thumbnail, type Review } from "./api";
import { useApi } from "./App";
import { Dialog } from "./Dialog";

const SECTION_NAMES: Record<string, string> = {
  inspiration: "Inspiration",
  designChallenges: "Design challenges",
  architecturalDecisions: "Architectural decisions",
  implementation: "Implementation",
  outcomes: "Outcomes",
  lessonsLearned: "Lessons learned",
};

const shorten = (text: string) => (text.length > 160 ? `${text.slice(0, 160)}…` : text);

export function PublishDialog({
  id,
  onClose,
  onPublished,
}: {
  id: string;
  onClose: () => void;
  onPublished: (message: string) => void;
}) {
  const client = useApi();
  const [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    client.review(id).then(
      (result) => live && setReview(result),
      (failure: unknown) => live && setError(describe(failure)),
    );
    return () => {
      live = false;
    };
  }, [client, id]);

  async function confirm() {
    if (!review?.reviewId) return;
    setBusy(true);
    try {
      const result = await client.publish(id, review.revision, review.reviewId);
      onPublished(
        `${review.title} ${review.isUpdate ? "updated" : "published"} at revision ` +
          `${result.sourceRevision}. Build the public site to include it.`,
      );
    } catch (failure) {
      setError(describe(failure));
      setBusy(false);
    }
  }

  const heading = review?.isUpdate ? "Update the public exhibit" : "Publish";
  return (
    <Dialog
      title={review ? `${heading} · ${review.title || "Untitled"}` : "Publish"}
      wide
      onClose={onClose}
    >
      {!review && !error && <p>Preparing the review…</p>}
      {error && (
        <p className="field__error" role="alert">
          {error}
        </p>
      )}
      {review && (
        <>
          <p className="sdialog__lede">
            Everything below becomes public exactly as shown — revision {review.revision}, at{" "}
            <code>{review.address}</code>. Edits made after you confirm are not included.
          </p>
          <div className="inventory" aria-label="What will become public">
            {review.blockers.length > 0 && (
              <section className="inv inv--block" id="pub-blockers">
                <h3>Before you can publish</h3>
                <ul>
                  {review.blockers.map((b) => (
                    <li key={b.field}>{b.message}</li>
                  ))}
                </ul>
              </section>
            )}
            <section className="inv">
              <h3>Text</h3>
              <ul>
                {review.text.map((entry) => (
                  <li key={entry.label}>
                    <strong>{SECTION_NAMES[entry.label] ?? entry.label}</strong> —{" "}
                    {shorten(entry.value)}
                  </li>
                ))}
              </ul>
              <p className="inv__note">AI-originated text: none.</p>
            </section>
            <section className="inv">
              <h3>Images</h3>
              <ul className="inv__imgs">
                {review.images.length === 0 && <li>None</li>}
                {review.images.map((image) => (
                  <li key={image.assetRef}>
                    <img src={thumbnail(image.assetRef)} alt="" />
                    <span>
                      {image.lead && <strong>Lead · </strong>}
                      {image.altText ? image.altText : <em className="inv__bad">No alt text</em>}
                      {image.caption && <> · caption: {image.caption}</>}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
            <section className="inv">
              <h3>Links and access</h3>
              <ul>
                {review.liveUrl.url ? (
                  <li>
                    Live app: <code>{review.liveUrl.url}</code> (published exactly as entered)
                  </li>
                ) : (
                  <li>Live URL not published — {review.liveUrl.reason}.</li>
                )}
                {review.links.map((link) => (
                  <li key={link.url}>
                    {link.label}: <code>{link.url}</code>
                  </li>
                ))}
                {review.repositories.map((repository, index) =>
                  repository.confirmedPublic ? (
                    <li key={index}>
                      Source: <code>{repository.url}</code> — confirmed public on GitHub at{" "}
                      {repository.checkedAt} ·{" "}
                      {repository.licence ?? 'no licence → "Source available"'}
                    </li>
                  ) : (
                    <li key={index}>
                      A linked repository could not be confirmed public ({repository.note}) — no
                      name or link is published; the badge reads &quot;Source private&quot;.
                    </li>
                  ),
                )}
                <li>
                  Badges:{" "}
                  {review.badges.length ? review.badges.map(badgeLabel).join(" · ") : "none"}
                </li>
              </ul>
            </section>
            <section
              className={`inv${review.rightsReview === "outstanding" ? " inv--block" : " inv--warn"}`}
              aria-label="Rights review"
            >
              <h3>Rights review</h3>
              <p>
                {review.rightsReview === "not required"
                  ? "Not marked as needing one. Confirm that nothing here uses names or artwork that belong to someone else; if it does, mark the rights review as required in the editor first (FR10.6)."
                  : review.rightsReview === "complete"
                    ? "Recorded as complete: names and artwork cleared."
                    : "Outstanding: names and artwork must be cleared before publishing (FR10.6)."}
              </p>
            </section>
            <section className="inv">
              <h3>Placement</h3>
              <ul>
                <li>Category: {review.category ?? "none — gallery only"}</li>
                <li>Featured: {review.featured ? "yes" : "no"}</li>
              </ul>
            </section>
          </div>
        </>
      )}
      <div className="sdialog__actions sdialog__actions--sticky">
        <button className="btn btn--ghost" type="button" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn btn--primary"
          type="button"
          disabled={busy || !review?.reviewId}
          onClick={() => void confirm()}
        >
          {review?.isUpdate ? "Update the public exhibit" : "Publish this revision"}
        </button>
      </div>
    </Dialog>
  );
}
