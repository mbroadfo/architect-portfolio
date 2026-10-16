// Exhibit page (FR9.2; ProjectDetail): lead image, title, summary and the links that exist,
// then the narrative sections (empty ones omitted), the details panel, the image gallery with
// an enlarged view, and the downloads block (omitted when empty). Details are derived only
// from exported C2 fields: badges, live URL, public repositories and links (FR4.10).
import { CATEGORY_ICONS, Icon } from "./icon";
import { Layout } from "./layout";
import {
  Badges,
  BadgeLabel,
  categoryPath,
  Highlights,
  largestImage,
  Picture,
  type PageContext,
} from "./parts";
import vocab from "./template-strings.json";
import type { Badge, Exhibit, Sections } from "./types";
import { downloadName } from "./variants";

const { text, attributes: attr, classes, ids } = vocab;

const SECTION_ORDER: readonly (keyof Sections)[] = [
  "inspiration",
  "designChallenges",
  "architecturalDecisions",
  "implementation",
  "outcomes",
  "lessonsLearned",
];

const has = (exhibit: Exhibit, kind: Badge["kind"]): boolean =>
  exhibit.badges.some((badge) => badge.kind === kind);

function presentSections(exhibit: Exhibit): [keyof Sections, string][] {
  return SECTION_ORDER.flatMap((key) => {
    const body = exhibit.sections[key];
    return body && body.trim() ? [[key, body] as [keyof Sections, string]] : [];
  });
}

function ExhibitHero({ exhibit, ctx }: { exhibit: Exhibit; ctx: PageContext }) {
  const category = exhibit.primaryCategory;
  const repository = exhibit.publicRepositories[0];
  return (
    <header className={classes.exhibitHero}>
      <div className={classes.exhibitHeroMedia}>
        <Picture image={exhibit.leadImage} ctx={ctx} sizes="hero" lazy={false} />
      </div>
      <div className={classes.exhibitHeroCopy}>
        <a className={classes.backLink} href={category ? categoryPath(category) : "/work/"}>
          <Icon name="prev" />
          {category ? category.name : text.allProjectsLower}
        </a>
        <h1>{exhibit.title}</h1>
        {exhibit.summary ? <p className={classes.exhibitHeroSummary}>{exhibit.summary}</p> : null}
        <Highlights exhibit={exhibit} />
        {exhibit.liveUrl || repository ? (
          <div className={classes.heroActions}>
            {exhibit.liveUrl ? (
              <a className={classes.buttonPrimary} href={exhibit.liveUrl} rel={attr.noopener}>
                {text.openApp}
                <Icon name="external" />
              </a>
            ) : null}
            {repository ? (
              <a className={classes.buttonGhost} href={repository.url} rel={attr.noopener}>
                <Icon name="github" />
                {text.viewSource}
              </a>
            ) : null}
          </div>
        ) : null}
        <Badges badges={exhibit.badges} />
      </div>
    </header>
  );
}

function accessText(exhibit: Exhibit): string {
  if (has(exhibit, "inBrowser")) return text.accessOpen;
  if (has(exhibit, "signInRequired")) return text.accessSignIn;
  if (has(exhibit, "byInvitation")) return text.accessInvitation;
  return text.accessNone;
}

function SourceRow({ exhibit }: { exhibit: Exhibit }) {
  const openSource = exhibit.badges.find((badge) => badge.kind === "openSource");
  const summary = openSource ? (
    <BadgeLabel badge={openSource} />
  ) : has(exhibit, "sourceAvailable") ? (
    <span>{text.sourceAvailable}</span>
  ) : has(exhibit, "sourcePrivate") ? (
    <span>{text.sourcePrivate}</span>
  ) : null;
  if (!summary && exhibit.publicRepositories.length === 0) return null;
  return (
    <div>
      <dt>
        <Icon name="code" />
        {text.source}
      </dt>
      <dd>
        {summary}
        {exhibit.publicRepositories.map((repository) => (
          <a key={repository.url} href={repository.url} rel={attr.noopener}>
            {repository.name}
          </a>
        ))}
      </dd>
    </div>
  );
}

function DetailsPanel({ exhibit }: { exhibit: Exhibit }) {
  const category = exhibit.primaryCategory;
  return (
    <aside className={classes.exhibitDetails} id={ids.details} aria-labelledby={ids.detailsHeading}>
      <h2 id={ids.detailsHeading}>{text.details}</h2>
      <dl>
        {category ? (
          <div>
            <dt>
              <Icon name={CATEGORY_ICONS[category.slug]} />
              {text.category}
            </dt>
            <dd>
              <a href={categoryPath(category)}>{category.name}</a>
            </dd>
          </div>
        ) : null}
        <div>
          <dt>
            <Icon name="cloud" />
            {text.access}
          </dt>
          <dd>{accessText(exhibit)}</dd>
        </div>
        {has(exhibit, "bestOnDesktop") ? (
          <div>
            <dt>
              <Icon name="gamepad" />
              {text.phones}
            </dt>
            <dd>{text.bestOnDesktop}</dd>
          </div>
        ) : null}
        <SourceRow exhibit={exhibit} />
        {exhibit.links.length > 0 ? (
          <div>
            <dt>
              <Icon name="link" />
              {text.links}
            </dt>
            <dd>
              {exhibit.links.map((link) => (
                <a key={link.url} href={link.url} rel={attr.noopener}>
                  {link.label}
                </a>
              ))}
            </dd>
          </div>
        ) : null}
      </dl>
    </aside>
  );
}

function Story({ sections }: { sections: [keyof Sections, string][] }) {
  return (
    <div className={classes.exhibitStory} id={ids.story}>
      {sections.map(([key, body]) => (
        <section
          key={key}
          className={classes.storySection}
          aria-labelledby={ids.sectionHeadings[key]}
        >
          <h2 id={ids.sectionHeadings[key]}>{vocab.sections[key]}</h2>
          <p>{body}</p>
        </section>
      ))}
    </div>
  );
}

function Gallery({ exhibit, ctx }: { exhibit: Exhibit; ctx: PageContext }) {
  return (
    <section
      className={classes.exhibitGallery}
      id={ids.gallery}
      aria-labelledby={ids.galleryHeading}
    >
      <h2 id={ids.galleryHeading}>{text.gallery}</h2>
      <ul className={classes.gallery}>
        {exhibit.images.map((image) => (
          <li key={image.assetRef}>
            <figure>
              <a className={classes.galleryButton} href={largestImage(image, ctx.resolveAsset)}>
                <span className={classes.visuallyHidden}>{text.enlarge}</span>{" "}
                <Picture image={image} ctx={ctx} sizes="gallery" />
              </a>
              {image.caption ? <figcaption>{image.caption}</figcaption> : null}
            </figure>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Downloads({ exhibit, ctx }: { exhibit: Exhibit; ctx: PageContext }) {
  return (
    <section
      className={classes.exhibitDownloads}
      id={ids.downloads}
      aria-labelledby={ids.downloadsHeading}
    >
      <h2 id={ids.downloadsHeading}>{text.downloads}</h2>
      <ul className={classes.downloads}>
        {exhibit.attachments.map((attachment) => (
          <li key={attachment.assetRef}>
            <a
              className={classes.download}
              href={ctx.resolveAsset({
                kind: "download",
                assetRef: attachment.assetRef,
                downloadName: downloadName(attachment),
              })}
            >
              <Icon name="download" />
              <span className={classes.downloadLabel}>{attachment.label}</span>{" "}
              <span className={classes.downloadType}>{attachment.fileType}</span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}

function InPageNav({ exhibit, hasStory }: { exhibit: Exhibit; hasStory: boolean }) {
  const items: [string, string][] = [
    ...(hasStory ? [[attr.fragmentStory, text.story] as [string, string]] : []),
    ...(exhibit.images.length > 0
      ? [[attr.fragmentGallery, text.gallery] as [string, string]]
      : []),
    ...(exhibit.attachments.length > 0
      ? [[attr.fragmentDownloads, text.downloads] as [string, string]]
      : []),
    [attr.fragmentDetails, text.details],
  ];
  return (
    <nav className={classes.exhibitNav} aria-label={attr.onThisPage}>
      {items.map(([href, label]) => (
        <a key={href} href={href}>
          {label}
        </a>
      ))}
    </nav>
  );
}

export function ExhibitPage({ ctx, exhibit }: { ctx: PageContext; exhibit: Exhibit }) {
  const sections = presentSections(exhibit);
  const category = exhibit.primaryCategory;
  const nav = category ? { category: category.slug, categoryCurrent: "true" as const } : {};
  return (
    <Layout ctx={ctx} title={exhibit.title} nav={nav}>
      <article className={classes.exhibit}>
        <ExhibitHero exhibit={exhibit} ctx={ctx} />
        <InPageNav exhibit={exhibit} hasStory={sections.length > 0} />
        <div className={classes.exhibitBody}>
          {sections.length > 0 ? <Story sections={sections} /> : null}
          <DetailsPanel exhibit={exhibit} />
        </div>
        {exhibit.images.length > 0 ? <Gallery exhibit={exhibit} ctx={ctx} /> : null}
        {exhibit.attachments.length > 0 ? <Downloads exhibit={exhibit} ctx={ctx} /> : null}
      </article>
    </Layout>
  );
}
