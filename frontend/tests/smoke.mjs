// UI interaction checks for the experiment workspace and the supporting prospect journey,
// against an explicitly mocked API. No Docker execution, network or inference happens here;
// experiment records come from an in-process journey on the labelled synthetic fixture and
// prospect records from the deterministic journey with the recording runner. Run inside the
// disposable, network-disabled browser container described in infra/README.md.
import { chromium } from "/opt/ui-check/node_modules/playwright/index.mjs";
import { createServer } from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";

const workspace = JSON.parse(await readFile("/work/workspace.json", "utf8"));
const workspacePublic = JSON.parse(await readFile("/work/workspace-public.json", "utf8"));
const records = JSON.parse(await readFile("/work/records.json", "utf8"));
const experiments = JSON.parse(await readFile("/work/experiments.json", "utf8"));
let publicMode = false;
const STAGES = ["researching", "deciding", "demonstrating", "drafting", "ready"];
const prospects = [];
const ticks = new Map();

// ---- experiment mock state (one plan at a time, driven by the recorded journey) ----
const recorded = experiments.detail;
const plans = [];
function planDetail(plan) {
  return {
    plan: { ...recorded.plan, id: plan.id, spec: { ...recorded.plan.spec, title: plan.title } },
    dataset: recorded.dataset,
    runs: plan.runs,
    proposals: plan.proposals,
    tasks: plan.tasks,
    jobs: plan.jobs,
    generation_mode: "deterministic",
    program_sha256: recorded.program_sha256,
  };
}
function overview() {
  return {
    ...experiments.overview,
    public_demo: publicMode,
    plans: plans.map((p) => ({
      id: p.id,
      version: 1,
      sha256: recorded.plan.sha256,
      dataset_id: recorded.plan.dataset_id,
      title: p.title,
      question: recorded.plan.spec.question,
      comparison: recorded.plan.spec.comparison,
      created_at: p.created_at,
      runs: p.runs.length,
      latest_run: p.runs[0]
        ? {
            id: p.runs[0].id,
            status: p.runs[0].status,
            failure_reason: null,
            finished_at: p.runs[0].finished_at,
            interpretation_status: "succeeded",
            interpretation_provenance: "deterministic",
          }
        : null,
      proposal_version: p.proposals[0]?.version || 0,
      tasks: p.tasks.map((t) => t.status),
      active_jobs: p.jobs.filter((j) => ["scheduled", "running"].includes(j.status)).length,
    })),
    tasks: plans.flatMap((p) => p.tasks),
    jobs: plans.flatMap((p) => p.jobs),
  };
}
function advance(plan) {
  for (const job of plan.jobs) {
    if (!["scheduled", "running"].includes(job.status)) continue;
    job.polls = (job.polls || 0) + 1;
    if (job.polls === 1) job.status = "running";
    if (job.polls >= 3) {
      job.status = "succeeded";
      if (job.kind === "analyze_plan") {
        job.outcome = experiments.analysis_job.outcome;
        plan.runs.unshift({ ...recorded.runs[recorded.runs.length - 1], id: job.id.replace(/^./, "a"), job_id: job.id });
        if (plan.proposals.length === 0)
          plan.proposals.unshift({ ...recorded.proposals[recorded.proposals.length - 1], version: 1, provenance: "deterministic" });
      } else {
        job.outcome = experiments.packet_job.outcome;
        const task = plan.tasks.find((t) => t.id === job.task_id);
        task.status = "ready_for_review";
        task.packet_artifact_id = experiments.packet.id;
        task.events = [...task.events, { stage: "running", at: new Date().toISOString() }, { stage: "ready_for_review", at: new Date().toISOString() }];
      }
    }
  }
}
function newJob(plan, kind, taskId) {
  const job = {
    ...experiments.analysis_job,
    id: `${plans.length}${kind.length}`.padEnd(32, "b").slice(0, 32),
    kind,
    task_id: taskId || null,
    status: "scheduled",
    attempts: 1,
    due_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    outcome: null,
    failure_reason: null,
    events: [{ stage: "scheduled", at: new Date().toISOString() }],
    polls: 0,
  };
  plan.jobs.unshift(job);
  return job;
}

function finished(run) {
  const final = run.template;
  return { ...final, id: run.id, status: final.status, created_at: run.created_at };
}
function progress(run) {
  if (run.template.status === "failed") {
    const n = (ticks.get(run.id) || 0) + 1;
    ticks.set(run.id, n);
    if (n < 2)
      return { ...run.template, id: run.id, status: "researching", failure_reason: null, events: run.template.events.slice(0, 2), brief: null, demo: null, draft: null };
    return finished(run);
  }
  const n = (ticks.get(run.id) || 0) + 1;
  ticks.set(run.id, n);
  const stage = STAGES[Math.min(n - 1, STAGES.length - 1)];
  if (stage === "ready") return finished(run);
  const idx = STAGES.indexOf(stage);
  const reached = run.template.events.filter((e) => ["queued", ...STAGES.slice(0, idx + 1)].includes(e.stage));
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
const json = (response, value, status = 200) => {
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(value));
};
const server = createServer(async (request, response) => {
  try {
    const path = request.url.split("?")[0];
    response.setHeader("Cache-Control", "no-store");
    if (path.startsWith("/api/experiments")) {
      if (path === "/api/experiments") return json(response, overview());
      if (path === "/api/experiments/datasets") return json(response, experiments.overview.datasets);
      if (path === "/api/experiments/plans" && request.method === "POST") {
        const data = await body(request);
        const plan = { id: String(plans.length + 1).padStart(32, "c"), title: data.title, created_at: new Date().toISOString(), runs: [], proposals: [], tasks: [], jobs: [] };
        plans.push(plan);
        return json(response, planDetail(plan).plan, 201);
      }
      let match = path.match(/^\/api\/experiments\/plans\/([a-f0-9]{32})(?:\/(runs|proposal|tasks))?$/);
      if (match) {
        const plan = plans.find((p) => p.id === match[1]);
        if (!plan) return json(response, { detail: "experiment_not_found" }, 404);
        if (!match[2]) {
          advance(plan);
          return json(response, planDetail(plan));
        }
        if (match[2] === "runs") return json(response, newJob(plan, "analyze_plan"), 202);
        if (match[2] === "proposal") {
          const data = await body(request);
          const previous = plan.proposals[0];
          if ((previous?.version || 0) !== data.base_version) return json(response, { detail: "proposal_version_conflict" }, 409);
          const next = { ...recorded.proposals[0], version: (previous?.version || 0) + 1, content: data.proposal, provenance: "human_edited", sha256: "d".repeat(64) };
          plan.proposals.unshift(next);
          for (const task of plan.tasks) if (["approved", "scheduled"].includes(task.status)) { task.status = "pending_review"; task.approval = null; }
          return json(response, next, 201);
        }
        if (match[2] === "tasks") {
          const data = await body(request);
          const task = { ...recorded.tasks[0], id: String(plan.tasks.length + 1).padStart(32, "e"), title: data.title, assignee_label: data.assignee_label, proposed_action: data.proposed_action, due_date: data.due_date, status: "pending_review", approval: null, job_id: null, packet_artifact_id: null, completion: null, proposal_version: plan.proposals[0].version, proposal_sha256: plan.proposals[0].sha256, proposal_id: plan.proposals[0].id, events: [{ stage: "pending_review", at: new Date().toISOString() }] };
          plan.tasks.unshift(task);
          return json(response, task, 201);
        }
      }
      match = path.match(/^\/api\/experiments\/tasks\/([a-f0-9]{32})\/(approve|schedule|cancel|complete)$/);
      if (match) {
        const plan = plans.find((p) => p.tasks.some((t) => t.id === match[1]));
        if (!plan) return json(response, { detail: "experiment_not_found" }, 404);
        const task = plan.tasks.find((t) => t.id === match[1]);
        const data = await body(request);
        if (match[2] === "approve") {
          if (data.proposal_sha256 !== plan.proposals[0].sha256) return json(response, { detail: "proposal_version_conflict" }, 409);
          task.status = "approved";
          task.approval = { ...recorded.tasks[0].approval, proposal_sha256: data.proposal_sha256, proposal_version: plan.proposals[0].version, approved_at: new Date().toISOString() };
        } else if (match[2] === "schedule") {
          const job = newJob(plan, "prepare_packet", task.id);
          task.status = "scheduled";
          task.job_id = job.id;
        } else if (match[2] === "cancel") {
          task.status = "cancelled";
        } else {
          task.status = "completed";
          task.completion = { completed_at: new Date().toISOString(), evidence_note: data.evidence_note };
        }
        task.events = [...task.events, { stage: task.status, at: new Date().toISOString() }];
        return json(response, task);
      }
      match = path.match(/^\/api\/experiments\/jobs\/([a-f0-9]{32})(\/cancel)?$/);
      if (match) {
        const plan = plans.find((p) => p.jobs.some((j) => j.id === match[1]));
        if (!plan) return json(response, { detail: "experiment_not_found" }, 404);
        const job = plan.jobs.find((j) => j.id === match[1]);
        if (match[2]) job.status = "cancelled";
        else advance(plan);
        return json(response, job);
      }
      match = path.match(/^\/api\/experiments\/artifacts\/([a-f0-9]{32})(\/packet\.md)?$/);
      if (match) {
        if (match[2]) {
          response.setHeader("Content-Type", "text/markdown");
          return response.end(experiments.packet.content.markdown);
        }
        return json(response, experiments.packet);
      }
      return json(response, { detail: "experiment_not_found" }, 404);
    }
    if (path.startsWith("/api/")) {
      response.setHeader("Content-Type", "application/json");
      if (path === "/api/workspace") return response.end(JSON.stringify(publicMode ? workspacePublic : workspace));
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
        const template = data.sample ? records[data.sample] : records.failed;
        const run = { id: String(prospects.length + 1).padStart(32, "0"), created_at: new Date().toISOString(), template };
        prospects.push(run);
        response.statusCode = 202;
        return response.end(JSON.stringify({ ...template, id: run.id, status: "queued", brief: null, demo: null, draft: null, execution: null, events: template.events.slice(0, 1), failure_reason: null }));
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
        run.template = { ...current, drafts_history: [current.draft, ...current.drafts_history], draft: { ...current.draft, version: current.draft.version + 1, sha256: "e".repeat(64), subject: data.subject, body: data.body, provenance: "human_edited", citations: current.draft.citations }, review: { state: "pending", draft_sha256: null, reviewed_at: null } };
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
    response.setHeader("Content-Type", file.endsWith(".js") ? "text/javascript" : file.endsWith(".css") ? "text/css" : "text/html");
    response.end(await readFile(file));
  } catch (error) {
    response.statusCode = 500;
    response.end(String(error));
  }
});
await new Promise((resolve) => server.listen(8080, "127.0.0.1", resolve));
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const checks = [];
try {
  await page.goto("http://127.0.0.1:8080/#/legacy");
  await page.getByRole("heading", { name: "Sell more: Your AI sales analyst" }).waitFor();
  await page.getByRole("button", { name: "Analyse a campaign" }).waitFor();
  await page.getByRole("link", { name: "Research a prospect" }).waitFor();
  await page.screenshot({ path: "/work/home.png", fullPage: true });
  checks.push("two entry doors and analyst dashboard");
  await page.getByRole("link", { name: "New analysis plan" }).click();
  await page.getByLabel("Plan title").fill("Campaign UI check");
  await page.screenshot({ path: "/work/plan.png", fullPage: true });
  await page.getByRole("button", { name: "Save plan" }).click();
  await page.getByRole("button", { name: "Run analysis now" }).click();
  await page.getByText("Purchase rate by original arm", { exact: true }).waitFor({ timeout: 15000 });
  assert.equal(await page.locator(".primary:visible").count(), 1);
  const order = await page.locator('section[aria-label="Analyst activity"], section[aria-label="Answer"], section[aria-label="Purchase rates"], section[aria-label="Next move"]').evaluateAll(nodes => nodes.map(n => n.getAttribute("aria-label")));
  assert.deepEqual(order, ["Analyst activity", "Answer", "Purchase rates", "Next move"]);
  assert.equal(await page.getByRole("heading", { name: "Exploratory breakdowns" }).isVisible(), false);
  assert.equal(await page.getByText("Retrospective re-analysis", { exact: true }).isVisible(), false);
  assert.equal(await page.locator("time:visible").count(), 0);
  assert.equal(await page.getByLabel("Notes").isVisible(), false);
  assert.equal(await page.getByRole("button", { name: /^Analyst activity/ }).getAttribute("aria-expanded"), "false");
  await page.getByRole("button", { name: /^Analyst activity/ }).click();
  assert.ok(await page.locator("time:visible").count() > 0);
  await page.getByRole("button", { name: /^Analyst activity/ }).click();
  await page.screenshot({ path: "/work/results.png", fullPage: true });
  const actionBox = await page.getByRole("button", { name: "Approve & schedule", exact: true }).boundingBox();
  assert.ok(actionBox.y >= 0 && actionBox.y + actionBox.height <= 900);
  checks.push("one primary action above fold, answer first, compact activity, collapsed analysis and read-only next move");
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Notes").fill("Edited by sales manager");
  assert.equal(await page.getByRole("button", { name: "Approve & schedule" }).isDisabled(), true);
  assert.equal(await page.getByLabel("Future audience size").isVisible(), false);
  await page.locator("summary").filter({ hasText: /^Advanced$/ }).click();
  await page.getByLabel("Future audience size").waitFor();
  await page.getByRole("button", { name: "Save next move", exact: true }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).waitFor();
  await page.getByRole("button", { name: "Approve & schedule" }).click();
  await page.locator(".answer-action").getByText("Ready for review", { exact: true }).waitFor({ timeout: 15000 });
  await page.getByRole("link", { name: "Download packet", exact: true }).waitFor();
  assert.equal(await page.locator(".primary:visible").count(), 1);
  const inputs = page.locator("details").filter({ has: page.locator("summary", { hasText: /^Inputs to add before launch/ }) }).first();
  assert.equal(await inputs.getAttribute("open"), null);
  await page.reload();
  await page.locator(".answer-action").getByText("Ready for review", { exact: true }).waitFor();
  await page.screenshot({ path: "/work/next-action.png", fullPage: true });
  checks.push("edit-only form; Advanced hidden; dirty edit blocks approval; save schedules; hero download survives reload");
  await page.locator("summary").filter({ hasText: /^See full analysis$/ }).click();
  await page.getByRole("heading", { name: "Secondary outcomes: visits and spend per assigned customer" }).waitFor();
  await page.locator("summary").filter({ hasText: /^See full analysis$/ }).click();
  await page.locator("summary").filter({ hasText: /^Verification$/ }).click();
  await page.getByRole("heading", { name: "Reconciliation", exact: true }).waitFor();
  checks.push("full analysis, metric references and verification remain accessible");
  await page.goto("http://127.0.0.1:8080/#/queue");
  await page.screenshot({ path: "/work/queue.png", fullPage: true });
  await page.goto("http://127.0.0.1:8080/#/prospects");
  await page.getByLabel("Your offering").waitFor();
  await page.screenshot({ path: "/work/landing.png", fullPage: true });
  await page.getByRole("button", { name: "Use the sample scenario" }).click();
  await page.getByRole("button", { name: "Approve draft", exact: true }).waitFor({ timeout: 15000 });
  assert.equal(await page.locator(".primary:visible").count(), 1);
  const approveDraftBox = await page.getByRole("button", { name: "Approve draft", exact: true }).boundingBox();
  assert.ok(approveDraftBox.y >= 0 && approveDraftBox.y + approveDraftBox.height <= 900);
  await page.getByRole("tab", { name: "Research", exact: true }).click();
  await page.getByRole("heading", { name: /demonstrably does/ }).waitFor();
  await page.screenshot({ path: "/work/research.png", fullPage: true });
  await page.getByRole("tab", { name: "Demonstration", exact: true }).click();
  await page.getByText("Verified", { exact: true }).waitFor();
  await page.screenshot({ path: "/work/demonstration.png", fullPage: true });
  await page.getByRole("tab", { name: "Outreach", exact: true }).click();
  assert.equal(await page.getByRole("button", { name: "Save edits as new version" }).count(), 0);
  assert.equal(await page.getByRole("heading", { name: "Evidence used in this draft" }).isVisible(), false);
  await page.getByRole("button", { name: "Approve draft", exact: true }).click();
  await page.getByRole("button", { name: "Draft approved", exact: true }).waitFor();
  await page.locator("summary").filter({ hasText: /^Read & edit draft$/ }).click();
  const draftBody = await page.getByLabel("Body", { exact: true }).inputValue();
  assert.ok(draftBody.includes("$16.00"));
  assert.ok(!draftBody.includes("1600 cents"));
  await page.getByLabel("Subject").fill("Edited subject");
  assert.equal(await page.getByRole("button", { name: "Draft approved", exact: true }).isDisabled(), true);
  await page.getByRole("button", { name: "Save edits as new version" }).click();
  await page.getByRole("button", { name: "Approve draft", exact: true }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Approve draft", exact: true }).isDisabled(), false);
  await page.screenshot({ path: "/work/outreach.png", fullPage: true });
  checks.push("prospect trace, demonstration, draft review and edit invalidation");
  await page.getByRole("button", { name: "New prospect" }).click();
  await page.getByLabel("Prospect website").fill("https://169.254.169.254/latest");
  await page.getByRole("button", { name: "Research this prospect" }).click();
  await page.getByRole("alert").filter({ hasText: "Enter a hostname, not an IP address." }).waitFor();
  await page.getByLabel("Prospect website").fill("https://prospect.example/");
  await page.getByRole("button", { name: "Research this prospect" }).click();
  await page.getByText("This prospect stopped.").waitFor();
  await page.getByRole("tab", { name: "Verification", exact: true }).click();
  await page.getByRole("tabpanel").getByText("excerpt_not_in_source").waitFor();
  await page.screenshot({ path: "/work/failure.png", fullPage: true });
  checks.push("blocked address and rejected model research remain visible");
  await page.goto("http://127.0.0.1:8080/__public-mode");
  await page.goto("http://127.0.0.1:8080/#/prospects");
  await page.getByRole("button", { name: "New prospect" }).click();
  await page.getByRole("button", { name: "Use the sample scenario" }).click();
  await page.getByRole("button", { name: "Approve draft", exact: true }).waitFor({ timeout: 15000 });
  await page.screenshot({ path: "/work/public.png", fullPage: true });
  checks.push("public sample journey works");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`http://127.0.0.1:8080/#/experiments/${plans[0].id}`);
  await page.getByText("Purchase rate by original arm", { exact: true }).waitFor();
  await page.screenshot({ path: "/work/mobile.png", fullPage: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false);
  assert.deepEqual(errors, []);
  checks.push("mobile without horizontal overflow; no page errors");
  await writeFile("/work/browser-check.json", JSON.stringify({ kind: "Mocked API UI interaction only", passed: true, checks }, null, 2));
} finally {
  await browser.close();
  server.close();
}
