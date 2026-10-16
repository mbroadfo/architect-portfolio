// Inline SVG icons from the prototype sprite, drawn with paths only: every attribute value is
// in the template vocabulary, and no `<use href="#...">` reference is needed.
import vocab from "./template-strings.json";
import type { CategorySlug } from "./types";

export type IconName = keyof typeof vocab.icons;

const { attributes: attr, classes } = vocab;

export const CATEGORY_ICONS: Record<CategorySlug, IconName> = {
  games: "gamepad",
  astronomy: "telescope",
  woodworking: "hammer",
  software: "code",
};

export function Icon({ name, large = false }: { name: IconName; large?: boolean }) {
  return (
    <svg
      className={large ? classes.iconLarge : classes.icon}
      viewBox={attr.viewBox}
      aria-hidden="true"
      focusable="false"
    >
      {vocab.icons[name].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}
