// The public page templates (C9 pages) in the owner-approved crafted studio design (FR9.6):
// home, all work, category, exhibit, and the two not-on-display pages. All owner text is
// rendered as React text, so it is always escaped (BR4.2); no dangerouslySetInnerHTML, no
// inline scripts or styles. Fixed strings come from template-strings.json, the vocabulary the
// public-output scan allows (scripts/scan_output.py).
import { Icon } from "./icon";
import { Layout } from "./layout";
import type { PageContext } from "./parts";
import vocab from "./template-strings.json";

export { CatalogPage, CategoryPage } from "./catalog";
export { ExhibitPage } from "./exhibit";
export { HomePage } from "./home";
export { Picture, type PageContext } from "./parts";

const { text, classes, ids } = vocab;

/** NotOnDisplay (FR9.3, FR9.8): served with a 404 status; keeps the site navigation. */
export function NotFoundPage({ ctx, kind }: { ctx: PageContext; kind: "exhibit" | "category" }) {
  const message = kind === "category" ? text.categoryNotFound : text.notFound;
  return (
    <Layout ctx={ctx} title={message} nav={{}}>
      <section className={classes.missing} aria-labelledby={ids.missingHeading}>
        <p className={classes.eyebrow}>{kind === "category" ? text.category : text.exhibit}</p>
        <h1 id={ids.missingHeading}>{message}</h1>
        <p className={classes.pageHeadLede}>{text.notFoundLede}</p>
        <a className={classes.buttonPrimary} href="/work/">
          {text.seeAllWork}
          <Icon name="arrow" />
        </a>
      </section>
    </Layout>
  );
}
