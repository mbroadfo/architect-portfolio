// Activity (FR7.7): the content repository's Git history, newest first.
import { useEffect, useState } from "react";
import { describe } from "./api";
import { useApi } from "./App";

export function ActivityView() {
  const client = useApi();
  const [entries, setEntries] = useState<{ time: string; action: string }[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    client.activity().then(
      (result) => live && setEntries(result),
      (failure: unknown) => live && setError(describe(failure)),
    );
    return () => {
      live = false;
    };
  }, [client]);

  return (
    <>
      <header className="studio-head">
        <div>
          <h1>Activity</h1>
          <p className="studio-head__sub">
            Every save, upload, publish, update and take-down is a commit in the private content
            repository.
          </p>
        </div>
      </header>
      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}
      <ol className="activity">
        {entries?.map((entry, index) => (
          <li key={`${entry.time}-${index}`}>
            <span className="activity__t">{entry.time.replace("T", " ").slice(0, 16)}</span>{" "}
            <strong>{entry.action}</strong>
          </li>
        ))}
      </ol>
    </>
  );
}
