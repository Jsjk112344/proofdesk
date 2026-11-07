# SalesDesk video v3 — 2:45

The v2-named plan, narration and subtitle files are the maintained source for v3.

## Recording and visual rules

Record the deployed public platform at **1280×720, deviceScaleFactor 1.5**,
output **1920×1080, 30 fps**. Show the whole platform screen most of the time.
No hard crops, transplanted badges or fabricated product values. Slow push-ins,
if used in the final edit, stay at or below **1.3×**, hold, then pull back to full.
The assembled cut uses whole-screen shots throughout.

App text is at least **13 px**; desktop Agent trace text is **15 px**. During a run
the map collapses, keeping the headline, counters, progress and at least eight tiles
above the fold. Tiles pulse while analysing and pop a check when ready. Maria's
wanted car, timeline, best match with score and SMS fit in one drawer view; match
breakdown and alternative matches expand on demand.

Keep the slide-style Maria story, scale-up count, thesis, time skip, number cards
and Vultr diagram. Match the explainer to their dark green, Inter and mint palette.
No separate “Sample dealer group” video-frame overlay. Native app labels remain;
the end-card footer reads “Sample dealer group · SalesDesk drafts; people send.”

Chapter labels: small caps, brand green pill, top left, slide in from the left and
hold for the whole chapter. Captions: bottom centre, Inter SemiBold 42 px, white on
60% dark. Keep **1:49–2:01** caption-free for Maria's SMS. Source exports are silent;
VO, optional documented licensed music and effects belong to the owner's final edit.

## Timeline

| Scene | Time | Visual |
|---|---|---|
| 1 · Maria | 0:00–0:15 | “Nine days ago…” slide, then whole Maria drawer: wanted car, sold timeline, silver car aged 74 days |
| 2 · Scale | 0:15–0:23 | Stylised map and count-up to 1,050 leads at risk |
| 3 · Thesis | 0:23–0:35 | Two thesis beats, then separate promise card at 0:31 |
| 4 · Title | 0:35–0:38 | SalesDesk · Your AI sales analyst |
| 5 · Fan out | 0:38–0:50 | Group logo at 2 AM splits into 24 map nodes; six at once light “Analysing on Vultr”, then checks; lead/car/brief icons; stores 0→24, leads 0→9,000; Vultr compute label |
| 6 · Find who's slipping | 0:50–1:05 | Whole real Group mid-run 0:50–0:53, then whole Sandy Agent trace |
| 7 · Find the right car | 1:05–1:20 | Whole Sandy trace, then whole Maria drawer with match breakdown expanded |
| 8 · Write the brief | 1:20–1:31 | Whole Sandy trace, actual brief and three Qwen follow-ups / 40 drafts |
| 9 · Time skip | 1:31–1:35 | Measured v3 public-run time, rounded; all 24 stores reviewed |
| 10 · Maria payoff | 1:35–2:01 | Whole drawer, real score 98, trade and full SMS; quiet final 12 seconds |
| 11 · Approval | 2:01–2:13 | Whole ranked queue, actual Approve all click, Ready downloads |
| 12 · Group impact | 2:13–2:25 | Headline “Increase your sales without adding headcount.” above 1,007 matched and $3,434,800 estimated gross cards |
| 13 · Vultr | 2:25–2:37 | Nightly scheduler (Vultr VM) → 24 sandboxed jobs (six parallel) → Qwen (Vultr Serverless Inference) → manager approval |
| 14 · Close | 2:37–2:45 | Large “Never lose a sale again.”; “SalesDesk · Sell more with your AI sales analyst”; URL, GitHub and footer |

Step 1 pill spans the explainer and real Group insert (0:38–0:53). Steps 2–4 span
0:53–1:05, 1:05–1:20 and 1:20–1:31 respectively.

## Changed voiceover

Scene 3: “Dealers don't lose these sales for lack of cars. They lose them because
nobody connects the lead to the car in time. SalesDesk makes sure you never lose a
sale to a missed follow-up again.” The separate third card reads **Never lose a
sale to a missed follow-up again.**

Scene 4: “SalesDesk. Your AI sales analyst.”

Scene 14: “SalesDesk. Every lead, every store, every morning. Never lose a sale again.”

The remaining VO is unchanged except the time skip, which must match the newly
recorded measured runtime. Complete read: [narration-v2.txt](narration-v2.txt).
Captions: [subtitles-v2.srt](subtitles-v2.srt). Hand-off: [RECORDING.md](RECORDING.md).

## Facts to verify against the recording before export

- **Maria:** last salesperson contact 7 days ago (no call-count claim); original car sold 6 days ago; silver RAV4 Hybrid XLE, 74 days on lot, match 98; 2017 CR-V trade-in.
- **Group:** 1,050 at risk ("over a thousand"); 1,007 matched; $3,434,800 recoverable gross ("$3.4M").
- **Sandy:** 40 at risk, 25 cold, plus the trace counts (leads read, cars searched here and at sister stores).
- **Run:** recorded public run: 124.758 seconds. 25 accepted Qwen replays, zero new inference calls and $0 new inference cost; compute is separate. Scene 13 makes no cost claim.

## Verified v2 corrections

The public run and exact messages are in `recording-facts-v2.json`. Sandy reads 375
open leads, flags 40 at risk / 25 cold, searches 117 local cars and 1,638 nearby
sister-store cars, and scores 70,200 lead/car pairs. Top store score is 100; Maria's
best match is 98. Qwen supplied three follow-ups; the full queue contains 40 drafts.
Analysis steps share one sandbox pass and complete together after validation.
The public take preserves the saved-response provenance badge. The narrator does
not claim every draft is Qwen-authored or that compute is included in inference cost.
The source has a last-contact timestamp, not a complete call history.

