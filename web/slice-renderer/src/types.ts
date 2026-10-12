// C2 PublicSiteSnapshot 1.0 and C11 renderer interface 1.0 types (contract-summary).

export type Slug = string;
export type AssetRef = string;
export type CategorySlug = "games" | "astronomy" | "woodworking" | "software";

export interface Category {
  slug: CategorySlug;
  name: string;
  position: number;
}

export interface CategoryWithCount extends Category {
  count: number;
}

export interface Image {
  assetRef: AssetRef;
  altText: string;
  caption?: string;
  width: number;
  height: number;
}

export interface Attachment {
  assetRef: AssetRef;
  label: string;
  fileType: "PDF" | "SKP" | "FCStd" | "DXF" | "STL" | "ZIP" | "VSDX";
  byteSize: number;
}

export interface Link {
  kind: "demo" | "documentation" | "other";
  label: string;
  url: string;
}

export interface Badge {
  kind:
    | "inBrowser"
    | "signInRequired"
    | "byInvitation"
    | "bestOnDesktop"
    | "openSource"
    | "sourceAvailable"
    | "sourcePrivate";
  spdx?: string;
}

export interface PublicRepository {
  name: string;
  url: string;
  licence?: string;
}

export interface Sections {
  inspiration?: string;
  designChallenges?: string;
  architecturalDecisions?: string;
  implementation?: string;
  outcomes?: string;
  lessonsLearned?: string;
}

export interface Exhibit {
  slug: Slug;
  title: string;
  summary: string;
  sections: Sections;
  leadImage: Image;
  images: Image[];
  attachments: Attachment[];
  links: Link[];
  liveUrl?: string;
  badges: Badge[];
  publicRepositories: PublicRepository[];
  primaryCategory?: Category;
  featured: boolean;
  publishedAt: string;
}

export interface PublicSiteSnapshot {
  schemaVersion: "1.0";
  generation: number;
  site: {
    ownerName: string;
    githubProfileUrl: string;
    contactEmail?: string | null;
  };
  exhibits: Exhibit[];
  featuredOrder: Slug[];
  categories: CategoryWithCount[];
}

export type Variant = "w480" | "w960" | "w1600";
export type ImageFormat = "webp" | "jpg";

export type ImageRef = { kind: "image"; assetRef: string; variant: Variant; format: ImageFormat };
export type DownloadRef = { kind: "download"; assetRef: string; downloadName: string };

/** Pure, synchronous lookup. Publication: C9 public paths. Preview: C4 image addresses. */
export type AssetResolver = (ref: ImageRef | DownloadRef) => string;

export interface RenderOptions {
  mode: "public" | "preview";
  resolveAsset: AssetResolver;
  previewSlug?: string;
}

export interface RenderedPage {
  path: string;
  status: 200 | 404;
  html: string;
}

export interface RenderOutput {
  contractVersion: "1.0";
  pages: RenderedPage[];
  requiredImages: { assetRef: string; variant: Variant; format: ImageFormat }[];
  requiredDownloads: { assetRef: string; downloadName: string }[];
  staticAssets: string[];
}

/** Thrown before any output when the snapshot or options are invalid. */
export class RenderInputError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RenderInputError";
  }
}
