import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import { api, newId, post } from "./shared";
import { ProspectsWorkspace, type Workspace } from "./prospects";
import {
  ExperimentsHome,
  ExperimentView,
  NewPlanForm,
  QueueView,
  taskLabel,
  useRoute,
  type Overview,
} from "./experiments";

function App() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const route = useRoute();

  async function refresh() {
    const next = await api<Overview>("/api/experiments");
    setOverview(next);
    return next;
  }
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api<Workspace>("/api/workspace");
        if (cancelled) return;
        setWorkspace(data);
        if (data.seeded_demo) {
          try {
            for (let attempt = 0; attempt < 90; attempt++) {
              const seed = await post<{ ready: boolean; stage: string }>("/api/demo/seed", { request_id: newId() });
              if (seed.ready) break;
              if (attempt === 89) throw new Error("Example preparation is still running. Reload to check saved progress.");
              await new Promise(resolve => setTimeout(resolve, 1000));
              if (cancelled) return;
            }
          } catch (e) { setError((e as Error).message); }
        }
        await refresh();
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    setError("");
    if (!loading && route.name !== "prospects") void refresh().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route.key]);

  const publicDemo = !!(workspace?.public_demo || overview?.public_demo);
  const title =
    route.name === "prospects"
      ? "Starting from zero"
      : route.name === "queue"
        ? "Action queue"
        : route.name === "new"
          ? "New analysis plan"
          : route.name === "experiment"
            ? overview?.plans.find((p) => p.id === route.id)?.title || "Analysis"
            : "Home";
  return (
    <div className="shell">
      <aside className="side">
        <a className="brand" href="#/" aria-label="SalesDesk home">
          <span className="mark" aria-hidden="true">
            S
          </span>
          SalesDesk
        </a>
        <nav className="nav" aria-label="Main">
          <a className={`nav-item ${route.name === "home" || route.name === "new" || route.name === "experiment" ? "current" : ""}`} href="#/">
            See what worked
          </a>
          <a className={`nav-item ${route.name === "queue" ? "current" : ""}`} href="#/queue">
            Action queue
            {overview && overview.tasks.some((t) => ["pending_review", "ready_for_review"].includes(t.status)) && (
              <span className="nav-count">{overview.tasks.filter((t) => ["pending_review", "ready_for_review"].includes(t.status)).length}</span>
            )}
          </a>
          <a className={`nav-item ${route.name === "prospects" ? "current" : ""}`} href="#/prospects">
            Starting from zero
          </a>
        </nav>
        <div className="side-label row-between">Saved analyses <a className="side-add" href="#/experiments/new" aria-label="New analysis plan">+</a></div>
        <nav className="side-list" aria-label="Saved analyses">
          {(!overview || overview.plans.length === 0) && <p className="side-empty">No analysis plan yet in this session.</p>}
          {overview?.plans.map((p) => (
            <a key={p.id} className={`side-item ${route.name === "experiment" && route.id === p.id ? "current" : ""}`} href={`#/experiments/${p.id}`}>
              <span className={`dot ${p.latest_run?.status === "succeeded" ? "ready" : p.latest_run?.status === "failed" ? "failed" : ""}`} aria-hidden="true" />
              <span className="side-name">{p.title}</span>
              <span className="side-status">{p.tasks[0] ? taskLabel(p.tasks[0]) : p.latest_run ? p.latest_run.status : "saved"}</span>
            </a>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="top">
          <span>
            Workspace <span className="slash">/</span> {title}
          </span>
          <span className="preview-tag">{publicDemo ? "Public demo" : "Private preview"}</span>
        </header>
        <main>
          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}
          {loading ? (
            <p className="loading" role="status">
              Preparing your SalesDesk workspace on Vultr…
            </p>
          ) : !workspace || !overview ? (
            <div className="empty">
              <h2>Workspace unavailable</h2>
              <p>Start the API with the README instructions, then reload.</p>
              <button className="primary" onClick={() => location.reload()}>
                Reload workspace
              </button>
            </div>
          ) : route.name === "prospects" ? (
            <ProspectsWorkspace workspace={workspace} />
          ) : route.name === "queue" ? (
            <QueueView overview={overview} onChange={async () => void (await refresh())} onError={setError} />
          ) : route.name === "new" ? (
            <NewPlanForm overview={overview} onCreated={async () => void (await refresh())} onError={setError} />
          ) : route.name === "experiment" ? (
            <ExperimentView key={route.id} planId={route.id} onChanged={async () => void (await refresh())} onError={setError} />
          ) : (
            <ExperimentsHome overview={overview} />
          )}
        </main>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
