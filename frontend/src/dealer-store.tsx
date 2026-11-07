import { useEffect, useRef, useState } from "react";
import { api, newId, post } from "./shared";
import {
  AnalystBadge,
  CarIcon,
  Icon,
  amount,
  dollars,
  short,
  storeName,
  vehicle,
  type DealerView,
  type Followup,
  type Lead,
  type Rooftop,
  type Unit,
} from "./dealer";
type Action = (fn: () => Promise<unknown>) => Promise<void>;
const approvalVersion = (row: Followup) => ({
  id: row.id,
  version: row.version,
  sha256: row.sha256,
});

function StoreStat({
  value,
  label,
  suffix = "",
}: {
  value: number | null | undefined;
  label: string;
  suffix?: string;
}) {
  return (
    <div className="d-stat">
      <span>{label}</span>
      <strong>
        {amount(value)}
        {suffix && value != null && <em>{suffix}</em>}
      </strong>
    </div>
  );
}
function ScheduleCard({
  data,
  action,
  full = false,
}: {
  data: DealerView;
  action: Action;
  full?: boolean;
}) {
  return (
    <section className={`d-panel schedule-card ${full ? "full" : ""}`}>
      <span className="schedule-icon">
        <Icon name="clock" size={24} />
      </span>
      <div>
        <h2>Your next morning is already covered.</h2>
        <p>Runs every night at 2:00 AM MT on Vultr</p>
        {data.schedule.last_error && (
          <p className="d-failure">
            Schedule needs attention. Open Verification for details.
          </p>
        )}
      </div>
      <label className="schedule-toggle">
        <input
          type="checkbox"
          role="switch"
          aria-label="Nightly review schedule"
          checked={!!data.schedule.enabled}
          onChange={(e) =>
            void action(() =>
              post("/api/dealer/schedule", { enabled: e.target.checked }),
            )
          }
        />
        <span aria-hidden="true" />
        <small>{data.schedule.enabled ? "On" : "Off"}</small>
      </label>
    </section>
  );
}
export function SchedulePage({
  data,
  run,
  busy,
  action,
}: {
  data: DealerView;
  run: () => void;
  busy: boolean;
  action: Action;
}) {
  return (
    <>
      <div className="d-hero">
        <div>
          <span className="d-eyebrow">
            WORK CONTINUES AFTER YOU CLOSE THE TAB
          </span>
          <h1>A fresh desk, every morning.</h1>
          <p>
            Your group’s review runs on Vultr. Store managers return to ranked
            follow-ups.
          </p>
        </div>
        <button
          className="d-primary"
          onClick={run}
          disabled={
            busy ||
            (!!data.review &&
              ["scheduled", "running"].includes(data.review.status))
          }
        >
          <Icon name="play" size={16} />
          Run now
        </button>
      </div>
      <ScheduleCard data={data} action={action} full />
      <section className="schedule-steps d-panel">
        <h2>The overnight routine</h2>
        <div>
          {[
            [
              "data",
              "Review every lead",
              "Find cold leads and changed vehicle availability.",
            ],
            [
              "spark",
              "Match the right car",
              "Consider nearby stores and aged inventory.",
            ],
            [
              "store",
              "Prepare each store",
              "Rank opportunities and draft the follow-ups.",
            ],
            [
              "check",
              "You approve",
              "Salespeople receive tasks and drafts to review.",
            ],
          ].map(([icon, title, body]) => (
            <div key={title}>
              <Icon name={icon} size={25} />
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
function FollowupCard({
  lead,
  row,
  rank,
  approve,
  skip,
  edit,
  detail,
  busy,
}: {
  lead: Lead;
  row?: Followup;
  rank: number;
  approve: () => void;
  skip: () => void;
  edit: () => void;
  detail: () => void;
  busy: boolean;
}) {
  const [tab, setTab] = useState("sms");
  const unit = lead.matches[0];
  return (
    <article
      className={`followup-card ${row?.status === "approved" ? "approved" : ""}`}
    >
      <div className="followup-person">
        <span className="lead-rank">{String(rank).padStart(2, "0")}</span>
        <div>
          <button
            onClick={detail}
            className="customer-name"
            aria-label={`Open ${lead.customer} details`}
          >
            {lead.customer}
            <Icon name="chevron" size={13} />
          </button>
          <span className="wanted-summary">
            Wanted {lead.wanted.color} {lead.wanted.make} {lead.wanted.model}{" "}
            {lead.wanted.trim}
          </span>
        </div>
        <span className="lead-risk">
          {row?.status === "approved" ? (
            <>
              <Icon name="check" size={12} />
              Approved
            </>
          ) : lead.risks.includes("Vehicle sold") ? (
            "Original vehicle sold"
          ) : (
            lead.risks[0]
          )}
        </span>
      </div>
      <div className="followup-content">
        <div className="unit-match">
          <div className="unit-picture">
            <CarIcon body={unit.body} />
            <span>{unit.color}</span>
          </div>
          <div>
            <span className="match-kicker">WHAT WE HAVE NOW</span>
            <h3>{vehicle(unit)}</h3>
            <div className="unit-meta">
              <strong>{dollars(unit.list_price)}</strong>
              <span>·</span>
              <span>{unit.days_on_lot} days on lot</span>
            </div>
            <span
              className={`unit-location ${unit.transfer ? "transfer" : ""}`}
            >
              {unit.transfer
                ? `At ${storeName(unit.store_name)}, transfer`
                : unit.status === "in_transit"
                  ? "In transit to this store"
                  : "In stock at this store"}
            </span>
          </div>
        </div>
        <div className="message-preview">
          <div
            className="message-tabs"
            role="tablist"
            aria-label={`Message preview for ${lead.customer}`}
          >
            <button
              role="tab"
              aria-selected={tab === "sms"}
              onClick={() => setTab("sms")}
            >
              SMS
            </button>
            <button
              role="tab"
              aria-selected={tab === "email"}
              onClick={() => setTab("email")}
            >
              Email
            </button>
            <span>
              {row?.provenance === "deterministic_template"
                ? "Template"
                : row?.provenance === "human_edited"
                  ? "Your edit"
                  : "Qwen draft"}{" "}
              · {lead.salesperson.split(" ")[0]}
            </span>
          </div>
          <p>
            {row
              ? short(
                  tab === "sms"
                    ? row.content.sms
                    : `${row.content.email_subject} — ${row.content.email_body}`,
                  14,
                )
              : "Draft unavailable. Open Verification for the analyst status."}
          </p>
        </div>
      </div>
      <div className="followup-footer">
        <span>
          <Icon name="spark" size={12} />
          {short(row?.content.reason || "Review the match", 10)}
        </span>
        <div>
          <button
            className="d-text-button"
            onClick={skip}
            disabled={busy || !row || row.status === "skipped"}
          >
            Skip
          </button>
          <button
            className="d-text-button"
            onClick={edit}
            disabled={busy || !row}
          >
            Edit
          </button>
          <button
            className="d-approve"
            onClick={approve}
            disabled={busy || !row || row.status === "approved"}
          >
            <Icon name="check" size={13} />
            {row?.status === "approved" ? "Approved" : "Approve"}
          </button>
        </div>
      </div>
    </article>
  );
}
function LeadDrawer({
  lead,
  row,
  close,
  approve,
  busy,
  primary = true,
  referenceTime,
}: {
  lead: Lead;
  row?: Followup;
  close: () => void;
  approve: () => void;
  busy: boolean;
  primary?: boolean;
  referenceTime: string;
}) {
  const [tab, setTab] = useState("sms");
  const ref = useRef<HTMLElement>(null);
  const dayAgo = (date?: string) =>
    date
      ? `${Math.max(0, Math.round((Date.parse(referenceTime) - Date.parse(date)) / 86400000))} days ago`
      : "This review";
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    ref.current?.focus();
    const handle = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
      if (event.key === "Tab") {
        const nodes = ref.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),a[href],textarea,input,select",
        );
        if (!nodes?.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", handle);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handle);
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, []);
  const limits: Record<string, number> = {
    make: 20,
    model: 25,
    trim: 10,
    body: 8,
    year: 8,
    color: 2,
    budget: 10,
    mileage: 3,
    "aged inventory": 6,
    "same store": 8,
  };
  return (
    <div className="d-overlay" onClick={close}>
      <section
        className="d-drawer lead-drawer"
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={`${lead.customer} lead detail`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="d-section-heading">
          <div>
            <span className="d-eyebrow">AN OPPORTUNITY WORTH REOPENING</span>
            <h2>{lead.customer}</h2>
          </div>
          <button
            className="d-icon-button"
            aria-label="Close lead detail"
            onClick={close}
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="lead-context">
          <p>
            Wanted a {lead.wanted.color} {vehicle(lead.wanted)}
          </p>
          {lead.trade_in && (
            <span>
              Trade-in · {lead.trade_in.split("|").slice(0, 3).join(" ")}
            </span>
          )}
        </div>
        <ol className="lead-timeline">
          <li>
            <i />
            <div>
              <strong>Enquiry received</strong>
              <span>{dayAgo(lead.created_at)}</span>
            </div>
          </li>
          <li>
            <i />
            <div>
              <strong>Last salesperson contact</strong>
              <span>{dayAgo(lead.last_contact_at)}</span>
            </div>
          </li>
          {lead.risks.includes("Vehicle sold") && (
            <li className="sold">
              <i />
              <div>
                <strong>Original vehicle sold</strong>
                <span>{dayAgo(lead.wanted.sold_date)}</span>
              </div>
            </li>
          )}
          <li className="matched">
            <i>
              <Icon name="spark" size={10} />
            </i>
            <div>
              <strong>SalesDesk found a fresh match</strong>
              <span>This review</span>
            </div>
          </li>
        </ol>
        <div className="candidate-heading">
          <h3>The best available matches</h3>
          <span>Score out of 100</span>
        </div>
        <div className="candidate-list">
          {lead.matches.map((unit, index) => (
            <div
              className={`candidate ${index === 0 ? "chosen" : ""}`}
              key={unit.stock_no}
            >
              <div className="candidate-main">
                <CarIcon body={unit.body} />
                <div>
                  <span className="match-kicker">
                    {index === 0 ? "BEST MATCH" : `ALTERNATIVE ${index + 1}`}
                  </span>
                  <h3>{vehicle(unit)}</h3>
                  <p>
                    {unit.color} · {unit.days_on_lot} days on lot ·{" "}
                    {dollars(unit.list_price)}
                  </p>
                  <span className="d-muted">
                    {unit.transfer
                      ? `At ${storeName(unit.store_name)}, transfer`
                      : "At this store"}
                  </span>
                </div>
                <strong className="match-score">
                  {unit.score}
                  <small>match</small>
                </strong>
              </div>
              <details className="score-details" open={index === 0}>
                <summary>Match breakdown</summary>
                <div>
                  {Object.entries(unit.components).map(([key, value]) => (
                    <div key={key}>
                      <span>{key}</span>
                      <i>
                        <em
                          style={{ width: `${(value / limits[key]) * 100}%` }}
                        />
                      </i>
                      <small>
                        {value}/{limits[key]}
                      </small>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          ))}
        </div>
        {row && (
          <section className="drawer-message">
            <div className="d-section-heading">
              <h3>The follow-up, ready for review</h3>
              <div
                className="message-tabs"
                role="tablist"
                aria-label="Lead message"
              >
                <button
                  role="tab"
                  aria-selected={tab === "sms"}
                  onClick={() => setTab("sms")}
                >
                  SMS
                </button>
                <button
                  role="tab"
                  aria-selected={tab === "email"}
                  onClick={() => setTab("email")}
                >
                  Email
                </button>
              </div>
            </div>
            <p>
              {tab === "sms" ? (
                row.content.sms
              ) : (
                <>
                  <strong>{row.content.email_subject}</strong>
                  <br />
                  <br />
                  {row.content.email_body}
                </>
              )}
            </p>
          </section>
        )}
        <div className="drawer-approval">
          <div>
            <span>Assigned to</span>
            <strong>{lead.salesperson}</strong>
          </div>
          <button
            className={primary ? "d-primary" : "d-approve"}
            onClick={approve}
            disabled={busy || !row || row.status === "approved"}
          >
            <Icon name="check" size={16} />
            {row?.status === "approved" ? "Approved" : "Approve follow-up"}
          </button>
        </div>
      </section>
    </div>
  );
}
function EditDrawer({
  row,
  close,
  save,
  busy,
}: {
  row: Followup;
  close: () => void;
  save: (content: Followup["content"]) => void;
  busy: boolean;
}) {
  const [content, setContent] = useState(row.content);
  return (
    <div className="d-overlay" onClick={close}>
      <section
        className="d-drawer edit-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Edit follow-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="d-section-heading">
          <h2>Edit follow-up</h2>
          <button
            className="d-icon-button"
            aria-label="Close editor"
            onClick={close}
          >
            <Icon name="close" />
          </button>
        </div>
        <p>Save your message for a fresh approval.</p>
        <label>
          SMS
          <textarea
            maxLength={320}
            value={content.sms}
            onChange={(e) => setContent({ ...content, sms: e.target.value })}
          />
        </label>
        <label>
          Email subject
          <input
            maxLength={100}
            value={content.email_subject}
            onChange={(e) =>
              setContent({ ...content, email_subject: e.target.value })
            }
          />
        </label>
        <label>
          Email
          <textarea
            maxLength={1000}
            value={content.email_body}
            onChange={(e) =>
              setContent({ ...content, email_body: e.target.value })
            }
          />
        </label>
        <button
          className="d-primary"
          disabled={busy}
          onClick={() => save(content)}
        >
          Save message
        </button>
      </section>
    </div>
  );
}
export function StoreView({
  roof,
  data,
  busy,
  action,
  run,
}: {
  roof: Rooftop;
  data: DealerView;
  busy: boolean;
  action: Action;
  run: () => void;
}) {
  const [detail, setDetail] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const result = roof.result;
  const metrics = result?.metrics;
  const rows = roof.followups;
  const queue = (result?.queue || []).filter(
    (lead) =>
      lead.matches.length > 0 &&
      rows.find((row) => row.lead_id === lead.lead_id)?.status !== "skipped",
  );
  const selected = queue.find((lead) => lead.lead_id === detail);
  const edited = rows.find((row) => row.id === editing);
  const pending = rows.filter((row) => row.status === "pending");
  const handoff = data.handoffs.find((h) => h.rooftop_id === roof.id);
  const availableRows = rows.filter((row) => row.status !== "skipped");
  const needsHandoff =
    pending.length > 0 || !handoff || handoff.status === "failed";
  const approve = (items: Followup[]) =>
    void action(() =>
      post(`/api/dealer/stores/${roof.id}/approve`, {
        versions: items.map(approvalVersion),
        request_id: newId(),
      }),
    );
  const modal = !!selected || !!edited;
  return (
    <>
      <section className="d-hero store-hero">
        <div>
          <a className="d-back" href="#/">
            <span>←</span> Group overview
          </a>
          <div className="store-title">
            <h1>{roof.name}</h1>
            <span className="d-soft-badge">
              {roof.job?.status === "failed" ||
              result?.brief.status === "failed"
                ? "Needs attention"
                : result
                  ? "Morning review"
                  : "Review pending"}
            </span>
          </div>
          <p>
            {roof.manager} <span>·</span> Store manager <span>·</span>{" "}
            {result?.brief.rendered?.headline ||
              "Your rooftop review is being prepared."}
          </p>
        </div>
        {result ? (
          <button
            className="d-primary"
            style={modal ? { visibility: "hidden" } : undefined}
            disabled={busy || !availableRows.length || !needsHandoff}
            onClick={() => approve(availableRows)}
          >
            <Icon name="check" size={15} />
            Approve all for {storeName(roof.name)}
          </button>
        ) : (
          <button className="d-primary" onClick={run} disabled={busy}>
            Run review
          </button>
        )}
      </section>
      <div className="d-stat-strip store-stats">
        <StoreStat label="Cold leads" value={metrics?.cold_leads} />
        <StoreStat label="Matched leads" value={metrics?.matched_leads} />
        <StoreStat label="Aged units matched" value={metrics?.aged_matched} />
        <StoreStat
          label="Median first response"
          value={metrics?.median_response_minutes}
          suffix=" min"
        />
      </div>
      {handoff && (
        <section
          className={`handoff-panel d-panel ${handoff.status === "succeeded" ? "ready" : ""}`}
        >
          <span className="handoff-icon">
            <Icon
              name={handoff.status === "succeeded" ? "check" : "clock"}
              size={20}
            />
          </span>
          <div>
            <h3>
              {handoff.status === "succeeded"
                ? "Ready"
                : handoff.status === "failed"
                  ? "Preparation needs attention"
                  : "Preparing on Vultr · you can close this tab"}
            </h3>
            {handoff.status === "succeeded" && (
              <p>Approved tasks and drafts for your salespeople.</p>
            )}
          </div>
          {handoff.status === "succeeded" && (
            <div className="handoff-downloads">
              <a
                aria-label="Follow-ups"
                href={`/api/dealer/handoffs/${handoff.id}/follow-ups.md`}
              >
                Follow-ups <span>↓</span>
              </a>
              <a
                aria-label="CRM tasks"
                href={`/api/dealer/handoffs/${handoff.id}/crm-tasks.csv`}
              >
                CRM tasks <span>↓</span>
              </a>
              <a
                aria-label="Transfers"
                href={`/api/dealer/handoffs/${handoff.id}/transfer-requests.csv`}
              >
                Transfers <span>↓</span>
              </a>
            </div>
          )}
        </section>
      )}
      <section className="store-queue">
        <div className="d-section-heading queue-heading">
          <div>
            <h2>
              Your morning follow-ups <span>{queue.length}</span>
            </h2>
            <p>Ranked by lead risk and available inventory.</p>
          </div>
          <AnalystBadge
            brief={result?.brief}
            saved={data.saved_sample_review}
          />
        </div>
        {(showAll ? queue : queue.slice(0, 8)).map((lead, index) => {
          const row = rows.find((row) => row.lead_id === lead.lead_id);
          return (
            <FollowupCard
              key={lead.lead_id}
              lead={lead}
              row={row}
              rank={index + 1}
              busy={busy}
              detail={() => setDetail(lead.lead_id)}
              edit={() => row && setEditing(row.id)}
              skip={() =>
                row &&
                void action(() =>
                  post(`/api/dealer/followups/${row.id}/skip`, {
                    sha256: row.sha256,
                  }),
                )
              }
              approve={() => row && approve([row])}
            />
          );
        })}
        {!queue.length && (
          <div className="d-panel queue-empty">
            <Icon name="spark" size={25} />
            <p>
              {roof.job?.status === "failed" ||
              result?.brief.status === "failed"
                ? "This rooftop needs attention. Review the saved failure in Verification."
                : "Follow-ups appear here when the review is ready."}
            </p>
          </div>
        )}
        {!showAll && queue.length > 8 && (
          <button className="show-more" onClick={() => setShowAll(true)}>
            See all {queue.length} follow-ups <Icon name="chevron" size={14} />
          </button>
        )}
      </section>
      {result && (
        <details className="numbers-panel d-panel">
          <summary>
            See the numbers <span>Response, sources & aged inventory</span>
          </summary>
          <div className="store-tables">
            <section>
              <h3>First response by salesperson</h3>
              <table>
                <thead>
                  <tr>
                    <th>Salesperson</th>
                    <th>Median response</th>
                  </tr>
                </thead>
                <tbody>
                  {result.salespeople.map((person) => (
                    <tr key={person.name}>
                      <td>{person.name}</td>
                      <td>{amount(person.median_response_minutes)} min</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section>
              <h3>Close rate by source</h3>
              <table>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Sold / leads</th>
                    <th>Close rate</th>
                  </tr>
                </thead>
                <tbody>
                  {result.sources.map((source) => (
                    <tr key={source.source}>
                      <td>{source.source}</td>
                      <td>
                        {source.sold} / {source.total}
                      </td>
                      <td>{(source.close_rate * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="aged-table">
              <h3>Aged inventory</h3>
              <table>
                <thead>
                  <tr>
                    <th>Vehicle</th>
                    <th>Age</th>
                    <th>Matched open leads</th>
                    <th>Floorplan cost to date</th>
                  </tr>
                </thead>
                <tbody>
                  {result.aged_inventory.map((unit) => (
                    <tr key={unit.stock_no}>
                      <td>{vehicle(unit)}</td>
                      <td>{unit.days_on_lot} days</td>
                      <td>{unit.matched_open_leads}</td>
                      <td>{dollars(unit.floorplan_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>
        </details>
      )}
      <ScheduleCard data={data} action={action} />
      {selected && (
        <LeadDrawer
          lead={selected}
          referenceTime={data.reference_time}
          row={rows.find((row) => row.lead_id === selected.lead_id)}
          close={() => setDetail(null)}
          approve={() => {
            const row = rows.find((row) => row.lead_id === selected.lead_id);
            if (row) approve([row]);
          }}
          busy={busy}
        />
      )}
      {edited && (
        <EditDrawer
          key={edited.id + edited.version}
          row={edited}
          close={() => setEditing(null)}
          busy={busy}
          save={(content) =>
            void action(async () => {
              const { reason: _reason, ...message } = content;
              await post(`/api/dealer/followups/${edited.id}/edit`, {
                base_sha256: edited.sha256,
                content: message,
              });
              setEditing(null);
            })
          }
        />
      )}
    </>
  );
}
export function DataPage({
  data,
  action,
}: {
  data: DealerView;
  action: Action;
}) {
  const [files, setFiles] = useState<Record<string, File>>({});
  const [reports, setReports] = useState(data.validation);
  const [rate, setRate] = useState(data.assumptions.floorplan_daily_rate);
  const [distance, setDistance] = useState(
    data.assumptions.match_distance_miles,
  );
  const [uploading, setUploading] = useState(false);
  useEffect(() => setReports(data.validation), [data.validation]);
  const upload = () =>
    void action(async () => {
      setUploading(true);
      try {
        const next = [];
        for (const kind of ["rooftops", "inventory", "leads"]) {
          if (!files[kind]) throw new Error("Choose all three CSV files.");
          if (files[kind].size > 10 * 1024 * 1024)
            throw new Error("Each file must be at most 10 MB.");
          next.push(
            await api<DealerView["validation"][number]>(
              `/api/dealer/import/${kind}`,
              {
                method: "POST",
                headers: { "Content-Type": "text/csv" },
                body: files[kind],
              },
            ),
          );
        }
        setReports(next);
        if (next.some((report) => report.rejected))
          throw new Error(
            "Some rows need attention. Review the validation details.",
          );
        await post("/api/dealer/import", {});
      } finally {
        setUploading(false);
      }
    });
  return (
    <>
      <div className="d-hero">
        <div>
          <span className="d-eyebrow">CSV IN, MORNING PRIORITIES OUT</span>
          <h1>Your dealer-group data</h1>
          <p>
            Export leads and inventory, add your stores, and let SalesDesk do
            the review.
          </p>
        </div>
        <button
          className="d-primary"
          onClick={upload}
          disabled={uploading || Object.keys(files).length !== 3}
        >
          <Icon name="data" size={16} />
          Import CSV files
        </button>
      </div>
      <div className="data-file-grid">
        {[
          [
            "rooftops",
            "Your stores",
            "Store locations, managers and salespeople.",
          ],
          [
            "inventory",
            "Your inventory",
            "Available cars, prices, cost and age.",
          ],
          [
            "leads",
            "Your leads",
            "Open opportunities and recent sales history.",
          ],
        ].map(([kind, label, description]) => (
          <section className="d-panel data-file" key={kind}>
            <Icon
              name={
                kind === "rooftops"
                  ? "store"
                  : kind === "inventory"
                    ? "group"
                    : "data"
              }
              size={24}
            />
            <h2>{label}</h2>
            <p>{description}</p>
            <label className="file-picker">
              {files[kind]?.name || "Choose CSV"}
              <input
                type="file"
                accept=".csv,text/csv"
                aria-label={label + " CSV"}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) setFiles({ ...files, [kind]: file });
                }}
              />
            </label>
            <small className="file-limit">CSV · up to 10 MB</small>
            <a href={`/api/dealer/templates/${kind}.csv`}>
              Download {kind} template <span>↓</span>
            </a>
          </section>
        ))}
      </div>
      <section className="d-panel data-validation">
        <div className="d-section-heading">
          <h2>Import validation</h2>
          <span className="d-soft-badge">{data.data_label}</span>
        </div>
        <div className="validation-counts">
          {reports.map((report) => (
            <div key={report.file}>
              <span>{report.file}</span>
              <strong>{amount(report.accepted)}</strong>
              <small>
                accepted
                {report.rejected
                  ? ` · ${amount(report.rejected)} need attention`
                  : ""}
              </small>
            </div>
          ))}
        </div>
        {reports.some((report) => report.rejected > 0) && (
          <p className="validation-note">Review row details in Verification.</p>
        )}
      </section>
      <details className="d-panel data-assumptions">
        <summary>Review assumptions</summary>
        <div>
          <label>
            Floorplan cost per unit per day ($)
            <input
              type="number"
              min="0"
              max="1000"
              value={rate}
              onChange={(e) => setRate(Number(e.target.value))}
            />
          </label>
          <label>
            Sister-store distance (miles)
            <input
              type="number"
              min="0"
              max="2000"
              value={distance}
              onChange={(e) => setDistance(Number(e.target.value))}
            />
          </label>
          <button
            className="d-approve"
            onClick={() =>
              void action(() =>
                post("/api/dealer/assumptions", {
                  floorplan_daily_rate: rate,
                  match_distance_miles: distance,
                }),
              )
            }
          >
            Save assumptions
          </button>
        </div>
      </details>
      <div className="data-next">
        <Icon name="arrow" size={18} />
        <p>Next: live CRM/DMS connections.</p>
      </div>
    </>
  );
}
