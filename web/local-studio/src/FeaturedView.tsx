// Featured order (FR9.7): reorder the published carousel; it changes only through the
// explicit "Update featured order" confirmation.
import { useEffect, useState } from "react";
import { describe, type Featured } from "./api";
import { useApi } from "./App";
import { Dialog } from "./Dialog";

export function FeaturedView({ announce }: { announce: (text: string) => void }) {
  const client = useApi();
  const [featured, setFeatured] = useState<Featured | null>(null);
  const [order, setOrder] = useState<{ id: string; title: string }[]>([]);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    client.featured().then(
      (result) => {
        if (!live) return;
        setFeatured(result);
        setOrder(result.order);
      },
      (failure: unknown) => live && setError(describe(failure)),
    );
    return () => {
      live = false;
    };
  }, [client]);

  function move(index: number, delta: number) {
    const next = [...order];
    const [item] = next.splice(index, 1);
    if (item) next.splice(index + delta, 0, item);
    setOrder(next);
  }

  async function confirm() {
    try {
      const result = await client.updateFeatured(order.map((entry) => entry.id));
      setFeatured(result);
      setOrder(result.order);
      setConfirming(false);
      announce("Featured order updated. Build the site to show it.");
    } catch (failure) {
      setError(describe(failure));
      setConfirming(false);
    }
  }

  const changed = featured !== null && order.some((entry, k) => featured.order[k]?.id !== entry.id);
  return (
    <>
      <header className="studio-head">
        <div>
          <h1>Featured order</h1>
          <p className="studio-head__sub">
            {order.length} of {featured?.max ?? 5} published exhibits featured · drafts appear once
            published
          </p>
        </div>
        <div className="studio-head__actions">
          <button
            className="btn btn--primary"
            type="button"
            disabled={!changed}
            onClick={() => setConfirming(true)}
          >
            Update featured order…
          </button>
        </div>
      </header>
      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}
      <ol className="order">
        {order.length === 0 && <li className="order__item">No published exhibit is featured.</li>}
        {order.map((entry, index) => (
          <li className="order__item" key={entry.id}>
            <span className="order__n">{index + 1}</span>
            <span className="order__t">{entry.title}</span>
            <span className="order__btns">
              <button
                className="btn btn--sm btn--ghost"
                type="button"
                disabled={index === 0}
                aria-label={`Move ${entry.title} up`}
                onClick={() => move(index, -1)}
              >
                Up
              </button>
              <button
                className="btn btn--sm btn--ghost"
                type="button"
                disabled={index === order.length - 1}
                aria-label={`Move ${entry.title} down`}
                onClick={() => move(index, 1)}
              >
                Down
              </button>
            </span>
          </li>
        ))}
      </ol>
      {featured && featured.notYetPublished.length > 0 && (
        <p className="field__hint">
          Featured but not yet published: {featured.notYetPublished.map((p) => p.title).join(", ")}.
        </p>
      )}
      {confirming && (
        <Dialog title="Update featured order" onClose={() => setConfirming(false)}>
          <p className="sdialog__lede">The home page carousel will show, in this order:</p>
          <ol className="sdialog__list">
            {order.map((entry) => (
              <li key={entry.id}>{entry.title}</li>
            ))}
          </ol>
          <div className="sdialog__actions">
            <button className="btn btn--ghost" type="button" onClick={() => setConfirming(false)}>
              Cancel
            </button>
            <button className="btn btn--primary" type="button" onClick={() => void confirm()}>
              Update featured order
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}
