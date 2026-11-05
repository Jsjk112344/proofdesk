// UI interaction checks for the sales journey against an explicitly mocked API.
// No Docker execution, network or inference happens here; records come from the
// deterministic journey run with the recording runner. Run inside the disposable,
// network-disabled browser container described in infra/README.md.
import { chromium } from "/opt/ui-check/node_modules/playwright/index.mjs";
import { createServer } from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";

const workspace = JSON.parse(await readFile("/work/workspace.json", "utf8"));
const workspacePublic = JSON.parse(await readFile("/work/workspace-public.json", "utf8"));
const records = JSON.parse(await readFile("/work/records.json", "utf8"));
let publicMode = false;
const STAGES = ["researching", "deciding", "demonstrating", "drafting", "ready"];
const prospects = [];
const ticks = new Map();

function finished(run) {
  const final = run.template;
  return { ...final, id: run.id, status: final.status, created_at: run.created_at };
}
function progress(run) {
  if (run.template.status === "failed") {
    const n = (ticks.get(run.id) || 0) + 1;
    ticks.set(run.id, n);
    if (n < 2)
      return {
        ...run.template,
        id: run.id,
        status: "researching",
        failure_reason: null,
        events: run.template.events.slice(0, 2),
        brief: null,
        demo: null,
        draft: null,
      };
    return finished(run);
  }
  const n = (ticks.get(run.id) || 0) + 1;
  ticks.set(run.id, n);
  const stage = STAGES[Math.min(n - 1, STAGES.length - 1)];
  if (stage === "ready") return finished(run);
  const idx = STAGES.indexOf(stage);
  const reached = run.template.events.filter((e) =>
    ["queued", ...STAGES.slice(0, idx + 1)].includes(e.stage),
  );
  return {
    ...run.template,
    id: run.id,
    status: stage,
    events: reached,
    brief: idx >= 1 ? run.template.brief : null,
    demo: idx >= 2 ? run.template.demo : null,
    draft: null,
    execution: idx >= 3 ? run.template.execution : null,
    review: { state: "pending", draft_sha256: null, reviewed_at: null },
  };
}
async function body(request) {
  let raw = "";
  for await (const chunk of request) raw += chunk;
  return JSON.parse(raw);
}
const server = createServer(async (request, response) => {
  try {
    const path = request.url.split("?")[0];
    response.setHeader("Cache-Control", "no-store");
    if (path.startsWith("/api/")) {
      response.setHeader("Content-Type", "application/json");
      if (path === "/api/workspace")
        return response.end(JSON.stringify(publicMode ? workspacePublic : workspace));
      if (path === "/api/prospects" && request.method === "POST") {
        const data = await body(request);
        if (data.prospect_url && data.prospect_url.includes("169.254.169.254")) {
          response.statusCode = 409;
          return response.end(JSON.stringify({ detail: "ip_literal_rejected" }));
        }
        if (publicMode && data.prospect_url) {
          response.statusCode = 409;
          return response.end(JSON.stringify({ detail: "public_demo_samples_only" }));
        }
        const template = data.sample
          ? records[data.sample]
          : records.failed;
        const run = {
          id: String(prospects.length + 1).padStart(32, "0"),
          created_at: new Date().toISOString(),
          template,
        };
        prospects.push(run);
        response.statusCode = 202;
        return response.end(
          JSON.stringify({ ...template, id: run.id, status: "queued", brief: null, demo: null, draft: null, execution: null, events: template.events.slice(0, 1), failure_reason: null }),
        );
      }
      if (path === "/api/prospects")
        return response.end(JSON.stringify(prospects.map((r) => (ticks.get(r.id) >= 6 || (r.template.status === "failed" && ticks.get(r.id) >= 2) ? finished(r) : progress(r)))));
      const match = path.match(/^\/api\/prospects\/([0-9]{32})(\/(draft|review))?$/);
      const run = match && prospects.find((r) => r.id === match[1]);
      if (!run) {
        response.statusCode = 404;
        return response.end(JSON.stringify({ detail: "prospect_not_found" }));
      }
      if (match[3] === "draft") {
        const data = await body(request);
        const current = finished(run);
        if (data.base_sha256 !== current.draft.sha256) {
          response.statusCode = 409;
          return response.end(JSON.stringify({ detail: "draft_version_conflict" }));
        }
        run.template = {
          ...current,
          drafts_history: [current.draft, ...current.drafts_history],
          draft: { ...current.draft, version: current.draft.version + 1, sha256: "e".repeat(64), subject: data.subject, body: data.body, provenance: "human_edited", citations: current.draft.citations },
          review: { state: "pending", draft_sha256: null, reviewed_at: null },
        };
        return response.end(JSON.stringify(finished(run)));
      }
      if (match[3] === "review") {
        const data = await body(request);
        const current = finished(run);
        if (data.draft_sha256 !== current.draft.sha256) {
          response.statusCode = 409;
          return response.end(JSON.stringify({ detail: "draft_version_conflict" }));
        }
        run.template = { ...current, review: { state: "reviewed", draft_sha256: data.draft_sha256, reviewed_at: new Date().toISOString() } };
        return response.end(JSON.stringify(finished(run)));
      }
      return response.end(JSON.stringify(progress(run)));
    }
    if (path === "/__public-mode") {
      publicMode = true;
      return response.end("public mode on");
    }
    if (path !== "/" && !/^\/assets\/[A-Za-z0-9._-]+$/.test(path)) {
      response.statusCode = 404;
      return response.end();
    }
    const file = "/work/dist" + (path === "/" ? "/index.html" : path);
    response.setHeader(
      "Content-Type",
      file.endsWith(".js") ? "text/javascript" : file.endsWith(".css") ? "text/css" : "text/html",
    );
    response.end(await readFile(file));
  } catch (error) {
    response.statusCode = 500;
    response.end(String(error));
  }
});
await new Promise((resolve) => server.listen(8080, "127.0.0.1", resolve));
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const checks = [];
try {
  await page.goto("http://127.0.0.1:8080");
  // Landing asks for an offering and a prospect, not a document.
  await page.getByLabel("Your offering").waitFor();
  await page.getByLabel("Prospect website").waitFor();
  assert.equal(await page.getByText("Choose a document").count(), 0);
  await page.getByRole("heading", { name: "What SalesDesk can demonstrate" }).waitFor();
  await page.screenshot({ path: "/work/landing.png", fullPage: true });
  checks.push("landing asks for offering and prospect website");
  // A blocked address is refused with a readable message.
  await page.getByLabel("Prospect website").fill("https://169.254.169.254/latest");
  await page.getByRole("button", { name: "Research this prospect" }).click();
  await page.getByRole("alert").filter({ hasText: "Enter a hostname, not an IP address." }).waitFor();
  checks.push("blocked address shows policy message");
  // Sample scenario journey with saved progress.
  await page.getByRole("button", { name: "Use the sample scenario" }).click();
  await page.getByText("Ready for review").waitFor();
  await page.getByText("Reviewed · v1").waitFor({ state: "detached", timeout: 1000 }).catch(() => {});
  await page.getByRole("heading", { name: /demonstrably does/ }).waitFor();
  await page.getByText("Hypothesis", { exact: true }).waitFor();
  await page.getByText("Unknowns and missing evidence").waitFor();
  assert.ok((await page.getByText(/captured 20/).count()) > 0, "source capture dates shown");
  await page.screenshot({ path: "/work/research.png", fullPage: true });
  checks.push("research brief with verbatim facts, sources, hypothesis and unknowns");
  await page.getByRole("tab", { name: "Demonstration" }).click();
  await page.getByText("Run the demonstration").waitFor();
  await page.getByText("Verified", { exact: true }).waitFor();
  await page.getByText("Synthetic input", { exact: true }).waitFor();
  await page.getByText("UI-MOCK-EXECUTION").waitFor();
  await page.screenshot({ path: "/work/demonstration.png", fullPage: true });
  checks.push("demonstration decision, synthetic input label, result and evidence");
  await page.getByRole("tab", { name: "Outreach" }).click();
  await page.getByText("Not reviewed").waitFor();
  const subject = page.getByLabel("Subject");
  assert.ok((await subject.inputValue()).includes("Harbor"));
  await page.getByRole("button", { name: "Mark this version reviewed" }).click();
  await page.getByText(/Reviewed · v1/).waitFor();
  await subject.fill("Edited subject line");
  await page.getByRole("button", { name: "Save edits as new version" }).click();
  await page.getByText("Draft v2").waitFor();
  await page.getByText("Not reviewed").waitFor();
  await page.screenshot({ path: "/work/outreach.png", fullPage: true });
  checks.push("review binds to a version and editing invalidates it");
  // Reload restores the same prospect and the edited draft.
  await page.reload();
  await page.getByText("Draft v2").waitFor({ timeout: 10000 }).catch(async () => {
    await page.getByRole("tab", { name: "Outreach" }).click();
    await page.getByText("Draft v2").waitFor();
  });
  checks.push("reload restores the prospect and draft version");
  // Skipped demonstration and failure state.
  await page.getByRole("button", { name: "New prospect" }).click();
  await page.getByRole("button", { name: "Other synthetic scenarios" }).click();
  await page.getByRole("button", { name: "Synthetic bakery" }).click();
  await page.getByText("Ready for review").waitFor();
  await page.getByRole("tab", { name: "Demonstration" }).click();
  await page.getByText("Skipped: not relevant").waitFor();
  checks.push("irrelevant prospect skips the demonstration with a reason");
  await page.getByRole("button", { name: "New prospect" }).click();
  await page.getByLabel("Prospect website").fill("https://prospect.example/");
  await page.getByRole("button", { name: "Research this prospect" }).click();
  await page.getByText("This prospect stopped.").waitFor();
  await page.getByRole("tab", { name: "Technical details" }).click();
  await page.getByText("excerpt_not_in_source").waitFor();
  await page.screenshot({ path: "/work/failure.png", fullPage: true });
  checks.push("model validation failure shows a sanitized diagnostic and no draft");
  // Public demo mode: labelled, real websites disabled, sample journey still works.
  await page.goto("http://127.0.0.1:8080/__public-mode");
  await page.goto("http://127.0.0.1:8080");
  await page.getByText("Public demo · synthetic scenarios · nothing is sent").waitFor();
  await page.getByRole("button", { name: "New prospect" }).click();
  await page.getByRole("note").filter({ hasText: "Public demo" }).waitFor();
  assert.equal(await page.getByLabel("Prospect website").isDisabled(), true);
  assert.equal(await page.getByRole("button", { name: "Research this prospect" }).isDisabled(), true);
  await page.getByRole("button", { name: "Use the sample scenario" }).click();
  await page.getByText("Ready for review").waitFor();
  await page.screenshot({ path: "/work/public.png", fullPage: true });
  checks.push("public demo mode is labelled, disables real websites and runs the sample");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("tab", { name: "Research" }).click();
  await page.screenshot({ path: "/work/mobile.png", fullPage: true });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  assert.equal(overflow, false, "Mobile page overflows horizontally");
  checks.push("mobile layout without horizontal overflow");
  assert.deepEqual(errors, []);
  checks.push("no page errors");
  await writeFile(
    "/work/browser-check.json",
    JSON.stringify(
      {
        kind: "UI interaction with mocked API; not execution, retrieval or live inference evidence",
        passed: true,
        checks,
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
  server.close();
}
