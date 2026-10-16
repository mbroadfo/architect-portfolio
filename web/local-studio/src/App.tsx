// The local Studio (L2, ADR-013): one page with hash routes for the approved Studio screens —
// Projects, the editor, preview, featured order, activity and the site build. The page holds
// no secrets: the server is reachable only from this machine and checks every change.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, type StudioApi } from "./api";
import { ActivityView } from "./ActivityView";
import { Dialog } from "./Dialog";
import { Editor } from "./Editor";
import { FeaturedView } from "./FeaturedView";
import { PreviewView } from "./PreviewView";
import { ProjectsView } from "./ProjectsView";
import { SiteView } from "./SiteView";

export const ApiContext = createContext<StudioApi>(api);
export const useApi = () => useContext(ApiContext);

export interface Route {
  view: "projects" | "edit" | "preview" | "featured" | "activity" | "site";
  id?: string;
}

const VIEWS = new Set<Route["view"]>([
  "projects",
  "edit",
  "preview",
  "featured",
  "activity",
  "site",
]);

export function parseRoute(hash: string): Route {
  const [view, id] = hash.replace(/^#/, "").split("/");
  if (!view || !VIEWS.has(view as Route["view"])) return { view: "projects" };
  const route = view as Route["view"];
  if ((route === "edit" || route === "preview") && !id) return { view: "projects" };
  return id ? { view: route, id: decodeURIComponent(id) } : { view: route };
}

const NAV: readonly (readonly [Route["view"], string])[] = [
  ["projects", "Projects"],
  ["featured", "Featured order"],
  ["activity", "Activity"],
  ["site", "Public site"],
];

export function App({ client = api }: { client?: StudioApi }) {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  const [pending, setPending] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const dirty = useRef(false);
  const current = useRef(window.location.hash);

  const setDirty = useCallback((value: boolean) => {
    dirty.current = value;
  }, []);

  useEffect(() => {
    function onHashChange() {
      const next = window.location.hash;
      if (dirty.current && next !== current.current) {
        window.history.replaceState(null, "", current.current || "#projects");
        setPending(next);
        return;
      }
      current.current = next;
      setRoute(parseRoute(next));
      window.scrollTo?.(0, 0);
    }
    function onBeforeUnload(event: BeforeUnloadEvent) {
      if (dirty.current) event.preventDefault();
    }
    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      window.removeEventListener("hashchange", onHashChange);
      window.removeEventListener("beforeunload", onBeforeUnload);
    };
  }, []);

  function leave() {
    const next = pending ?? "#projects";
    dirty.current = false;
    setPending(null);
    current.current = next;
    window.location.hash = next;
    setRoute(parseRoute(next));
  }

  return (
    <ApiContext.Provider value={client}>
      <a className="skip" href="#studio-main" onClick={(e) => e.preventDefault()}>
        Skip to content
      </a>
      <header className="studio-bar">
        <a className="studio-mark" href="#projects">
          Michael Broadfoot <span>Studio</span>
        </a>
        <nav className="studio-nav" aria-label="Studio">
          {NAV.map(([view, label]) => (
            <a key={view} href={`#${view}`} aria-current={route.view === view ? "page" : undefined}>
              {label}
            </a>
          ))}
        </nav>
        <span className="studio-signout">Local only · this machine</span>
      </header>
      <main id="studio-main" className="studio-main" tabIndex={-1}>
        {route.view === "projects" && <ProjectsView announce={setStatus} />}
        {route.view === "edit" && route.id && (
          <Editor key={route.id} id={route.id} setDirty={setDirty} announce={setStatus} />
        )}
        {route.view === "preview" && route.id && <PreviewView id={route.id} />}
        {route.view === "featured" && <FeaturedView announce={setStatus} />}
        {route.view === "activity" && <ActivityView />}
        {route.view === "site" && <SiteView />}
      </main>
      {pending !== null && (
        <Dialog title="Leave without saving?" onClose={() => setPending(null)}>
          <p className="sdialog__lede">You have unsaved changes. Nothing has been published.</p>
          <div className="sdialog__actions">
            <button className="btn btn--primary" type="button" onClick={() => setPending(null)}>
              Stay
            </button>
            <button className="btn btn--ghost" type="button" onClick={leave}>
              Discard unsaved changes
            </button>
          </div>
        </Dialog>
      )}
      <div className="visually-hidden" role="status" aria-live="polite">
        {status}
      </div>
    </ApiContext.Provider>
  );
}
