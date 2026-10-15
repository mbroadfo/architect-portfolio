// All-work catalog (/work/) and category pages (/category/<slug>), FR9.1 and FR9.8: category
// chips with published counts, a result count and the equal-card grid.
import { Layout } from "./layout";
import { Cards, categoryPath, orderedCategories, type PageContext } from "./parts";
import vocab from "./template-strings.json";
import type { CategorySlug } from "./types";

const { text, attributes: attr, classes, ids } = vocab;

function Chip({
  href,
  label,
  count,
  current,
}: {
  href: string;
  label: string;
  count: number;
  current: boolean;
}) {
  return (
    <a className={classes.chip} href={href} aria-current={current ? "page" : undefined}>
      {label} <span className={classes.chipCount}>{String(count)}</span>
    </a>
  );
}

function Chips({ ctx, current }: { ctx: PageContext; current?: CategorySlug }) {
  const categories = orderedCategories(ctx.snapshot);
  return (
    <nav className={classes.chips} aria-label={attr.browseByCategory}>
      <Chip
        href="/work/"
        label={text.all}
        count={ctx.snapshot.exhibits.length}
        current={current === undefined}
      />
      {categories.map((category) => (
        <Chip
          key={category.slug}
          href={categoryPath(category)}
          label={category.name}
          count={category.count}
          current={current === category.slug}
        />
      ))}
    </nav>
  );
}

function Listing({
  ctx,
  eyebrow,
  heading,
  lede,
  category,
}: {
  ctx: PageContext;
  eyebrow: string;
  heading: string;
  lede: string;
  category?: CategorySlug;
}) {
  const exhibits = category
    ? ctx.snapshot.exhibits.filter((e) => e.primaryCategory?.slug === category)
    : ctx.snapshot.exhibits;
  return (
    <section className={classes.catalog} aria-labelledby={ids.catalogHeading}>
      <header className={classes.pageHead}>
        <p className={classes.eyebrow}>{eyebrow}</p>
        <h1 id={ids.catalogHeading}>{heading}</h1>
        <p className={classes.pageHeadLede}>{lede}</p>
      </header>
      {exhibits.length === 0 ? (
        <p className={classes.notice}>{text.newWork}</p>
      ) : (
        <>
          <Chips ctx={ctx} current={category} />
          <p className={classes.resultCount}>
            <span>{String(exhibits.length)}</span>{" "}
            {exhibits.length === 1 ? text.publishedExhibit : text.publishedExhibits}
          </p>
          <Cards exhibits={exhibits} ctx={ctx} columns={3} />
        </>
      )}
    </section>
  );
}

export function CatalogPage({ ctx }: { ctx: PageContext }) {
  return (
    <Layout ctx={ctx} title={text.allProjects} nav={{ active: "all" }}>
      <Listing
        ctx={ctx}
        eyebrow={text.projects}
        heading={text.allProjects}
        lede={text.catalogLede}
      />
    </Layout>
  );
}

export function CategoryPage({
  ctx,
  slug,
  name,
}: {
  ctx: PageContext;
  slug: CategorySlug;
  name: string;
}) {
  return (
    <Layout ctx={ctx} title={name} nav={{ category: slug, categoryCurrent: "page" }}>
      <Listing
        ctx={ctx}
        eyebrow={text.category}
        heading={name}
        lede={vocab.categories[slug].lede}
        category={slug}
      />
    </Layout>
  );
}
