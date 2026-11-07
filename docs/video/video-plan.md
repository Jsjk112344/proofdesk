# SalesDesk demo video plan (3:00)

Target length **3:00** (check the lablab form for a limit; if it is shorter, cut scene 9 first, then trim scene 10).
Pace: **~150 words/min**. Every scene's narration was counted to fit its slot.
Subtitles: `subtitles.srt` (same folder), timed to this plan. Re-time only if your voiceover drifts.
Resolution: record at **1440×900 browser window, 2× (Retina)**, export **1920×1080**, 30 fps.

## Timeline at a glance

| # | Time | Length | Scene | Screen | Transition in |
|---|---|---|---|---|---|
| 1 | 0:00–0:14 | 14 s | Cold open: the problem | Group view (last night's results), slow zoom on map | Fade from black |
| 2 | 0:14–0:22 | 8 s | Title | Title card over blurred Group view | Blur + fade |
| 3 | 0:22–0:46 | 24 s | The swarm | Click **Run tonight's review now**, tiles + counters live | Hard cut |
|: | 0:42–0:46 | 4 s | Honest jump cut | Card: "Full 24-store run: 2.3 min on Vultr · shortened" | Quick fade |
| 4 | 0:46–1:06 | 20 s | Morning numbers | Finished Group view: stat strip → group brief | Fade out of card |
| 5 | 1:06–1:14 | 8 s | Open a store | Click **Sandy** tile → store queue | Hard cut (natural click) |
| 6 | 1:14–1:52 | 38 s | **Maria G.** (hero) | Open Maria drawer: timeline → best match + breakdown → SMS | Drawer slide-in |
| 7 | 1:52–2:12 | 20 s | Approve | Close drawer → **Approve all for Sandy** → Ready → open `crm-tasks.csv` for 3 s | Hard cut |
| 8 | 2:12–2:24 | 12 s | Walk away | Schedule screen: nightly 2 AM toggle; close tab | Hard cut |
| 9 | 2:24–2:38 | 14 s | Before / after | Slide | Crossfade |
| 10 | 2:38–2:52 | 14 s | Architecture | Slide (diagram builds left→right) | Crossfade |
| 11 | 2:52–3:00 | 8 s | Close | End card: logo, tagline, URL, repo | Crossfade, fade to black |

Time split: **problem 22 s · product working 2 min 2 s · proof/tech 36 s**. The demo is ~70% of the video, per the playbook.

## Scene by scene

### 1. Cold open (0:00–0:14)
- **Screen:** Group view as it loads (previous night's results visible). Slow 1.15× zoom toward the map.
- **Cursor:** still. Don't move it.
- **VO:** "It's 6 AM. Summit Auto Group runs 24 dealerships, with 3,000 cars on the lots and 9,000 open leads. In this sample, 652 leads are cold. Which customer should each store call first?"
- **Zoom:** no punch-ins; let the map breathe.

### 2. Title (0:14–0:22)
- **Screen:** freeze frame of the Group view, blurred 20 px and darkened, with centered title: **SalesDesk**, under it *Sell more: your AI sales analyst.*
- **VO:** "SalesDesk. Sell more: your AI sales analyst. It works every lead, at every rooftop, every night."

### 3. The swarm (0:22–0:46)
- **Screen:** back to the Group view, unblurred. Cursor moves to **Run tonight's review now**, click at 0:24.
- **Zoom:** 0:25 punch to the counter row + progress bar (1.6×) for ~6 s; 0:32 pull back to show map markers and tiles turning "Analysing on Vultr" → "Ready".
- **VO:** "Here's tonight's review. SalesDesk fans the work out across all 24 rooftops: six isolated workers running in parallel on Vultr. Each one checks every lead's risk and searches the inventory at its own store and nearby sister stores. Then Qwen on Vultr Inference writes that store's brief."
- **Jump cut (0:42–0:46):** full-frame card, white text on dark green: "Full 24-store review: 2.3 minutes on Vultr · shortened for this video". Real footage only; never speed up counters.

### 4. Morning numbers (0:46–1:06)
- **Screen:** finished Group view (hero reads "Good morning…").
- **Zoom:** 0:46 punch to stat strip (1.5×), cursor glides left→right under each number as it's spoken; 0:55 hold on **Recoverable gross**; 1:01 pull back and move toward the brief panel, then toward the tile grid.
- **VO:** "By morning: 1,050 leads at risk, 1,007 matched to a car in stock, and 792 distinct aged units matched. That's an estimated $3.4 million in recoverable gross. Leadership sees the group. Every store manager gets a queue."
- **⚠ Match the numbers to your actual take.** If your run shows different figures, update the VO and subtitles 13–15 before export.

### 5. Open a store (1:06–1:14)
- **Screen:** scroll slightly to the tile grid, click **Sandy**. Store view loads with the follow-up queue.
- **VO:** "Let's open Sandy. Forty follow-ups, ranked by risk and by what's on the lot."

### 6. Maria G. (1:14–1:52): the hero scene
- **Screen:** click Maria's card → drawer slides in.
- **Choreography:**
  - 1:14 drawer opens; zoom to the "Wanted a blue 2024 Toyota RAV4 Hybrid XLE / Trade-in 2017 Honda CR-V" box.
  - 1:19 move to timeline; hover "Original vehicle sold · 6 days ago" (orange dot).
  - 1:28 move to **Best match** card: silver RAV4 Hybrid XLE, 74 days on lot, $32,900, score 98. Expand **Match breakdown** at ~1:30.
  - 1:39 hover "Trade-in · 2017 Honda CR-V".
  - 1:44 scroll to "The follow-up, ready for review", SMS tab visible; click **Email** tab at ~1:48 to show it exists, back to SMS.
- **VO:** "Maria asked about a blue 2024 RAV4 Hybrid nine days ago. Her last contact was a week ago, and the car she wanted sold. Without a fresh match, she needs another search. SalesDesk found a silver one on this lot: same model, same trim, in budget. It has sat for 74 days, with an entered daily carrying-cost assumption. It knows she has a 2017 CR-V to trade in. And Qwen drafts the text using only this car's recorded facts."
- **Zoom:** keep 1.3–1.5× here. This is the scene judges remember.

### 7. Approve (1:52–2:12)
- **Screen:** close drawer, click **Approve all for Sandy** (1:54). Show the status pill go to **Ready** with Follow-ups / CRM tasks / Transfers buttons. Click **CRM tasks**, show the CSV opened in Numbers/Excel for ~3 s (2:06–2:09), cut back.
- **VO:** "The manager reads, edits if needed, and approves Sandy in one click. Vultr prepares the drafts, CRM tasks and sister-store transfer requests. These are drafts and tasks. SalesDesk never sends customer messages."
- 2:09–2:12: 3 s of breathing room on the Ready state, no VO.

### 8. Walk away (2:12–2:24)
- **Screen:** sidebar → **Schedule**. Zoom on "Runs every night at 2:00 AM MT on Vultr" (toggle on). At 2:20 press ⌘W (or close the laptop on camera if you record yourself).
- **VO:** "Then close the laptop. The next review runs at 2 AM, every night, for every store, on Vultr. Tomorrow, the queue is waiting again."

### 9. Before / after (2:24–2:38): slide
- **Layout:** two columns. *Before:* "Search the CRM for cold leads · Check if their car sold · Phone other stores for stock · Write every follow-up". *After:* "Open SalesDesk · Approve a ranked queue". Footer: "Full 24-store review: 2.3 min on Vultr (measured)".
- **VO:** "Before: managers dig through leads, sold units and other stores' stock. After: they approve a ranked list. The full 24-store review ran in about two minutes twenty seconds."

### 10. Architecture (2:38–2:52): slide
- **Diagram (builds left→right, ~1 box per second):** Browser → Caddy HTTPS → FastAPI + scheduler on **Vultr VM** → 24 rooftop jobs in disposable **Docker sandboxes**, **6 at a time** → **Vultr Serverless Inference (Qwen)** → Approval → Worker → Downloads.
- **VO:** "Under the hood: a durable scheduler on a Vultr VM, a disposable Docker sandbox for every rooftop, and Qwen on Vultr Serverless Inference for under one cent a run."
- Check the per-run inference cost in STATUS.md before recording. If "a few cents" isn't accurate, change the line.

### 11. Close (2:52–3:00)
- **End card:** SalesDesk logo, *Sell more: your AI sales analyst*, URL `salesdesk.149.28.51.139.sslip.io`, GitHub repo, "Built for Vultr Agent Rush".
- **VO:** "Automotive is our first vertical. SalesDesk: sell more, with your AI sales analyst."

## Measured evidence

The fresh public live-inference run took **140.131 seconds** through the final result capture, including final render/screenshot overhead. All 25 briefs used live Qwen responses. Token-based cost: **$0.0077789**, compute separate. The stat strip is **9,000 reviewed / 1,050 at risk / 1,007 in stock / 792 distinct aged units / $3,434,800 estimated gross** (display rounds gross to $3.4M). The group brief now uses the same in-stock denominator. Six real child jobs entered running state in the first 20 seconds. See `measured-run.json`.

Maria: enquiry 9 days earlier, last contact 7 days earlier, original blue unit sold 6 days earlier; silver 2024 Toyota RAV4 Hybrid XLE, stock S00138, 74 days, $32,900, score 98; 2017 Honda CR-V trade.

Public sample runs execute Docker analysis live and may reuse accepted Qwen responses. Keep the Qwen cached-response disclosure visible on hover; replay is not a fresh inference request. The measured full-live inference cost above is separate.

## How to record

1. **Voiceover first.** Record the full VO in one take from this script (phone or USB mic in a quiet room, ~15 cm away). Then cut footage to fit the VO. Recording the screen first leads to rushed narration.
2. **Screen takes per scene.** Record scenes 1, 3–8 as separate takes in a fresh incognito session at 1440×900. Use **Screen Studio** (auto-zoom, smooth cursor) if you have it; otherwise QuickTime/OBS, with zooms added in the editor.
3. **Scene 3 must be a real run.** Start recording, click Run, let it go ~20 s, then use the labelled jump cut to the finished state.
4. **Editor:** CapCut, DaVinci Resolve or iMovie. Lay down the VO, then the clips, then slides, then import `subtitles.srt` and burn it in (white, semi-bold, dark 60% box, bottom center, ~42 px at 1080p).
5. **Music:** optional, quiet instrumental at −28 dB under the VO, swelling slightly on the title card and end card.
6. **Before export:** check that every number spoken matches the screen at that moment; check the subtitles against the final VO; watch it once with sound off (subtitles alone should tell the story).
