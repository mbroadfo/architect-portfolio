import { describe, expect, it } from "vitest";
import {
  PLACEHOLDER_HEADING,
  PLACEHOLDER_MESSAGE,
  placeholderMessage,
  renderPlaceholder,
} from "./placeholder";

describe("public site placeholder (U0 S0)", () => {
  it("returns the installation message", () => {
    expect(placeholderMessage()).toBe(PLACEHOLDER_MESSAGE);
  });

  it("renders a heading and the message into the root element", () => {
    const root = document.createElement("main");
    renderPlaceholder(root);
    expect(root.querySelector("h1")?.textContent).toBe(PLACEHOLDER_HEADING);
    expect(root.querySelector("p")?.textContent).toBe(PLACEHOLDER_MESSAGE);
  });

  it("replaces existing content instead of appending to it", () => {
    const root = document.createElement("main");
    root.append(document.createElement("section"));
    renderPlaceholder(root);
    expect(root.children).toHaveLength(2);
    expect(root.querySelector("section")).toBeNull();
  });

  it("sets text, never markup (BR4.2)", () => {
    const root = document.createElement("main");
    renderPlaceholder(root);
    expect(root.querySelector("script")).toBeNull();
    expect(root.innerHTML).not.toContain("<script");
  });

  it("throws a clear error when the root element is missing", () => {
    expect(() => renderPlaceholder(null)).toThrow("#app element is missing");
  });
});
