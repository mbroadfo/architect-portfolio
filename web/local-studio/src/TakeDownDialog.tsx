// Take down (FR8): a confirmation naming the exhibit, with the FR8.4 notice.
import { useState } from "react";
import { describe } from "./api";
import { useApi } from "./App";
import { Dialog } from "./Dialog";

export function TakeDownDialog({
  id,
  title,
  featured,
  category,
  onClose,
  onDone,
}: {
  id: string;
  title: string;
  featured: boolean;
  category: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const client = useApi();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setBusy(true);
    try {
      await client.takeDown(id, title);
      onDone();
    } catch (failure) {
      setError(describe(failure));
      setBusy(false);
    }
  }

  return (
    <Dialog title={`Take down ${title}?`} onClose={onClose}>
      <ul className="sdialog__list">
        <li>
          Removes its page, gallery card and images from the published versions. The next site build
          leaves them out.
        </li>
        {featured && (
          <li>
            Removes it from the featured carousel. Its featured slot is released and won&apos;t come
            back automatically.
          </li>
        )}
        {category && (
          <li>
            Removes it from {category}. If that leaves the category empty, the category is hidden.
          </li>
        )}
        <li>Keeps everything in the Studio, so you can publish it again later.</li>
        <li>
          Can&apos;t withdraw copies already downloaded, or held in other caches, search engines or
          archives.
        </li>
      </ul>
      {error && (
        <p className="field__error" role="alert">
          {error}
        </p>
      )}
      <div className="sdialog__actions">
        <button className="btn btn--ghost" type="button" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn btn--danger"
          type="button"
          disabled={busy}
          onClick={() => void confirm()}
        >
          Take down {title}
        </button>
      </div>
    </Dialog>
  );
}
