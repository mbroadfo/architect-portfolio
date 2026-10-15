import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, badgeLabel, describe as describeError, thumbnail } from "./api";

function respond(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("sends the Studio header on changes but not on reads", async () => {
    const fetchMock = respond(200, { projects: [] });
    vi.stubGlobal("fetch", fetchMock);
    await api.list();
    expect((fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1]).toMatchObject({
      method: "GET",
      headers: {},
    });
    const create = respond(201, { id: "x" });
    vi.stubGlobal("fetch", create);
    await api.create("X");
    const init = (create.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect(init.headers).toMatchObject({
      "X-Studio-Request": "1",
      "Content-Type": "application/json",
    });
    expect(init.body).toBe(JSON.stringify({ title: "X" }));
  });

  it("uploads multipart with the revision", async () => {
    const fetchMock = respond(201, { id: "stars" });
    vi.stubGlobal("fetch", fetchMock);
    await api.upload("stars", 4, new File(["x"], "a.jpg"));
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/projects/stars/images");
    expect((init.body as FormData).get("revision")).toBe("4");
    expect(init.headers).toEqual({ "X-Studio-Request": "1" });
  });

  it("maps error responses to ApiError", async () => {
    vi.stubGlobal("fetch", respond(409, { code: "STALE_REVISION", message: "saved elsewhere" }));
    await expect(api.get("stars")).rejects.toMatchObject({ status: 409, code: "STALE_REVISION" });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("oops", { status: 500, statusText: "Boom" })),
    );
    await expect(api.upload("s", 1, new File([], "a"))).rejects.toMatchObject({ code: "INTERNAL" });
  });

  it("covers every endpoint", async () => {
    const fetchMock = respond(200, { entries: [], projects: [] });
    vi.stubGlobal("fetch", fetchMock);
    await api.save("stars", 2, {} as never, []);
    await api.review("stars");
    await api.publish("stars", 2, "r");
    await api.takeDown("stars", "STARS");
    await api.featured();
    await api.updateFeatured(["a"]);
    await api.activity();
    await api.site();
    await api.build();
    await api.packagePages();
    const paths = fetchMock.mock.calls.map((call) => (call as unknown as [string])[0]);
    expect(paths).toContain("/api/projects/stars/take-down");
    expect(paths).toContain("/api/site/build");
    expect(paths).toContain("/api/site/package");
  });

  it("describes errors and labels badges", () => {
    expect(describeError(new ApiError(409, "STALE_REVISION", "saved elsewhere"))).toBe(
      "saved elsewhere",
    );
    expect(describeError(new ApiError(500, "X", ""))).toContain("500");
    expect(describeError(new Error("plain"))).toBe("plain");
    expect(describeError("odd")).toBe("Something went wrong.");
    expect(badgeLabel({ kind: "openSource", spdx: "MIT" })).toBe("Open source · MIT");
    expect(badgeLabel({ kind: "sourcePrivate" })).toBe("Source private");
    expect(badgeLabel({ kind: "future" })).toBe("future");
    expect(thumbnail("ast_x")).toBe("/media/ast_x/w480.jpg");
  });
});
