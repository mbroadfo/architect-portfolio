// Building blocks shared by the public pages: responsive pictures, derived badges and exhibit
// cards. All owner text is rendered as React text, so it is always escaped (BR4.2). Fixed
// strings come from template-strings.json, the vocabulary the public-output scan allows.
import { Icon, CATEGORY_ICONS } from "./icon";
import vocab from "./template-strings.json";
import type {
  AssetResolver,
  Badge,
  Category,
  CategoryWithCount,
  Exhibit,
  Image,
  PublicSiteSnapshot,
} from "./types";
import { imageVariants } from "./variants";

export interface PageContext {
  snapshot: PublicSiteSnapshot;
  resolveAsset: AssetResolver;
  isPreview: boolean;
}

const { text, attributes: attr, classes } = vocab;

export type SizesName = keyof typeof attr.sizes;

const LIVE_BADGES = new Set<Badge["kind"]>(["inBrowser", "signInRequired", "byInvitation"]);
const ACCESS_BADGES = new Set<Badge["kind"]>([...LIVE_BADGES, "bestOnDesktop"]);

export const exhibitPath = (exhibit: Pick<Exhibit, "slug">): string => `/work/${exhibit.slug}`;
export const categoryPath = (category: Pick<Category, "slug">): string =>
  `/category/${category.slug}`;

/** The categories in their fixed display order. */
export function orderedCategories(snapshot: PublicSiteSnapshot): CategoryWithCount[] {
  return [...snapshot.categories].sort(
    (a, b) => a.position - b.position || a.slug.localeCompare(b.slug),
  );
}

function srcset(image: Image, format: "webp" | "jpg", resolve: AssetResolver): string {
  return imageVariants(image)
    .map(({ variant, width }) => {
      const url = resolve({ kind: "image", assetRef: image.assetRef, variant, format });
      return `${url} ${width}w`;
    })
    .join(", ");
}

/** Address of the largest JPEG variant: the no-script target of the enlarged view. */
export function largestImage(image: Image, resolve: AssetResolver): string {
  const variants = imageVariants(image);
  const largest = variants[variants.length - 1];
  return resolve({
    kind: "image",
    assetRef: image.assetRef,
    variant: largest?.variant ?? "w480",
    format: "jpg",
  });
}

export interface PictureProps {
  image: Image;
  ctx: PageContext;
  sizes: SizesName;
  className?: string;
  lazy?: boolean;
  /** Decorative copies (a tile beside its own label) pass an empty alt. */
  decorative?: boolean;
}

/** C8 responsive image: WebP and JPEG srcsets of the existing variants, with size hints. */
export function Picture({ image, ctx, sizes, className, lazy = true, decorative }: PictureProps) {
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
        sizes={attr.sizes[sizes]}
      />
      <img
        className={className}
        src={fallback}
        srcSet={srcset(image, "jpg", ctx.resolveAsset)}
        sizes={attr.sizes[sizes]}
        alt={decorative ? "" : image.altText}
        width={image.width}
        height={image.height}
        loading={lazy ? "lazy" : "eager"}
        decoding="async"
      />
    </picture>
  );
}

/** One badge, exactly as C2 derived it (FR4.10): the label, plus the SPDX id for openSource. */
export function BadgeLabel({ badge }: { badge: Badge }) {
  const live = LIVE_BADGES.has(badge.kind);
  return (
    <span className={live ? classes.badgeLive : classes.badge}>
      {vocab.badges[badge.kind]}
      {badge.kind === "openSource" && badge.spdx ? (
        <>
          {" "}
          <span className={classes.badgeSeparator} aria-hidden="true">
            {text.dot}
          </span>{" "}
          {badge.spdx}
        </>
      ) : null}
    </span>
  );
}

export function Badges({ badges }: { badges: Badge[] }) {
  if (badges.length === 0) return null;
  return (
    <div className={classes.cardFoot}>
      {badges.map((badge) => (
        <BadgeLabel key={`${badge.kind}:${badge.spdx ?? ""}`} badge={badge} />
      ))}
    </div>
  );
}

/** Highlights line: the primary category, then the access badges (no free text exists in C2). */
export function Highlights({ exhibit }: { exhibit: Exhibit }) {
  const items = [
    ...(exhibit.primaryCategory ? [exhibit.primaryCategory.name] : []),
    ...exhibit.badges.filter((b) => ACCESS_BADGES.has(b.kind)).map((b) => vocab.badges[b.kind]),
  ];
  if (items.length === 0) return null;
  return (
    <p className={classes.heroMeta}>
      {items.map((item, position) => (
        <ItemWithSeparator key={`${position}:${item}`} item={item} first={position === 0} />
      ))}
    </p>
  );
}

function ItemWithSeparator({ item, first }: { item: string; first: boolean }) {
  return (
    <>
      {first ? null : (
        <>
          {" "}
          <span aria-hidden="true">{text.dot}</span>{" "}
        </>
      )}
      {item}
    </>
  );
}

/** Exhibit card (ExhibitCard): category eyebrow, title link, summary, derived badges. */
export function Card({ exhibit, ctx }: { exhibit: Exhibit; ctx: PageContext }) {
  const category = exhibit.primaryCategory;
  return (
    <li className={classes.card}>
      <a className={classes.cardImage} href={exhibitPath(exhibit)} tabIndex={-1} aria-hidden="true">
        <Picture image={exhibit.leadImage} ctx={ctx} sizes="card" />
      </a>
      <div className={classes.cardBody}>
        {category ? <p className={classes.cardCategory}>{category.name}</p> : null}
        <h3>
          {category ? <Icon name={CATEGORY_ICONS[category.slug]} /> : null}
          <a href={exhibitPath(exhibit)}>{exhibit.title}</a>
        </h3>
        {exhibit.summary ? <p>{exhibit.summary}</p> : null}
        <Badges badges={exhibit.badges} />
      </div>
    </li>
  );
}

export function Cards({
  exhibits,
  ctx,
  columns,
}: {
  exhibits: Exhibit[];
  ctx: PageContext;
  columns: 2 | 3;
}) {
  return (
    <ul className={columns === 2 ? classes.cards2 : classes.cards3}>
      {exhibits.map((exhibit) => (
        <Card key={exhibit.slug} exhibit={exhibit} ctx={ctx} />
      ))}
    </ul>
  );
}
