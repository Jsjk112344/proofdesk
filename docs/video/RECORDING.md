# SalesDesk v2 recording hand-off

The Maria-first cut is **2:45 (165 seconds)**, silent, H.264, 1920×1080, 30 fps.
Use [salesdesk-v2.mp4](salesdesk-v2.mp4) for the captioned review and
[salesdesk-v2-nosubs.mp4](salesdesk-v2-nosubs.mp4) for the voiceover edit.
[Contact sheet](_review/v2-contact.png) · [Plan](video-plan-v2.md) ·
[Measured facts](recording-facts-v2.json) · [Scene takes](scene-manifest-v2.json).
The previous three-minute hand-off is preserved in [RECORDING-v1.md](RECORDING-v1.md).

## Clean voiceover script

Nine days ago, Maria asked a dealership about a blue RAV4 Hybrid. Her last contact was seven days ago. Six days ago, that car sold. Meanwhile, a silver one sat on the same lot for 74 days.

Now multiply that by 24 stores. Every morning, over a thousand leads like Maria are slipping away.

Dealers don't lose these sales for lack of cars. They lose them because nobody connects the lead to the car in time.

SalesDesk is an AI sales analyst that makes that connection, every night.

At 2 AM, SalesDesk starts its review. It splits the group into 24 jobs, one per store, running in parallel in isolated sandboxes on Vultr.

Let's follow one store: Sandy. First, the agent reads every open lead and flags the ones going cold: no contact in three days, or the car they wanted is gone.

Next, it searches every car on this lot and at nearby sister stores, and scores each one against the request: model, trim, budget, mileage. Cars that have sat the longest get priority.

Then Qwen, on Vultr Serverless Inference, writes the store's morning brief and three personal follow-ups, using only recorded vehicle facts.

Two minutes, five seconds later, all 24 stores are done.

Remember Maria? Here's what the agent found: the silver RAV4 Hybrid on her own lot, a 98 out of 100 match. It knows about her CR-V trade-in. Her message is already written.

At 7 AM, Sandy's manager opens a ranked queue of 40 follow-ups and approves them in one click. Each salesperson gets their tasks and drafts.

Across the group, that's over a thousand customers matched to a car in stock, and an estimated $3.4 million in gross back in play.

It all runs on Vultr: the scheduler and sandboxes on a Vultr VM, and Qwen on Vultr Serverless Inference, with validated drafts for manager review.

SalesDesk. Every lead, every store, every morning. Sell more, with your AI sales analyst.

## Lay in the voice and re-time captions

Record [narration-v2.txt](narration-v2.txt) as one clean read, with pauses at the scene
boundaries in the plan. Speak the measured time skip naturally. Leave **1:46–1:58**
quiet for Maria's full SMS; its last six seconds must remain readable without captions.

Import `salesdesk-v2-nosubs.mp4`, your recording and `subtitles-v2.srt` into your editor.
Start VO at 0:00, align each caption to the actual spoken words, then adjust holds or
scene boundaries to fit the read. Keep the result within **2:40–2:50**, targeting 2:45.
Use Inter SemiBold at 42 px, white on a 60% dark box. Raise captions during Act 2 so
they clear the chapter labels. Never burn a second caption track over the captioned cut.

If the voice already matches the edit:

```bash
ffmpeg -i docs/video/salesdesk-v2.mp4 -i voiceover.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k \
  -af apad -t 165 -movflags +faststart SalesDesk-final.mp4
```

No music, sound effects or synthesized voice are included. No clearly licensed audio
was selected. Add a documented royalty-free bed at −26 dB only if desired, duck it
under VO, and retain the licence with the final project.

## Recorded facts and narration corrections

- Final public run: **124.758 seconds**, rounded to **2 min 5 sec** on the visible skip.
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

All product pixels come from the deployed public URL. Source viewport: 1440×900,
2× stills, smooth injected cursor only. No product text, counters, numbers or progress
were injected. Trace counts come from Sandy's leased child and reconciled sandbox
output. Analysis rows complete together because they share one sandbox pass.
The final release keeps pending inference labelled Pending and preserves replay badges.

Detail edits crop the real app and retain its actual sample badge in the edit border.
No generated number is placed onto the UI. Maria's real score stays 98; it is not
artificially counted up. Kinetic number cards count up separately from UI footage.
Crisp 2× stills supply the tight wanted-car, timeline, match, score and SMS holds.
Ready and Maria detail retakes use the same completed session after approval, with
unchanged message content and no further inference. The approval click itself is real.

## Optional Screen Studio retakes

| Scene | Start state | Useful improvement |
| --- | --- | --- |
| 5 | Fresh public Group session, Run available | Smooth button-to-six-tiles camera move. Record the entire real run; measure it again. |
| 6–8 | Click Sandy while its child job runs | Follow the actual trace transitions and focus each pair of rows. Never slow the job or manufacture progress. |
| 10 | Completed Sandy review, Maria's drawer open | Smooth push-in from 98 to trade-in to the full SMS. Keep the cursor off the text and preserve the sample badge. |
| 11 | Same review, unapproved queue | Collapse Agent trace, approve once, then pan from real Ready status to downloads. No CSV shot. |

Retakes are optional. Any new run requires rechecking figures, wall time, provenance
and the time-skip card. Source clips and 2× stills are committed under `scenes/v2-*`
and `stills/v2-*`; raw browser recordings and session cookies remain ignored.

## Rebuild

```bash
uv sync --locked
uv run playwright install chromium
uv run python -m scripts.record_demo_v2
uv run python -m scripts.record_demo_v2 --ready-only
# Reconcile the measured time and all facts with video-plan-v2.md / subtitles-v2.srt.
uv run python -m scripts.render_video_v2
uv run python -m scripts.assemble_video_v2
```

These commands reuse the existing recorder, asset style and assembler helpers.
FFmpeg needs libx264, libass and drawtext. This workstation uses
`/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`. Recording executes actual session work under
existing quotas; never reset ledgers. The detail-only pass uses the session saved by
the preceding recorder and makes no new inference calls.

## Pre-export and submission checklist

- [ ] Figures match the final recorded screen, including the measured time skip.
- [ ] No disclaimers in voiceover or captions; app sample badge remains visible.
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
