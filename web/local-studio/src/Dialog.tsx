// A modal dialog in the approved Studio style: focus moves into it, Escape cancels.
import { useEffect, useId, useRef, type ReactNode } from "react";

export function Dialog({
  title,
  wide = false,
  onClose,
  children,
}: {
  title: string;
  wide?: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  const headingId = useId();
  const box = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);

  useEffect(() => {
    close.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    box.current?.querySelector<HTMLElement>("button, a, input, textarea, select")?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") close.current();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previous?.focus?.();
    };
  }, []);

  return (
    <div className="sdialog-backdrop">
      <div
        ref={box}
        className={`sdialog sdialog--open${wide ? " sdialog--wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
      >
        <div className={`sdialog__body${wide ? " sdialog__body--scroll" : ""}`}>
          <h2 id={headingId}>{title}</h2>
          {children}
        </div>
      </div>
    </div>
  );
}
