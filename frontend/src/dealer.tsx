import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, newId, post } from "./shared";
import { StoreView, SchedulePage, DataPage } from "./dealer-store";

type Metrics = Record<string, number | null>;
export type Brief = {
  status: string;
  provenance: string;
  failure_reason?: string;
  label?: string;
  rendered?: {
    headline: string;
    findings: string[];
    recommendations?: string[];
  };
  receipt?: unknown;
};
export type Unit = {
  stock_no: string;
  rooftop_id: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  body: string;
  color: string;
  mileage: number;
  list_price: number;
  cost: number;
  days_on_lot: number;
  status: string;
  sold_date?: string;
  eta?: string;
  score: number;
  components: Record<string, number>;
  store_name: string;
  transfer: boolean;
  matched_open_leads?: number;
  floorplan_cost?: number;
};
export type Lead = {
  lead_id: string;
  customer: string;
  first_name: string;
  salesperson: string;
  trade_in: string;
  created_at: string;
  last_contact_at: string;
  wanted: Unit;
  risks: string[];
  matches: Unit[];
  priority: number;
};
export type Followup = {
  provenance?: string;
  id: string;
  lead_id: string;
  content: {
    reason: string;
    sms: string;
    email_subject: string;
    email_body: string;
  };
  version: number;
  sha256: string;
  status: string;
};
export type Rooftop = {
  id: string;
  name: string;
  city: string;
  lat: number;
  lng: number;
  manager: string;
  result: {
    trace?: Record<string, number>;
    metrics: Metrics;
    queue: Lead[];
    brief: Brief;
    previous_metrics?: Metrics;
    aged_inventory: Unit[];
    sources: {
      source: string;
      total: number;
      sold: number;
      close_rate: number;
    }[];
    salespeople: { name: string; median_response_minutes: number }[];
    reconciliation?: unknown;
  } | null;
  followups: Followup[];
  job: {
    id: string;
    status: string;
    events: { stage: string; counts?: Record<string, number> }[];
    failure_reason: string | null;
  } | null;
};
export type DealerView = {
  reference_time: string;
  group: string;
  data_label: string;
  rooftops: Rooftop[];
  review: {
    id: string;
    status: string;
    created_at: string;
    failure_reason?: string;
  } | null;
  rollup: {
    totals: Metrics;
    brief?: Brief;
    deltas: Metrics;
    failures: { rooftop_id: string; reason: string }[];
  };
  validation: {
    file: string;
    rows: number;
    accepted: number;
    rejected: number;
    details: unknown[];
  }[];
  assumptions: { floorplan_daily_rate: number; match_distance_miles: number };
  concurrency: number;
  handoffs: {
    id: string;
    rooftop_id: string;
    status: string;
    failure_reason?: string;
  }[];
  schedule: { enabled: boolean; next_due?: string; last_error?: string };
  saved_sample_review: boolean;
};

export const amount = (n: number | null | undefined) =>
  n == null ? "—" : new Intl.NumberFormat("en-US").format(n);
export const dollars = (n: number | null | undefined) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(n);
export const short = (text: string, count: number) => {
  const words = text.split(/\s+/);
  return words.length > count ? words.slice(0, count).join(" ") + "…" : text;
};
export const vehicle = (unit: Unit) =>
  `${unit.year || ""} ${unit.make} ${unit.model} ${unit.trim}`.trim();
export const storeName = (name: string) => name.replace(/^Summit /, "");
export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    group: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    store: (
      <>
        <path d="M3 10h18L18 3H6l-3 7ZM5 10v11h14V10M9 21v-7h6v7" />
      </>
    ),
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    data: (
      <>
        <ellipse cx="12" cy="5" rx="8" ry="3" />
        <path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0" />
      </>
    ),
    arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
    check: <path d="m5 12 4 4L19 6" />,
    spark: (
      <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z" />
    ),
    close: <path d="m6 6 12 12M6 18 18 6" />,
    chevron: <path d="m9 5 7 7-7 7" />,
    shield: (
      <>
        <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z" />
        <path d="m8 12 3 3 5-6" />
      </>
    ),
    play: <path d="m9 5 11 7-11 7V5Z" />,
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] || paths.spark}
    </svg>
  );
}
export function CarIcon({
  body = "SUV",
  large = false,
}: {
  body?: string;
  large?: boolean;
}) {
  return (
    <svg
      className={`car-icon ${large ? "large" : ""}`}
      viewBox="0 0 100 52"
      fill="none"
      aria-hidden="true"
    >
      <path
        d={
          body === "truck"
            ? "M8 32V21h29l10 11h42v10H8V32ZM14 21V10h20l12 22M50 32V20h38v12"
            : body === "sedan"
              ? "M6 33 24 28l11-13h28l15 14 15 5v9H6V33Z"
              : "M8 32 16 27l8-15h42l15 17 11 4v10H8V32Z"
        }
        fill="currentColor"
        fillOpacity=".12"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path
        d="M30 16h14v13H23m26-13h13l13 13H49V16Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <circle
        cx="24"
        cy="41"
        r="7"
        fill="var(--d-surface)"
        stroke="currentColor"
        strokeWidth="2"
      />
      <circle
        cx="76"
        cy="41"
        r="7"
        fill="var(--d-surface)"
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  );
}
function Stat({
  label,
  value,
  change,
  money = false,
}: {
  label: string;
  value: number | null | undefined;
  change?: number | null;
  money?: boolean;
}) {
  return (
    <div className="d-stat">
      <span>{label}</span>
      <strong key={String(value)}>
        {money ? dollars(value) : amount(value)}
      </strong>
      {change != null && change !== 0 && (
        <small>
          {change > 0 ? "+" : ""}
          {amount(change)} vs. previous night
        </small>
      )}
    </div>
  );
}
export function AnalystBadge({
  brief,
  saved = false,
}: {
  brief?: Brief;
  saved?: boolean;
}) {
  if (!brief || brief.status !== "succeeded") return null;
  return (
    <span
      className="d-analyst"
      title={
        brief.provenance === "saved_replay" || saved
          ? "Cached response: accepted Qwen output for identical inputs. No new inference request."
          : brief.provenance === "deterministic"
            ? "Controller-authored rule-based reading; no inference request."
            : "Validated live Qwen response on Vultr Serverless Inference."
      }
    >
      <Icon name="spark" size={14} />
      {brief.provenance === "deterministic"
        ? "Rule-based analyst"
        : "Qwen 3.8 · Vultr"}
    </span>
  );
}
function phase(roof: Rooftop) {
  if (roof.result?.brief.status === "failed") return "failed";
  if (!roof.job) return roof.result ? "ready" : "idle";
  if (roof.job.status === "failed") return "failed";
  if (roof.job.status === "succeeded") return "ready";
  if (roof.job.status === "scheduled") return "queued";
  return roof.job.events.some((e) => e.stage === "brief_written")
    ? "written"
    : "analysing";
}
const phaseText: Record<string, string> = {
  ready: "Ready for review",
  queued: "Queued",
  analysing: "Analysing on Vultr",
  written: "Brief written",
  failed: "Needs attention",
  idle: "Awaiting review",
};
function RegionalMap({ roofs }: { roofs: Rooftop[] }) {
  const project = (lon: number, lat: number) => [
    (lon + 121) * 31 + 26,
    (46 - lat) * 23 + 2,
  ];
  const polygon = (coords: number[][]) =>
    coords.map(([lon, lat]) => project(lon, lat).join(",")).join(" ");
  const states = [
    {
      name: "NEVADA",
      at: [-116.8, 39],
      coords: [
        [-120, 42],
        [-114, 42],
        [-114, 35],
        [-120, 39],
        [-120, 42],
      ],
    },
    {
      name: "UTAH",
      at: [-112.5, 38],
      coords: [
        [-114, 42],
        [-111, 42],
        [-111, 41],
        [-109, 41],
        [-109, 37],
        [-114, 37],
        [-114, 42],
      ],
    },
    {
      name: "COLORADO",
      at: [-106, 38.7],
      coords: [
        [-109, 41],
        [-102, 41],
        [-102, 37],
        [-109, 37],
        [-109, 41],
      ],
    },
    {
      name: "WYOMING",
      at: [-107.6, 43],
      coords: [
        [-111, 45],
        [-104, 45],
        [-104, 41],
        [-111, 41],
        [-111, 45],
      ],
    },
    {
      name: "IDAHO",
      at: [-115, 44.2],
      coords: [
        [-117, 46],
        [-114.5, 46],
        [-111, 44.4],
        [-111, 42],
        [-117, 42],
        [-116.5, 44.5],
        [-117, 46],
      ],
    },
  ];
  return (
    <svg
      className="regional-map"
      viewBox="0 0 680 290"
      role="img"
      aria-label="Dealer group map across the Mountain West"
    >
      <defs>
        <pattern
          id="map-grid"
          width="22"
          height="22"
          patternUnits="userSpaceOnUse"
        >
          <circle cx="1" cy="1" r=".8" fill="#cbd9d5" />
        </pattern>
      </defs>
      <rect width="680" height="290" fill="url(#map-grid)" />
      {states.map((state) => (
        <g key={state.name}>
          <polygon
            points={polygon(state.coords)}
            fill="#f4f8f6"
            stroke="#c9d7d2"
            strokeWidth="1.2"
          />
          <text
            x={project(state.at[0], state.at[1])[0]}
            y={project(state.at[0], state.at[1])[1]}
            textAnchor="middle"
          >
            {state.name}
          </text>
        </g>
      ))}
      {roofs.map((roof) => {
        const [x, y] = project(roof.lng, roof.lat);
        const p = phase(roof);
        const risk = roof.result?.metrics.at_risk;
        return (
          <a
            key={roof.id}
            href={`#/store/${roof.id}`}
            aria-label={`${roof.name}, ${amount(risk)} at risk`}
          >
            <g className={`map-marker ${p}`}>
              <title>
                {roof.name} · {amount(risk)} at risk
              </title>
              <circle cx={x} cy={y} r={5 + Math.sqrt(risk || 0) / 3} />
              <circle cx={x} cy={y} r="2" className="map-core" />
            </g>
          </a>
        );
      })}
      <text x="36" y="265" className="map-footnote">
        SUMMIT AUTO GROUP · MOUNTAIN WEST
      </text>
    </svg>
  );
}
function RooftopTile({ roof }: { roof: Rooftop }) {
  const p = phase(roof);
  const m = roof.result?.metrics;
  const prev = roof.result?.previous_metrics?.median_response_minutes;
  const response = m?.median_response_minutes;
  return (
    <a className={`rooftop-tile ${p}`} href={`#/store/${roof.id}`}>
      <div className="tile-top">
        <h3>{storeName(roof.name)}</h3>
        <span className="tile-state">
          <i />
          {p === "ready" ? "Ready" : phaseText[p]}
        </span>
      </div>
      {m ? (
        <>
          <div className="tile-risk">
            <strong>{amount(m.at_risk)}</strong>
            <span>leads at risk</span>
          </div>
          <div className="tile-bottom">
            <span>{amount(m.matched_leads)} matches</span>
            <span>{amount(m.aged_matched)} aged units</span>
            <span title="Median first response, compared with the previous saved review">
              {prev != null && response != null
                ? response < prev
                  ? "↘ "
                  : response > prev
                    ? "↗ "
                    : "→ "
                : ""}
              {amount(response)}m
            </span>
          </div>
        </>
      ) : (
        <div className="tile-work">
          <Icon name={p === "failed" ? "shield" : "spark"} size={20} />
          <span>
            {p === "analysing" ? "Reviewing leads & inventory" : phaseText[p]}
          </span>
        </div>
      )}
    </a>
  );
}
function GroupView({
  data,
  run,
  busy,
}: {
  data: DealerView;
  run: () => void;
  busy: boolean;
}) {
  const running =
    !!data.review && ["scheduled", "running"].includes(data.review.status);
  const totals = data.rollup.totals;
  const brief = data.rollup.brief;
  const ready = data.rooftops.filter((r) => phase(r) === "ready").length;
  const mountainDay = (date: Date) =>
    new Intl.DateTimeFormat("en-CA", { timeZone: "America/Denver" }).format(
      date,
    );
  const ranToday =
    data.review &&
    mountainDay(new Date(data.review.created_at)) === mountainDay(new Date());
  return (
    <>
      <section className="d-hero">
        <div>
          <span className="d-eyebrow">YOUR GROUP, WORKED OVERNIGHT</span>
          <h1>
            {running
              ? "Every rooftop. Working together."
              : "Good morning. Here’s what SalesDesk did overnight."}
          </h1>
          <p>
            {running
              ? "Vultr workers are reviewing leads, finding matches, and writing each store’s brief."
              : brief?.rendered?.headline ||
                "Your next morning starts with the leads worth a fresh look."}
          </p>
        </div>
        {!running && (!ranToday || data.review?.status === "failed") && (
          <button className="d-primary" onClick={run} disabled={busy}>
            <Icon name="play" size={16} />
            Run tonight’s review now
          </button>
        )}
        {running && (
          <div className="run-count">
            <strong>
              {ready}
              <span> / {data.rooftops.length}</span>
            </strong>
            <span>rooftops ready</span>
          </div>
        )}
      </section>
      <div className="d-stat-strip">
        <Stat label="Leads reviewed" value={totals.open_leads} />
        <Stat
          label="Leads at risk"
          value={totals.at_risk}
          change={running ? undefined : data.rollup.deltas.at_risk}
        />
        <Stat
          label="Matched to a car in stock"
          value={totals.matched_in_stock}
        />
        <Stat label="Aged units matched" value={totals.aged_matched} />
        <Stat
          label="Recoverable gross (est.)"
          value={totals.recoverable_gross}
          money
        />
      </div>
      {running && (
        <div className="d-live-progress" role="status">
          <div className="progress-track">
            <span
              style={{ width: `${(ready / data.rooftops.length) * 100}%` }}
            />
          </div>
          <span>
            <i className="live-dot" />
            {data.concurrency} parallel workers on Vultr
          </span>
          <div className="live-log">
            {data.rooftops
              .filter((r) => phase(r) === "analysing" || phase(r) === "written")
              .slice(0, 3)
              .map((r) => (
                <span key={r.id}>
                  {storeName(r.name)} ·{" "}
                  {r.job?.events.at(-1)?.stage.replaceAll("_", " ")}
                </span>
              ))}
          </div>
        </div>
      )}
      <div className="group-middle">
        <section className="d-panel map-panel">
          <div className="d-section-heading">
            <div>
              <span className="d-eyebrow">THE GROUP AT A GLANCE</span>
              <h2>Opportunity across the Mountain West</h2>
            </div>
            <span className="d-soft-badge">
              {data.rooftops.length} rooftops
            </span>
          </div>
          <RegionalMap roofs={data.rooftops} />
          <div className="map-legend">
            <span>
              <i className="legend-ready" />
              Ready for review
            </span>
            <span>
              <i className="legend-running" />
              Working on Vultr
            </span>
            <span>
              <i className="legend-queued" />
              Queued
            </span>
          </div>
        </section>
        <section className="d-panel analyst-panel">
          <div className="d-section-heading">
            <h2>Your group brief</h2>
            <AnalystBadge brief={brief} saved={data.saved_sample_review} />
          </div>
          {brief?.status === "failed" ? (
            <p className="d-failure">
              The analyst brief needs attention. Verified numbers are preserved.
            </p>
          ) : (
            <>
              <div className="brief-findings">
                {(brief?.rendered?.findings || [])
                  .slice(0, 3)
                  .map((finding, i) => (
                    <div key={finding}>
                      <span>{String(i + 1).padStart(2, "0")}</span>
                      <p>{short(finding, 25)}</p>
                    </div>
                  ))}
              </div>
              <div className="d-next">
                <span className="d-eyebrow">SUGGESTED NEXT MOVE</span>
                <p>
                  {short(
                    brief?.rendered?.recommendations?.[0] ||
                      "Open a rooftop to review its ranked follow-ups.",
                    25,
                  )}
                </p>
                <a href="#/store/r02">
                  Review Sandy <Icon name="arrow" size={16} />
                </a>
              </div>
            </>
          )}
        </section>
      </div>
      <section id="stores">
        <div className="d-section-heading grid-heading">
          <div>
            <h2>Every store. A clear next move.</h2>
            <span className="d-muted">
              Ranked follow-ups, ready for each manager.
            </span>
          </div>
          <span className="d-muted">{ready} ready for review</span>
        </div>
        <div className="rooftop-grid">
          {data.rooftops.map((roof) => (
            <RooftopTile key={roof.id} roof={roof} />
          ))}
        </div>
      </section>
      {data.rollup.failures.length > 0 && (
        <div className="d-alert">
          {data.rollup.failures.length} rooftop reviews need attention. Open
          Verification for details.
        </div>
      )}
      {(brief?.rendered?.recommendations?.length || 0) > 1 && (
        <section className="d-panel recommendations">
          <h2>Group recommendations</h2>
          {brief?.rendered?.recommendations?.slice(1).map((text) => (
            <p key={text}>{text}</p>
          ))}
        </section>
      )}
    </>
  );
}

let workspaceBootstrap: Promise<unknown> | undefined;
const ensureWorkspace = () => (workspaceBootstrap ||= api("/api/workspace"));
export function DealerApp() {
  const [data, setData] = useState<DealerView | null>(null);
  const [route, setRoute] = useState(location.hash);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [verification, setVerification] = useState(false);
  const fetching = useRef(false);
  const refresh = async () => {
    if (fetching.current) return;
    fetching.current = true;
    try {
      setData(await api<DealerView>("/api/dealer"));
    } finally {
      fetching.current = false;
    }
  };
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        await ensureWorkspace();
        if (live) await refresh();
      } catch (e) {
        if (live) setError((e as Error).message);
      }
    })();
    const listener = () => {
      setRoute(location.hash);
      setError("");
    };
    window.addEventListener("hashchange", listener);
    return () => {
      live = false;
      window.removeEventListener("hashchange", listener);
    };
  }, []);
  const active =
    (data?.review && ["scheduled", "running"].includes(data.review.status)) ||
    data?.handoffs.some((h) => ["scheduled", "running"].includes(h.status));
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => {
      void refresh().catch((e) => setError((e as Error).message));
    }, 800);
    return () => clearInterval(timer);
  }, [active]);
  const action = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
      await refresh().catch(() => {});
    } finally {
      setBusy(false);
    }
  };
  const run = () =>
    void action(() => post("/api/dealer/reviews", { request_id: newId() }));
  const selected = route.startsWith("#/store/")
    ? data?.rooftops.find((r) => r.id === route.split("/")[2])
    : null;
  useEffect(() => {
    if (route === "#/stores" && data)
      document.getElementById("stores")?.scrollIntoView({ block: "start" });
    else window.scrollTo(0, 0);
  }, [route, !!data]);
  const page =
    route === "#/schedule"
      ? "Schedule"
      : route === "#/data"
        ? "Data"
        : selected
          ? storeName(selected.name)
          : "Group overview";
  return (
    <div className="dealer-shell">
      <aside className="d-sidebar">
        <a className="d-brand" href="#/">
          <span className="d-logo">
            <Icon name="spark" size={21} />
          </span>
          SalesDesk<span className="d-brand-dot">.</span>
        </a>
        <div className="d-workspace-label">
          <span className="workspace-avatar">S</span>
          <div>
            <strong>{data?.group || "SalesDesk"}</strong>
            <span>Dealer group workspace</span>
          </div>
        </div>
        <nav aria-label="Main">
          {[
            ["Group", "group", "#/"],
            ["Stores", "store", "#/stores"],
            ["Schedule", "clock", "#/schedule"],
            ["Data", "data", "#/data"],
          ].map(([label, icon, link]) => (
            <a
              key={label}
              href={link}
              className={
                route === link ||
                (label === "Stores" && selected) ||
                (label === "Group" && !route)
                  ? "current"
                  : ""
              }
            >
              <Icon name={icon} />
              {label}
              {label === "Stores" && data && (
                <small>{data.rooftops.length}</small>
              )}
            </a>
          ))}
        </nav>
        <div className="d-sidebar-bottom">
          <div className="vultr-indicator">
            <i />
            Powered by Vultr
          </div>
          <p>
            Every lead. Every rooftop.
            <br />A better morning.
          </p>
          <button onClick={() => setVerification(true)}>
            <Icon name="shield" size={16} />
            Verification
          </button>
          <div className="d-account">
            <span>GM</span>
            <div>
              Group leadership<small>{data?.group || "Dealer group"}</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="d-main">
        <header className="d-topbar">
          <div className="d-breadcrumb">
            Workspace <span>/</span>
            <strong>{page}</strong>
          </div>
          <div className="d-top-actions">
            <span className="sample-badge">
              {data?.data_label || "Sample dealer group"}
            </span>
            <label className="d-role-switch">
              <Icon name={selected ? "store" : "group"} size={16} />
              <select
                aria-label="View role"
                value={selected?.id || "group"}
                onChange={(e) => {
                  location.hash =
                    e.target.value === "group"
                      ? "#/"
                      : `#/store/${e.target.value}`;
                }}
              >
                <option value="group">Group view</option>
                {data?.rooftops.map((roof) => (
                  <option key={roof.id} value={roof.id}>
                    {storeName(roof.name)}
                  </option>
                ))}
              </select>
            </label>
            <span className="d-top-avatar">GM</span>
          </div>
        </header>
        <main className="d-content">
          {error && (
            <div role="alert" className="d-alert">
              {error}
            </div>
          )}
          {!data ? (
            <div className="d-loading" role="status">
              <Icon name="spark" size={30} />
              <h1>Opening your morning desk</h1>
              <p>Your dealer group is loading.</p>
            </div>
          ) : route === "#/schedule" ? (
            <SchedulePage data={data} run={run} busy={busy} action={action} />
          ) : route === "#/data" ? (
            <DataPage data={data} action={action} />
          ) : selected ? (
            <StoreView
              key={selected.id}
              roof={selected}
              data={data}
              busy={busy}
              action={action}
              run={run}
            />
          ) : (
            <GroupView data={data} busy={busy} run={run} />
          )}
        </main>
        <footer className="d-footer">
          <span>SalesDesk · Sell more: Your AI sales analyst.</span>
          <button onClick={() => setVerification(true)}>
            Verification <Icon name="shield" size={13} />
          </button>
        </footer>
      </div>
      {verification && (
        <div className="d-overlay" onClick={() => setVerification(false)}>
          <section
            className="d-drawer verification-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Verification"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="d-section-heading">
              <h2>Verification</h2>
              <button
                className="d-icon-button"
                aria-label="Close Verification"
                onClick={() => setVerification(false)}
              >
                <Icon name="close" />
              </button>
            </div>
            <p>
              Synthetic sample: fictional group and people; makes and models are
              product names. CSV exports are untrusted and session-scoped.
            </p>
            <p>
              Floorplan entered assumption:{" "}
              {dollars(data?.assumptions.floorplan_daily_rate)} per unit per
              day. Match distance:{" "}
              {amount(data?.assumptions.match_distance_miles)} miles.
            </p>
            <p>
              Recoverable gross estimates listed price minus cost per best lead
              match. The same car may appear for several leads; this is not a
              sales forecast.
            </p>
            <p>
              Qwen labels identify accepted live output or exact-input cached
              responses. Additional follow-ups use labelled controller
              templates. Drafts and CRM tasks require human approval. Nothing is
              sent, and no CRM/DMS is connected.
            </p>
            <p>
              Anonymous workspace and schedule expire with the session. Nightly
              recurrence is bounded by review quotas.
            </p>
            <details>
              <summary>
                Requests, jobs, validation and approval versions
              </summary>
              <pre>{JSON.stringify(data, null, 2)}</pre>
            </details>
          </section>
        </div>
      )}
    </div>
  );
}

// Focused store and operating surfaces keep the group shell shared.
