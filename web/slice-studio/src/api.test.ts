// API client edge cases (Step 21).
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createClient, fetchToken } from "./api";
import { previewResolver } from "./preview";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API client", () => {
  it("maps an error body without JSON to INTERNAL with the status text", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response("<html>bad gateway</html>", { status: 502, statusText: "Bad Gateway" }),
      ),
    );
    const error = await createClient("t")
      .list()
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("INTERNAL");
    expect((error as ApiError).message).toBe("Bad Gateway");
  });

  it("refuses a sign-in response without a token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({}), { status: 200 })),
    );
    await expect(fetchToken()).rejects.toThrow("Sign-in returned no token");
  });

  it("encodes project ids in paths", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await createClient("t").get("a/b");
    expect(String(fetchMock.mock.calls[0]?.[0 as never])).toContain("/slice/projects/a%2Fb");
  });

  it("resolves preview images to the candidate's data addresses", () => {
    const resolve = previewResolver({
      revision: 1,
      snapshot: {} as never,
      imageAddresses: { "ast_x/w480.jpg": "data:image/jpeg;base64,AA==" },
    });
    expect(resolve({ kind: "image", assetRef: "ast_x", variant: "w480", format: "jpg" })).toBe(
      "data:image/jpeg;base64,AA==",
    );
    expect(resolve({ kind: "image", assetRef: "ast_x", variant: "w480", format: "webp" })).toBe("");
    expect(resolve({ kind: "download", assetRef: "ast_x", downloadName: "x.pdf" })).toBe("#");
  });
});
