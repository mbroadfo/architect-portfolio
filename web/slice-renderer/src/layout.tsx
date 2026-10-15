// The public shell (design-system-mapping: Sidebar / MobileBar / Drawer, SkipLink, footer):
// sidebar with wordmark, tagline, Home, All Projects, the populated categories and the credo;
// mobile bar with a menu link that opens the drawer (script) or targets it (no script); and
// the FR9.4 footer. Only the stylesheet and the one external script are loaded; nothing from
// another origin (FR9.5).
import type { ReactNode } from "react";
import { CATEGORY_ICONS, Icon } from "./icon";
import { categoryPath, orderedCategories, type PageContext } from "./parts";
import preview from "./preview-strings.json";
import { STATIC_ASSETS } from "./static-assets";
import vocab from "./template-strings.json";
import type { CategorySlug } from "./types";

const { text, attributes: attr, classes, ids } = vocab;

/** Which navigation entry is the current page, or which category the page belongs to. */
export interface NavState {
  active?: "home" | "all";
  category?: CategorySlug;
  /** "page" on the category's own page; "true" on an exhibit inside the category. */
  categoryCurrent?: "page" | "true";
}

function SideNav({ ctx, nav }: { ctx: PageContext; nav: NavState }) {
  const categories = orderedCategories(ctx.snapshot);
  const current = (on: boolean, value: "page" | "true" = "page") => (on ? value : undefined);
  return (
    <nav className={classes.sideNav} aria-label={attr.primaryNav}>
      <ul>
        <li>
          <a href={attr.home} aria-current={current(nav.active === "home")}>
            <Icon name="home" />
            {text.home}
          </a>
        </li>
        <li>
          <a href="/work/" aria-current={current(nav.active === "all")}>
            <Icon name="grid" />
            {text.allProjects}
          </a>
        </li>
      </ul>
      {categories.length > 0 ? (
        <>
          <p className={classes.sideNavLabel}>{text.categories}</p>
          <ul>
            {categories.map((category) => (
              <li key={category.slug}>
                <a
                  href={categoryPath(category)}
                  aria-current={current(nav.category === category.slug, nav.categoryCurrent)}
                >
                  <Icon name={CATEGORY_ICONS[category.slug]} />
                  {category.name}
                </a>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </nav>
  );
}

function Sidebar({ ctx, nav }: { ctx: PageContext; nav: NavState }) {
  const { ownerName } = ctx.snapshot.site;
  const [first, ...rest] = text.tagline;
  return (
    <aside className={classes.sidebar} id={ids.sidebar} aria-label={attr.site}>
      <div className={classes.sidebarTop}>
        <a className={classes.wordmark} href={attr.home}>
          {ownerName}
        </a>
        <p className={classes.tagline}>
          {first}
          {rest.map((word) => (
            <TaglineWord key={word} word={word} />
          ))}
        </p>
        <a className={classes.closeButton} href={attr.fragmentMain} aria-label={attr.closeMenu}>
          <Icon name="close" />
        </a>
      </div>
      <SideNav ctx={ctx} nav={nav} />
      <figure className={classes.credo}>
        <blockquote>{text.credo}</blockquote>
        <figcaption className={classes.signature}>{text.signature}</figcaption>
      </figure>
    </aside>
  );
}

function TaglineWord({ word }: { word: string }) {
  return (
    <>
      {" "}
      <span aria-hidden="true">{text.dot}</span> {word}
    </>
  );
}

function Footer({ ctx }: { ctx: PageContext }) {
  const { ownerName, githubProfileUrl, contactEmail } = ctx.snapshot.site;
  return (
    <footer className={classes.siteFoot}>
      <p className={classes.siteFootMark}>{ownerName}</p>
      <ul>
        <li>
          <a href={githubProfileUrl}>
            <Icon name="github" />
            {text.github}
          </a>
        </li>
        {contactEmail ? (
          <li>
            <a href={`mailto:${contactEmail}`}>
              <Icon name="mail" />
              {contactEmail}
            </a>
          </li>
        ) : null}
      </ul>
      <p className={classes.siteFootCopy}>
        {text.copyright} <span>{ownerName}</span>
      </p>
    </footer>
  );
}

export function Layout({
  ctx,
  title,
  nav,
  children,
}: {
  ctx: PageContext;
  title: string;
  nav: NavState;
  children: ReactNode;
}) {
  const { ownerName } = ctx.snapshot.site;
  return (
    <html lang={attr.lang}>
      <head>
        <meta charSet={attr.charset} />
        <meta name={attr.viewportName} content={attr.viewport} />
        {ctx.isPreview ? <meta name={preview.robotsName} content={preview.noindex} /> : null}
        <title>{title}</title>
        <link rel={attr.stylesheet} href={STATIC_ASSETS.site.path} />
        <script src={STATIC_ASSETS.script.path} defer />
      </head>
      <body>
        {ctx.isPreview ? <p className={preview.bannerClass}>{preview.marking}</p> : null}
        <a className={classes.skip} href={attr.fragmentMain}>
          {text.skip}
        </a>
        <div className={classes.shell}>
          <header className={classes.mobileBar}>
            <a className={classes.wordmarkStacked} href={attr.home}>
              {ownerName}
            </a>
            <a
              className={classes.menuButton}
              href={attr.fragmentSidebar}
              aria-controls={ids.sidebar}
              aria-label={attr.openMenu}
            >
              <Icon name="menu" />
            </a>
          </header>
          <Sidebar ctx={ctx} nav={nav} />
          <div className={classes.scrim} hidden />
          <main id={ids.main} tabIndex={-1}>
            {children}
            <Footer ctx={ctx} />
          </main>
        </div>
      </body>
    </html>
  );
}
