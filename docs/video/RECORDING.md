# SalesDesk v3 recording hand-off

The Maria-first cut is **2:45 (165 seconds)**, silent, H.264, 1920×1080, 30 fps.
Use [salesdesk-v3.mp4](salesdesk-v3.mp4) for the captioned review and
[salesdesk-v3-nosubs.mp4](salesdesk-v3-nosubs.mp4) for the voiceover edit.
[Review and before/after screenshots](REVIEW-v3.md) · [Contact sheet](_review/v3-contact.png) · [Plan](video-plan-v2.md) ·
[Measured facts](recording-facts-v3.json) · [Scene takes](scene-manifest-v3.json).
The previous three-minute hand-off is preserved in [RECORDING-v1.md](RECORDING-v1.md).

## Clean voiceover script

Nine days ago, Maria asked a dealership about a blue RAV4 Hybrid. Her last contact was seven days ago. Six days ago, that car sold. Meanwhile, a silver one sat on the same lot for 74 days.

Now multiply that by 24 stores. Every morning, over a thousand leads like Maria are slipping away.

Dealers don't lose these sales for lack of cars. They lose them because nobody connects the lead to the car in time. SalesDesk makes sure you never lose a sale to a missed follow-up again.

SalesDesk. Your AI sales analyst.

At 2 AM, SalesDesk starts its review. It splits the group into 24 jobs, one per store, running in parallel in isolated sandboxes on Vultr.

Let's follow one store: Sandy. First, the agent reads every open lead and flags the ones going cold: no contact in three days, or the car they wanted is gone.

Next, it searches every car on this lot and at nearby sister stores, and scores each one against the request: model, trim, budget, mileage. Cars that have sat the longest get priority.

Then Qwen, on Vultr Serverless Inference, writes the store's morning brief and three personal follow-ups, using only recorded vehicle facts.

Two minutes, seven seconds later, all 24 stores are done.

Remember Maria? Here's what the agent found: the silver RAV4 Hybrid on her own lot, a 98 out of 100 match. It knows about her CR-V trade-in. Her message is already written.

At 7 AM, Sandy's manager opens a ranked queue of 40 follow-ups and approves them in one click. Each salesperson gets their tasks and drafts.

Across the group, that's over a thousand customers matched to a car in stock, and an estimated $3.4 million in gross back in play.

It all runs on Vultr: the scheduler and sandboxes on a Vultr VM, and Qwen on Vultr Serverless Inference, with validated drafts for manager review.

SalesDesk. Every lead, every store, every morning. Never lose a sale again.

## Lay in the voice and re-time captions

Record [narration-v2.txt](narration-v2.txt) as one clean read, with pauses at the scene
boundaries in the plan. Speak the measured time skip naturally. Leave **1:49–2:01**
quiet for Maria's full SMS; its last six seconds must remain readable without captions.

Import `salesdesk-v3-nosubs.mp4`, your recording and `subtitles-v2.srt` into your editor.
Start VO at 0:00, align each caption to the actual spoken words, then adjust holds or
scene boundaries to fit the read. Keep the result within **2:40–2:50**, targeting 2:45.
Use Inter SemiBold at 42 px, white on a 60% dark box. Keep captions bottom centre; chapter labels are top left. Never burn a second caption track over the captioned cut.

If the voice already matches the edit:

```bash
ffmpeg -i docs/video/salesdesk-v3.mp4 -i voiceover.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k \
  -af apad -t 165 -movflags +faststart SalesDesk-final.mp4
```

No music, sound effects or synthesized voice are included. No clearly licensed audio
was selected. Add a documented royalty-free bed at −26 dB only if desired, duck it
under VO, and retain the licence with the final project.

## Recorded facts and narration corrections

- Final public run: **127.493 seconds**, rounded to **2 min 7 sec** on the visible skip.
- Group: **1,050 at risk**, **1,007 matched in stock**, **792 distinct aged units matched**,
  **$3,434,800 estimated recoverable gross**. The spoken $3.4 million is rounded.
- Sandy: **375 open leads**, **40 at risk / 25 cold**, **117 local / 1,638 sister-store cars**,
  **70,200 scored lead/car pairs**, top store score **100**, **40 total follow-ups**.
- Qwen supplied **three** Sandy follow-ups, including Maria's. Remaining drafts keep
  their existing Template labels. The VO no longer says Qwen wrote every follow-up.
- Maria: enquiry nine days earlier, last contact seven days earlier, original car sold
  six days earlier; silver 2024 Toyota RAV4 Hybrid XLE, **74 days**, **98** match,
  **2017 Honda CR-V** trade. “After one call” was removed because call count is unknown.
- Recorded run: **25 accepted Qwen replays**, **zero fresh inference responses**, **$0 new
  inference usage**. Docker analysis executed live. The previous separate fresh-inference
  measurement remains in `measured-run.json`; it does not describe this take.
  The “under a cent a night” claim was removed, since compute is separate.
- Gross is an estimate from listed vehicle figures, can reuse one unit for multiple
  leads and is not a sales forecast. These notes stay out of VO and captions.

## Footage and visual integrity

All app scenes were re-recorded from the public HTTPS platform at 1280×720 with
1.5× device scale and 1920×1080 video output. Whole screens replace v2 detail crops; Maria has a slow 1.06× push-in and pull-back.
Playwright video uses the native CSS viewport and is scaled as a whole to 1080p;
the retained takes had empty recorder padding removed, with the entire app frame preserved.
Native sample labels and replay provenance remain in the app. No extra frame label
is added. The fan-out is a separate motion graphic using the v2 verified figures:
24 stores, six concurrent jobs and 9,000 open leads. It is followed by three seconds
of genuine Group mid-run footage before Sandy's trace.

Maria's wanted car, timeline, match 98 and full SMS fit in the drawer together.
Match breakdown expands for scene 7; alternatives remain available on demand.
Scenes 1, 6–8, 10 and 11 use new app footage; scene 5 is the new explainer, and the
mid-run Group insert is also newly recorded. All story/impact/architecture cards
are retained and updated to match v3 messaging.

## Rebuild

```bash
uv sync --locked
uv run playwright install chromium
uv run python -m scripts.record_demo_v3
uv run python -m scripts.record_demo_v3 --ready-only
# Reconcile the measured time and all facts with video-plan-v2.md / subtitles-v2.srt.
uv run python -m scripts.render_video_v3
uv run python -m scripts.render_fanout_v3
uv run python -m scripts.assemble_video_v3
```

These commands reuse the existing recorder, asset style and assembler helpers.
FFmpeg needs libx264, libass and drawtext. This workstation uses
`/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`. Recording executes actual session work under
existing quotas; never reset ledgers. The detail-only pass uses the session saved by
the preceding recorder and makes no new inference calls.

## Pre-export and submission checklist

- [ ] Figures match the final recorded screen, including the measured time skip.
- [ ] Native sample labels remain visible; no extra frame overlay.
- [ ] End footer reads “Sample dealer group · SalesDesk drafts; people send.”
- [ ] Watch with sound off: Maria, scale, agent work, approval and payoff make sense.
- [ ] Full SMS is readable for at least six seconds without overlapping captions.
- [ ] Voice and captions align; Act 2 captions clear chapter labels.
- [ ] Export is 1920×1080 / 30 fps, **2:45 ±5 seconds**; audio is clear and unclipped.
- [ ] **Confirm the actual signed-in LabLab form's video length and upload limit.**
- [ ] Verify public app and GitHub access signed out, then upload video and slides.
- [ ] Submit by the owner's **Sunday Nov 8, 2026, 16:00 ET target**, ahead of the
  owner-supplied 18:00 ET deadline. Save the receipt.

The [official event page](https://lablab.ai/ai-hackathons/vultr-hackathon), rechecked
Nov 6 ET, requires a recorded demo but does not publish a video length limit.
The general rule/guide pages failed to load in this check. The previous hand-off
records a general under-five-minute recommendation and a rubric discouraging videos
under three minutes. **The signed-in event form limit remains unconfirmed.** This
cut follows the owner's approved 2:45 direction. No submission has been made.
