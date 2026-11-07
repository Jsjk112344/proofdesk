# SalesDesk recording hand-off

The silent edit follows `video-plan.md` and `subtitles.srt`: **3:00**, 1920×1080,
30 fps. Open [rough-cut.mp4](rough-cut.mp4) for the captioned version or
[rough-cut-nosubs.mp4](rough-cut-nosubs.mp4) to edit captions yourself.
Submission slides: [SalesDesk-slides.pdf](SalesDesk-slides.pdf).

Plain-text read-through: [narration.txt](narration.txt).

## Narration, clean read-through

It's 6 AM. Summit Auto Group runs 24 dealerships, with 3,000 vehicles and 9,000 open leads. In this sample, 652 leads are cold. Which customer should each store call first?

SalesDesk. Sell more: your AI sales analyst. It works every lead, at every rooftop, every night.

Here's tonight's review. SalesDesk fans the work out across all 24 rooftops: six isolated workers running in parallel on Vultr. Each one checks every lead's risk and searches the inventory at its own store and nearby sister stores. This sample reuses accepted Qwen briefs.

By morning: 1,050 leads at risk, 1,007 matched to a car in stock, and 792 distinct aged units matched. That's an estimated $3.4 million in recoverable gross. Leadership sees the group. Every store manager gets a queue.

Let's open Sandy. Forty follow-ups, ranked by risk and by what's on the lot.

Maria asked about a blue 2024 RAV4 Hybrid nine days ago. Her last contact was a week ago, and the car she wanted sold. Without a fresh match, she needs another search. SalesDesk found a silver one on this lot: same model, same trim, in budget. It has sat for 74 days, with an entered daily carrying-cost assumption. It knows she has a 2017 CR-V to trade in. And Qwen drafts the text using only this car's recorded facts.

The manager reads, edits if needed, and approves Sandy in one click. Vultr prepares the drafts, CRM tasks and sister-store transfer requests. These are drafts and tasks. SalesDesk never sends customer messages.

Then close the laptop. The next review runs at 2 AM, every night, for every store, on Vultr. Tomorrow, the queue is waiting again.

Before: managers dig through leads, sold units and other stores' stock. After: they approve a ranked list. The full 24-store review ran in about two minutes.

Under the hood: a durable scheduler on a Vultr VM, a disposable Docker sandbox for every rooftop, and Qwen on Vultr Serverless Inference for under one cent a run.

Automotive is our first vertical. SalesDesk: sell more, with your AI sales analyst.

## Record and add your voice

Record this script as one clean read, with a phone or USB microphone in a quiet room.
Speak vehicle names and numbers naturally. Keep pauses between the scenes; use the
plan's scene times as a guide. Record a second take of any sentence you stumble over.
The rough cut intentionally has no audio. No voice has been synthesized.

In CapCut, DaVinci Resolve, iMovie or any editor, import `rough-cut-nosubs.mp4`, your
voiceover and `subtitles.srt`. Put the voice at **0:00**. Nudge scene boundaries, hold
frames or shorten pauses to fit your read while keeping the export at 3:00 or less.
Keep the real review footage at normal speed and retain the labelled jump cut. Align
each subtitle to the final voice, then burn captions once. The supplied captioned
rough cut is a reference; do not place a second set of subtitles over it.

For the supplied treatment use Inter SemiBold, approximately 42 px at 1080p, white,
bottom center, with a 60% dark box. `subtitles.ass` is a styling derivative of the SRT
with a 1920×1080 canvas. It avoids FFmpeg's default small-canvas font scaling.

Optional command to attach an already aligned voice track without moving the edit:

```bash
ffmpeg -i docs/video/rough-cut.mp4 -i voiceover.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k \
  -af apad -t 180 -movflags +faststart SalesDesk-final.mp4
```

## Optional Screen Studio re-takes

Use the public URL, a 1440×900 browser window and a 2× display. Keep **Sample dealer
group** visible, including inside Maria's drawer. Every screen take comes from the
actual deployed app. The script's only added DOM is its cursor; UI values are untouched. The final Group
number sweep was re-taken against the same completed review to align the cursor with
the narration; it triggered no new analysis or inference.

| Scene | Exact start state | Re-take focus |
| --- | --- | --- |
| 1, 14 s | Fresh incognito session, Group view, all 24 saved tiles ready and Run available | Keep the pointer still; gentle zoom toward the map. |
| 3, 22 s raw | Same Group view before any review in that session | Click Run at 2 s. Show real reset and six analysing tiles. Record the full run; use the honest jump cut at 0:42. Never accelerate job counters. |
| 4, 20 s | Finished Group result from that same Run click | Smooth stat-strip sweep, gross hold, then brief and tiles. Hover Qwen to disclose cached output. |
| 5, 8 s | Finished Group view with Sandy tile visible | Click Sandy, pause on its 40-item ranked queue. |
| 6, 38 s | Sandy; Maria first; no approval yet | Most valuable re-take: wanted blue car and CR-V trade, sold timeline, silver match, score breakdown, SMS then Email then SMS. Pull back for the message so the sample label and full draft stay visible. |
| 7, 17 s + 3 s export | Sandy; drawer closed; Approve all enabled | Approve once. Wait for real Ready status. Download CRM tasks, then open the actual CSV in Numbers or Excel for 3 s. |
| 8, 12 s | Schedule screen in the same session, toggle initially off | Enable, pause on 2:00 AM MT, and close the tab at 8 s. Record browser chrome if you want the close gesture visible. |

The backup CSV take shows the **byte-identical downloaded CSV in Chromium's plain-text
file viewer**, rather than a native spreadsheet. `scenes/crm-tasks.csv` is the real
40-row approved export. A Numbers/Excel re-take is optional. Headless app capture does
not show browser chrome; the schedule shot closes its page and holds the final frame
to fill the slot. Server persistence was verified by reopening, then the test schedule
was disabled. The submitted edit should show the enabled state, as captured.

## Facts pinned to the footage

- 9,000 leads reviewed; **1,050 at risk**, **1,007 best matches in stock**, **792 distinct
  aged units matched**, **$3,434,800 estimated recoverable gross** (screen: $3,434,800; narration rounds to $3.4 million).
  Gross uses listed price minus cost and can count the same unit for multiple leads.
  It is not a sales forecast. Aged-unit matching does not establish customer intent.
- Store risk counts genuinely range **12–85**; Sandy has **40**, with no queue cap.
- Recorded take: completion observed **121.290 s**;
  finished Group visible **124.177 s**. This is live sandbox analysis with
  **accepted Qwen replay**, not 25 fresh inference requests. `recorded-run.json` and
  `scene-manifest.json` identify the take and each choreography still.
- Separate full-live measurement: **25 provider responses, $0.0077789 token cost**,
  140.131 s through final result capture. Say **under one cent a run**. Compute is
  separate, and token-cost estimates are not billing receipts. The durable video
  envelope reserves $0.0502400 for those 25 calls; reservation is not actual usage.
- Maria: blue 2024 RAV4 Hybrid XLE enquiry nine days earlier, contact seven days earlier,
  original car sold six days earlier; silver S00138 at Sandy, **74 days**, **$32,900**,
  score **98**, 2017 Honda CR-V trade. The $8/day carrying cost is an entered assumption.
- Summit Auto Group, rooftops and people are fictional. Nothing is sent to customers;
  approvals create tasks, drafts and review requests.

## Rebuild

```bash
uv sync --locked
uv run playwright install chromium
uv run python -m scripts.record_demo_scenes
uv run python -m scripts.render_demo_assets
uv run python -m scripts.assemble_demo_video
```

FFmpeg must support libx264 and libass. On this workstation the assembler defaults to
`/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`; elsewhere pass `--ffmpeg /path/to/ffmpeg`.
The recorder creates a new public session and executes real work within existing
quotas. New source inputs may use bounded paid inference; never reset ledgers.
If you re-record a run, review its measured runtime and update the narration, jump-cut
card and SRT before rebuilding the cut. Raw WebM and session cookies stay ignored in
`.local/video-prep/`; the published artifacts contain neither cookies nor credentials.

## Before final export and submission

- [ ] Every spoken number matches the frame and the final run; Maria's facts still match.
- [ ] Captions match the recorded voice and have been re-timed where needed.
- [ ] Watch with sound off. The story, sample label and replay disclosure remain clear.
- [ ] Keep the honest jump-cut label; do not speed up counters or composite UI numbers.
- [ ] Export H.264 MP4 at 1920×1080, 30 fps, **3:00 or less**, with audible voice and no clipped words.
- [ ] Confirm the actual signed-in LabLab form's video length and upload constraints.
- [ ] Open the public URL and repository signed out; inspect the uploaded PDF and video.
- [ ] Upload the narrated video and `SalesDesk-slides.pdf`; complete submission by the
  owner's **Sunday November 8, 16:00 ET target**, ahead of the owner-supplied 18:00 ET deadline.
- [ ] Save the submission receipt. No submission has been made by this preparation.

The [official event page](https://lablab.ai/ai-hackathons/vultr-hackathon) requires a
recorded demo but did not publish a video-length limit in the checked page. LabLab's
[general submission guide](https://lablab.ai/delivering-your-hackathon-solution)
recommends under five minutes and allows MP4/MOV up to 300 MB; event-specific forms
prevail. The [general rubric](https://lablab.ai/hackathon-rules) also discourages videos
under three minutes. This package follows the owner's exact three-minute target.
**The signed-in event form's length limit remains unconfirmed**; check it before upload.
