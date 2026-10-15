// Home page (FR9.1): the featured carousel when any published exhibit is featured (FR9.7), the
// populated categories with their published counts (FR9.8), then the gallery of published
// exhibits. With nothing published, the installation notice.
import { CATEGORY_ICONS, Icon } from "./icon";
import { Layout } from "./layout";
import {
  Cards,
  categoryPath,
  exhibitPath,
  Highlights,
  orderedCategories,
  Picture,
  type PageContext,
} from "./parts";
import vocab from "./template-strings.json";
import type { CategoryWithCount, Exhibit } from "./types";

const { text, attributes: attr, classes, ids } = vocab;

function Slide({ exhibit, ctx, first }: { exhibit: Exhibit; ctx: PageContext; first: boolean }) {
  return (
    <div
      className={classes.heroSlide}
      role={attr.group}
      aria-roledescription={attr.slide}
      aria-label={exhibit.title}
      hidden={!first}
    >
      <div className={classes.heroMedia}>
        <Picture
          image={exhibit.leadImage}
          ctx={ctx}
          sizes="hero"
          className={classes.heroImage}
          lazy={!first}
        />
      </div>
      <div className={classes.heroCopy}>
        <p className={classes.eyebrow}>{text.featured}</p>
        <h2 className={classes.heroTitle}>{exhibit.title}</h2>
        <Highlights exhibit={exhibit} />
        {exhibit.summary ? <p className={classes.heroDesc}>{exhibit.summary}</p> : null}
        <div className={classes.heroActions}>
          <a className={classes.heroView} href={exhibitPath(exhibit)}>
            {text.viewProject}
            <Icon name="arrow" />
          </a>
          {exhibit.liveUrl ? (
            <a className={classes.heroOpen} href={exhibit.liveUrl} rel={attr.noopener}>
              {text.openTheApp}
              <Icon name="external" />
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/** FeaturedCarousel: server-rendered first slide; site.js reveals the controls (FR9.7). */
function Carousel({ featured, ctx }: { featured: Exhibit[]; ctx: PageContext }) {
  return (
    <section
      className={classes.hero}
      aria-roledescription={attr.carousel}
      aria-label={attr.featuredWork}
    >
      <nav className={classes.topNav} aria-label={attr.sectionsNav}>
        <a href="/work/">{text.projects}</a>
      </nav>
      {featured.map((exhibit, position) => (
        <Slide key={exhibit.slug} exhibit={exhibit} ctx={ctx} first={position === 0} />
      ))}
      {featured.length > 1 ? (
        <>
          <div className={classes.heroControls} hidden>
            <p className={classes.heroCount}>
              <span className={classes.heroIndex} />
              <span aria-hidden="true">{text.slash}</span>
              <span className={classes.heroTotal} />
            </p>
            <button className={classes.heroPrev} type="button" aria-label={attr.previousFeatured}>
              <Icon name="prev" />
            </button>
            <button className={classes.heroNext} type="button" aria-label={attr.nextFeatured}>
              <Icon name="arrow" />
            </button>
          </div>
          <div
            className={classes.heroDots}
            role={attr.group}
            aria-label={attr.chooseFeatured}
            hidden
          />
          <p className={classes.heroStatus} aria-live="polite" />
        </>
      ) : null}
    </section>
  );
}

function CategoryTile({ category, ctx }: { category: CategoryWithCount; ctx: PageContext }) {
  const cover = ctx.snapshot.exhibits.find((e) => e.primaryCategory?.slug === category.slug);
  return (
    <li className={classes.type}>
      <a href={categoryPath(category)}>
        {cover ? (
          <span className={classes.typeImage}>
            <Picture image={cover.leadImage} ctx={ctx} sizes="tile" decorative />
          </span>
        ) : null}
        <span className={classes.typeBody}>
          <Icon name={CATEGORY_ICONS[category.slug]} large />
          <span className={classes.typeTitle}>{category.name}</span>
          <span className={classes.typeSub}>{vocab.categories[category.slug].sub}</span>
          <span className={classes.typeCount}>
            <span>{String(category.count)}</span>{" "}
            <span>{category.count === 1 ? text.project : text.projectsLower}</span>
          </span>
        </span>
      </a>
    </li>
  );
}

const TYPE_GRIDS = { 1: classes.types2, 2: classes.types2, 3: classes.types3, 4: classes.types4 };

function Explore({ ctx }: { ctx: PageContext }) {
  const categories = orderedCategories(ctx.snapshot);
  if (categories.length === 0) return null;
  const grid = TYPE_GRIDS[categories.length as keyof typeof TYPE_GRIDS] ?? classes.types4;
  return (
    <section className={classes.explore} aria-labelledby={ids.exploreHeading}>
      <header className={classes.sectionHead}>
        <h2 id={ids.exploreHeading}>{text.explore}</h2>
        <a className={classes.linkMore} href="/work/">
          {text.viewAll}
          <Icon name="arrow" />
        </a>
      </header>
      <ul className={grid}>
        {categories.map((category) => (
          <CategoryTile key={category.slug} category={category} ctx={ctx} />
        ))}
      </ul>
      <a className={classes.viewAllMobile} href="/work/">
        {text.viewAll}
      </a>
    </section>
  );
}

export function HomePage({ ctx }: { ctx: PageContext }) {
  const { exhibits, featuredOrder, site } = ctx.snapshot;
  const nav = { active: "home" } as const;
  if (exhibits.length === 0) {
    return (
      <Layout ctx={ctx} title={site.ownerName} nav={nav}>
        <section className={classes.missing}>
          <h1 className={classes.visuallyHidden}>{site.ownerName}</h1>
          <p className={classes.notice}>{text.newWork}</p>
        </section>
      </Layout>
    );
  }
  const bySlug = new Map(exhibits.map((e) => [e.slug, e]));
  const featured = featuredOrder.flatMap((slug) => bySlug.get(slug) ?? []);
  return (
    <Layout ctx={ctx} title={site.ownerName} nav={nav}>
      <h1 className={classes.visuallyHidden}>{site.ownerName}</h1>
      {featured.length > 0 ? <Carousel featured={featured} ctx={ctx} /> : null}
      <Explore ctx={ctx} />
      <section className={classes.work} aria-labelledby={ids.workHeading}>
        <header className={classes.sectionHead}>
          <div>
            <h2 id={ids.workHeading}>{text.selectedWork}</h2>
            <p className={classes.sectionSub}>{text.selectedWorkSub}</p>
          </div>
          <a className={classes.linkMore} href="/work/">
            {text.allProjectsLower}
            <Icon name="arrow" />
          </a>
        </header>
        <Cards exhibits={exhibits} ctx={ctx} columns={2} />
      </section>
    </Layout>
  );
}
