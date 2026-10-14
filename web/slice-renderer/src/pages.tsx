// Static page templates. All owner text is rendered as React text, so it is always escaped
// (BR4.2). No inline scripts or styles; every element holds at most one text value, so the
// markup carries no separator comments. Fixed strings come from template-strings.json, the
// vocabulary the public-output scan allows (scripts/scan_output.py).
import type { ReactNode } from "react";
import preview from "./preview-strings.json";
import { STATIC_ASSETS } from "./static-assets";
import vocab from "./template-strings.json";
import type { AssetResolver, Exhibit, Image, PublicSiteSnapshot } from "./types";
import { downloadName, imageVariants } from "./variants";

export interface PageContext {
  snapshot: PublicSiteSnapshot;
  resolveAsset: AssetResolver;
  isPreview: boolean;
}

const { text, attributes: attr, classes } = vocab;

function srcset(image: Image, format: "webp" | "jpg", resolve: AssetResolver): string {
  return imageVariants(image)
    .map(({ variant, width }) => {
      const url = resolve({ kind: "image", assetRef: image.assetRef, variant, format });
      return `${url} ${width}w`;
    })
    .join(", ");
}

export function Picture({ image, ctx }: { image: Image; ctx: PageContext }) {
  const [smallest] = imageVariants(image);
  const fallback = ctx.resolveAsset({
    kind: "image",
    assetRef: image.assetRef,
    variant: smallest?.variant ?? "w480",
    format: "jpg",
  });
  return (
    <picture>
      <source
        type={attr.webp}
        srcSet={srcset(image, "webp", ctx.resolveAsset)}
        sizes={attr.sizes}
      />
      <img
        src={fallback}
        srcSet={srcset(image, "jpg", ctx.resolveAsset)}
        sizes={attr.sizes}
        alt={image.altText}
        width={image.width}
        height={image.height}
      />
    </picture>
  );
}

function Layout({
  ctx,
  title,
  children,
}: {
  ctx: PageContext;
  title: string;
  children: ReactNode;
}) {
  const { site } = ctx.snapshot;
  return (
    <html lang={attr.lang}>
      <head>
        <meta charSet={attr.charset} />
        <meta name={attr.viewportName} content={attr.viewport} />
        {ctx.isPreview ? <meta name={preview.robotsName} content={preview.noindex} /> : null}
        <title>{title}</title>
        <link rel={attr.stylesheet} href={STATIC_ASSETS.site.path} />
      </head>
      <body>
        {ctx.isPreview ? <p className={preview.bannerClass}>{preview.marking}</p> : null}
        <header className={classes.siteHeader}>
          <a className={classes.siteTitle} href={attr.home}>
            {site.ownerName}
          </a>
          <nav aria-label={attr.primaryNav}>
            <a href="/work/">{text.allWork}</a>
          </nav>
        </header>
        <main>{children}</main>
        <footer className={classes.siteFooter}>
          <a href={site.githubProfileUrl}>{text.github}</a>
        </footer>
      </body>
    </html>
  );
}

function Card({ exhibit, ctx }: { exhibit: Exhibit; ctx: PageContext }) {
  return (
    <li className={classes.card}>
      <a href={`/work/${exhibit.slug}`}>
        <Picture image={exhibit.leadImage} ctx={ctx} />
        <h3>{exhibit.title}</h3>
      </a>
    </li>
  );
}

function Gallery({ exhibits, ctx }: { exhibits: Exhibit[]; ctx: PageContext }) {
  return (
    <ul className={classes.gallery}>
      {exhibits.map((exhibit) => (
        <Card key={exhibit.slug} exhibit={exhibit} ctx={ctx} />
      ))}
    </ul>
  );
}

export function HomePage({ ctx }: { ctx: PageContext }) {
  const { exhibits, featuredOrder, categories, site } = ctx.snapshot;
  if (exhibits.length === 0) {
    return (
      <Layout ctx={ctx} title={site.ownerName}>
        <p className={classes.notice}>{text.newWork}</p>
      </Layout>
    );
  }
  const bySlug = new Map(exhibits.map((e) => [e.slug, e]));
  const featured = featuredOrder.flatMap((slug) => bySlug.get(slug) ?? []);
  return (
    <Layout ctx={ctx} title={site.ownerName}>
      {featured.length > 0 ? (
        <section>
          <h2>{text.featured}</h2>
          <Gallery exhibits={featured} ctx={ctx} />
        </section>
      ) : null}
      {categories.length > 0 ? (
        <nav>
          <h2>{text.categories}</h2>
          <ul>
            {categories.map((category) => (
              <li key={category.slug}>
                <a href={`/category/${category.slug}`}>{category.name}</a>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
      <section>
        <h2>{text.work}</h2>
        <Gallery exhibits={exhibits} ctx={ctx} />
      </section>
    </Layout>
  );
}

export function CatalogPage({ ctx }: { ctx: PageContext }) {
  return (
    <Layout ctx={ctx} title={text.allWork}>
      <h1>{text.allWork}</h1>
      <Gallery exhibits={ctx.snapshot.exhibits} ctx={ctx} />
    </Layout>
  );
}

export function CategoryPage({
  ctx,
  slug,
  name,
}: {
  ctx: PageContext;
  slug: string;
  name: string;
}) {
  const exhibits = ctx.snapshot.exhibits.filter((e) => e.primaryCategory?.slug === slug);
  return (
    <Layout ctx={ctx} title={name}>
      <h1>{name}</h1>
      <Gallery exhibits={exhibits} ctx={ctx} />
    </Layout>
  );
}

function ExhibitDetails({ exhibit, ctx }: { exhibit: Exhibit; ctx: PageContext }) {
  return (
    <>
      {exhibit.links.length > 0 ? (
        <section>
          <h2>{text.links}</h2>
          <ul>
            {exhibit.links.map((link) => (
              <li key={link.url}>
                <a href={link.url}>{link.label}</a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {exhibit.publicRepositories.length > 0 ? (
        <section>
          <h2>{text.repositories}</h2>
          <ul>
            {exhibit.publicRepositories.map((repository) => (
              <li key={repository.url}>
                <a href={repository.url}>{repository.name}</a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {exhibit.attachments.length > 0 ? (
        <section>
          <h2>{text.downloads}</h2>
          <ul>
            {exhibit.attachments.map((attachment) => (
              <li key={attachment.assetRef}>
                <a
                  href={ctx.resolveAsset({
                    kind: "download",
                    assetRef: attachment.assetRef,
                    downloadName: downloadName(attachment),
                  })}
                >
                  {attachment.label}
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </>
  );
}

export function ExhibitPage({ ctx, exhibit }: { ctx: PageContext; exhibit: Exhibit }) {
  return (
    <Layout ctx={ctx} title={exhibit.title}>
      <article className={classes.exhibit}>
        <h1>{exhibit.title}</h1>
        <Picture image={exhibit.leadImage} ctx={ctx} />
        {exhibit.summary ? <p className={classes.summary}>{exhibit.summary}</p> : null}
        <p className={classes.published}>
          <time dateTime={exhibit.publishedAt}>{exhibit.publishedAt.slice(0, 10)}</time>
        </p>
        {exhibit.images.map((image) => (
          <Picture key={image.assetRef} image={image} ctx={ctx} />
        ))}
        <ExhibitDetails exhibit={exhibit} ctx={ctx} />
      </article>
    </Layout>
  );
}

export function NotFoundPage({ ctx, message }: { ctx: PageContext; message: string }) {
  return (
    <Layout ctx={ctx} title={message}>
      <h1>{message}</h1>
      <p>
        <a href="/work/">{text.allWork}</a>
      </p>
    </Layout>
  );
}
