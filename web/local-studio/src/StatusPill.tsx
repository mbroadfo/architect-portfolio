import type { Status } from "./api";

const CLASSES: Record<Status, string> = {
  Draft: "status",
  Published: "status status--published",
  "Changes since last publish": "status status--changes",
  "Taken down": "status status--taken",
};

/** FR3.2: the project's one status, shown in words. */
export function StatusPill({ status }: { status: Status }) {
  return <span className={CLASSES[status]}>{status}</span>;
}
