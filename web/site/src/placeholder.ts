/**
 * Placeholder content for the public site (U0 S0). The real site arrives with U7 and U8.
 * Text is set through textContent, never as markup (BR4.2).
 */
export const PLACEHOLDER_HEADING = "Architect Portfolio";
export const PLACEHOLDER_MESSAGE = "New work is being installed.";

export function placeholderMessage(): string {
  return PLACEHOLDER_MESSAGE;
}

export function renderPlaceholder(root: HTMLElement | null): HTMLElement {
  if (root === null) {
    throw new Error("renderPlaceholder: the #app element is missing");
  }
  const heading = document.createElement("h1");
  heading.textContent = PLACEHOLDER_HEADING;
  const message = document.createElement("p");
  message.textContent = placeholderMessage();
  root.replaceChildren(heading, message);
  return root;
}
