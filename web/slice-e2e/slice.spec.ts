// W6: the walking slice end to end against the local stack (AC0.1, AC0.3, AC0.5, AC0.6,
// AC0.8; NFR6.1, NFR6.2; C9 headers). Placeholder content only.
import { expect, test, type APIRequestContext } from "@playwright/test";

const API = process.env.SLICE_API_URL ?? "http://127.0.0.1:8000";
const SITE = process.env.SLICE_SITE_URL ?? "http://127.0.0.1:8080";
const IDP = process.env.SLICE_IDP_URL ?? "http://127.0.0.1:9000";

const TITLE = "Walking slice <demo> & friends";
const ESCAPED_TITLE = "Walking slice &lt;demo&gt; &amp; friends";
const SLUG = "walking-slice-demo-friends";
const SUMMARY = "Placeholder summary for the walking slice.";

test.describe.configure({ mode: "serial" });

async function token(request: APIRequestContext, subject = "local-owner"): Promise<string> {
  const response = await request.get(`${IDP}/token`, { params: { sub: subject } });
  expect(response.ok()).toBeTruthy();
  return ((await response.json()) as { access_token: string }).access_token;
}

async function timed<T>(work: () => Promise<T>): Promise<[T, number]> {
  const started = Date.now();
  const result = await work();
  return [result, Date.now() - started];
}

test("W1 to W4: create, save, preview and publish a static page in the Studio", async ({
  page,
  request,
}) => {
  const empty = await request.get(`${SITE}/`);
  expect(empty.status()).toBe(200);
  expect(await empty.text()).toContain("New work is being installed.");

  // W1: sign in through the local fake issuer and create a project.
  await page.goto("/");
  await page.getByTestId("signin-button").click();
  await page.getByTestId("new-project-title-input").fill(TITLE);
  await page.getByTestId("new-project-create-button").click();
  await expect(page.getByTestId("editor-status")).toHaveText("Draft");
  await expect(page.getByTestId("editor-revision")).toHaveText("Revision 1");
  await expect(page.getByTestId("editor-slug")).toHaveText(`/work/${SLUG}`);

  // W2: save.
  await page.getByTestId("editor-summary-input").fill(SUMMARY);
  await page.getByTestId("editor-save-button").click();
  await expect(page.getByTestId("editor-revision")).toHaveText("Revision 2");

  // W3 (AC0.5): marked preview in a sandboxed frame; nothing is written.
  await page.getByTestId("editor-preview-button").click();
  const frame = page.getByTestId("preview-frame");
  await expect(frame).toHaveAttribute("sandbox", "");
  const preview = page.frameLocator('[data-testid="preview-frame"]');
  await expect(preview.getByText("Preview — not public")).toBeVisible();
  await expect(preview.getByRole("heading", { level: 1 })).toHaveText(TITLE);
  expect((await request.get(`${SITE}/work/${SLUG}`)).status()).toBe(404);

  // W4 (AC0.6): confirm Publish of the reviewed revision.
  await page.getByTestId("publish-button").click();
  await expect(page.getByTestId("publish-confirmation-text")).toHaveText(
    "Publish revision 2 to the public site?",
  );
  await page.getByTestId("publish-confirm-button").click();
  await expect(page.getByTestId("editor-status")).toHaveText("Published");

  const published = await request.get(`${SITE}/work/${SLUG}`);
  expect(published.status()).toBe(200);
  const html = await published.text();
  expect(html).toContain(ESCAPED_TITLE);
  expect(html).toContain(SUMMARY);
  expect(html).not.toContain("<demo>");
  expect(html).not.toContain("Preview — not public");
  expect(html).not.toMatch(/<script/i);

  await page.goto(`${SITE}/work/${SLUG}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(TITLE);
  await expect(page.getByRole("img")).toHaveAttribute("alt", /placeholder illustration/i);

  // AC0.8: a saved change reads "Changes since last publish"; the public page is unchanged.
  await page.goto("/");
  await page.getByTestId("signin-button").click();
  await page.getByRole("button", { name: TITLE }).click();
  await page.getByTestId("editor-summary-input").fill("An unpublished change.");
  await page.getByTestId("editor-save-button").click();
  await expect(page.getByTestId("editor-status")).toHaveText("Changes since last publish");
  expect(await (await request.get(`${SITE}/work/${SLUG}`)).text()).toBe(html);

  // AC0.3: a save based on an older revision is refused with the reload message.
  const owner = await token(request);
  const list = await request.get(`${API}/slice/projects`, {
    headers: { Authorization: `Bearer ${owner}` },
  });
  const project = ((await list.json()) as { projects: { projectId: string; revision: number }[] })
    .projects[0];
  expect(project).toBeDefined();
  const bump = await request.patch(`${API}/slice/projects/${project?.projectId}`, {
    headers: { Authorization: `Bearer ${owner}`, "If-Match": `"${project?.revision}"` },
    data: { summary: "Changed elsewhere." },
  });
  expect(bump.status()).toBe(200);
  await page.getByTestId("editor-summary-input").fill("A lost update.");
  await page.getByTestId("editor-save-button").click();
  await expect(page.getByTestId("notice-text")).toHaveText("Reload: this project changed.");
});

test("AC0.1: the API refuses callers without the owner's token", async ({ request }) => {
  expect((await request.get(`${API}/health`)).status()).toBe(200);
  expect((await request.get(`${API}/slice/projects`)).status()).toBe(401);
  const other = await token(request, "local-other");
  const response = await request.get(`${API}/slice/projects`, {
    headers: { Authorization: `Bearer ${other}` },
  });
  expect(response.status()).toBe(403);
  expect(((await response.json()) as { code: string }).code).toBe("NOT_OWNER");
});

test("NFR6.1 and NFR6.2: API calls under 1 s, Publish under 10 s", async ({ request }) => {
  const headers = { Authorization: `Bearer ${await token(request)}` };
  const [created, createMs] = await timed(() =>
    request.post(`${API}/slice/projects`, { headers, data: { title: "Timing check" } }),
  );
  expect(created.status()).toBe(201);
  const { projectId } = (await created.json()) as { projectId: string };
  const [saved, saveMs] = await timed(() =>
    request.patch(`${API}/slice/projects/${projectId}`, {
      headers: { ...headers, "If-Match": '"1"' },
      data: { summary: "Placeholder timing summary." },
    }),
  );
  expect(saved.status()).toBe(200);
  const [previewed, previewMs] = await timed(() =>
    request.get(`${API}/slice/projects/${projectId}/preview`, { headers }),
  );
  expect(previewed.status()).toBe(200);
  const [publishedResponse, publishMs] = await timed(() =>
    request.post(`${API}/slice/projects/${projectId}/publish`, { headers, data: { revision: 2 } }),
  );
  expect(publishedResponse.status()).toBe(200);
  console.log(
    `timings: create ${createMs} ms, save ${saveMs} ms, preview ${previewMs} ms, publish ${publishMs} ms`,
  );
  expect(createMs).toBeLessThan(1000);
  expect(saveMs).toBeLessThan(1000);
  expect(previewMs).toBeLessThan(1000);
  expect(publishMs).toBeLessThan(10_000);
});

test("C9 headers on a 200 and a 404 (NFR15.1)", async ({ request }) => {
  for (const [path, status] of [
    ["/", 200],
    ["/work/no-such-exhibit", 404],
  ] as const) {
    const response = await request.get(`${SITE}${path}`);
    expect(response.status()).toBe(status);
    const headers = response.headers();
    expect(headers["content-security-policy"]).toBe("default-src 'self'; frame-ancestors 'none'");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  }
});
