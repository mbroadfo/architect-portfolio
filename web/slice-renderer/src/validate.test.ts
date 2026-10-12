// C2 semantic rule tests (S1 to S7) and C8/C9 helpers (Step 16).
import { describe, expect, it } from "vitest";
import { ASSET, exhibit, snapshot } from "./test-fixtures";
import { RenderInputError } from "./types";
import { validateSnapshot } from "./validate";
import { downloadName, imageVariants } from "./variants";

const second = exhibit({ slug: "second-project", leadImage: { ...exhibit().leadImage } });

describe("validateSnapshot", () => {
  it("accepts a valid snapshot", () => {
    expect(validateSnapshot(snapshot()).exhibits).toHaveLength(1);
  });

  it.each([
    ["S1 unknown featured slug", snapshot({ featuredOrder: ["placeholder-project"] })],
    [
      "S1 duplicate featured slug",
      snapshot({
        exhibits: [exhibit({ featured: true })],
        featuredOrder: ["placeholder-project", "placeholder-project"],
      }),
    ],
    [
      "S2 categories mismatch",
      snapshot({ categories: [{ slug: "games", name: "Games", position: 0, count: 1 }] }),
    ],
    ["S3 duplicate slugs", snapshot({ exhibits: [exhibit(), exhibit()] })],
    [
      "S4 spdx without openSource",
      snapshot({ exhibits: [exhibit({ badges: [{ kind: "sourcePrivate", spdx: "MIT" }] })] }),
    ],
    [
      "S5 access badge without liveUrl",
      snapshot({ exhibits: [exhibit({ badges: [{ kind: "inBrowser" }] })] }),
    ],
    [
      "S5 two access badges",
      snapshot({
        exhibits: [
          exhibit({
            liveUrl: "https://demo.test.example",
            badges: [{ kind: "inBrowser" }, { kind: "byInvitation" }],
          }),
        ],
      }),
    ],
    [
      "S6 openSource without a licensed repository",
      snapshot({ exhibits: [exhibit({ badges: [{ kind: "openSource", spdx: "MIT" }] })] }),
    ],
    [
      "S6 sourceAvailable without a repository",
      snapshot({ exhibits: [exhibit({ badges: [{ kind: "sourceAvailable" }] })] }),
    ],
    [
      "S6 sourcePrivate with a repository",
      snapshot({
        exhibits: [
          exhibit({
            badges: [{ kind: "sourcePrivate" }],
            publicRepositories: [{ name: "r", url: "https://github.com/example/r" }],
          }),
        ],
      }),
    ],
    [
      "S7 repeated image asset",
      snapshot({
        exhibits: [exhibit({ images: [{ assetRef: ASSET, altText: "x", width: 1, height: 1 }] })],
      }),
    ],
  ])("refuses %s", (_name, input) => {
    expect(() => validateSnapshot(input)).toThrow(RenderInputError);
  });

  it("accepts two exhibits sharing one fixture image across exhibits", () => {
    expect(validateSnapshot(snapshot({ exhibits: [exhibit(), second] })).exhibits).toHaveLength(2);
  });

  it("reports the failing schema paths", () => {
    expect(() => validateSnapshot({ schemaVersion: "2.0" })).toThrow(/schemaVersion/);
  });
});

describe("C8 variants and C9 download names", () => {
  it("never upscales", () => {
    expect(imageVariants({ width: 200 })).toEqual([{ variant: "w480", width: 200 }]);
    expect(imageVariants({ width: 960 })).toEqual([
      { variant: "w480", width: 480 },
      { variant: "w960", width: 960 },
    ]);
  });

  it("slugs labels into download names", () => {
    expect(downloadName({ label: "  Plans & Drawings! ", fileType: "FCStd" })).toBe(
      "plans-drawings.fcstd",
    );
    expect(downloadName({ label: "!!!", fileType: "ZIP" })).toBe("download.zip");
    expect(downloadName({ label: `${"a".repeat(59)} b`, fileType: "STL" })).toBe(
      `${"a".repeat(59)}.stl`,
    );
  });
});
