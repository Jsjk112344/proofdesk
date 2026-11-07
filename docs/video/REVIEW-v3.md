# SalesDesk v3 review

Both exports are **165.000 seconds (2:45)**, 1920×1080, 30 fps, H.264, silent:
[salesdesk-v3.mp4](salesdesk-v3.mp4) · [without captions](salesdesk-v3-nosubs.mp4).
[Contact sheet](_review/v3-contact.png).

## UI changes and screenshots

All before/after screenshots below use a **1280×720 browser viewport** and are
saved at CSS resolution for direct comparison. Recording uses **1.5 device scale**.

| Screen | Change | Before | After |
|---|---|---|---|
| Group | Minimum 13 px text; smaller map; map collapses while running; compact tiles; status colour and pulse, ready check pop; headline, counters, progress and over eight tiles visible during work | [Before](_review/v3-before-group.png) | [After](_review/v3-after-group.png) |
| Sandy | Minimum 15 px trace; tighter spacing; redundant stat strip collapses with expanded trace; first follow-up readable with trace | [Before](_review/v3-before-store.png) | [After](_review/v3-after-store.png) |
| Maria | Wider compact drawer, readable type, best match first, expandable breakdown and alternatives; wanted car, timeline, score and SMS fit together | [Before](_review/v3-before-maria.png) | [After](_review/v3-after-maria.png) |

[Mid-run Group](stills/v3-run-tiles.png) and
[completed trace with first follow-up](stills/v3-run-trace-done.png) and
[1280×720 trace / Ready view](_review/v3-after-trace.png) retain native
1.5× captures from that viewport. The approved store adds its real Ready panel;
one short scroll keeps it, the trace and the full first follow-up together.
Maria requires no scroll for the primary story and SMS.

Playwright’s empty recorder padding was removed before assembly, preserving the
entire 1280×720 app frame and scaling it to 1080p. This corrects recorder canvas
size; it does not crop any platform UI. The recorder now uses native CSS video
size and whole-frame scaling directly. Native 1.5× stills need no correction.

## Re-recorded scenes

- Scene 1: whole Maria drawer for the opening story.
- Scene 6: genuine Group mid-run insert, then Sandy's actual trace transitions.
- Scene 7: whole Sandy trace and Maria's expanded match breakdown.
- Scene 8: Sandy's Qwen/brief and completed draft-count trace.
- Scene 10: whole Maria payoff and SMS; locked camera and stationary cursor.
- Scene 11: ranked queue, actual approval click and Ready downloads.
- Additional completed Group take is retained in the source manifest.

Scene 5 is the new editorial fan-out graphic: central group at 2 AM, 24 store
nodes, six active at once, lead/car/brief icons, stores 0→24 and leads 0→9,000.
The compute layer carries Vultr. A three-second real Group insert follows it.
All original story-card types remain. Chapters slide into green pills at top left;
captions stay bottom centre, with a quiet SMS hold at 1:49–2:01.

The thesis adds its separate missed-follow-up promise card, the impact cards add
“Increase your sales without adding headcount.”, and the end card leads with
“Never lose a sale again.” The exact requested tagline, URL, GitHub and sample/footer
line remain. No separate sample-label overlay is composited onto app footage.

## Observed evidence

Final public run: **127.493 seconds**, rounded to **2 min 7 sec** in card and narration;
24 stores succeeded, 25 accepted Qwen replays, no new live inference calls and **$0 new
inference usage**. Docker analysis executed live. Compute billing remains separate.
The first verification take also completed, with 25 accepted replays and no new
inference usage. No ledger was reset and no new VM was provisioned.

The public deployment matched all **85 file hashes**. Frontend build, Ruff,
formatting, Python compilation and the **114-test offline suite** passed (seven
optional checks skipped). Public browser checks passed for trace font, full first
follow-up, no horizontal overflow, full Maria story/SMS and alternatives toggle.
The recording reported no page errors. See [layout check](v3-layout-check.json),
[deployment check](v3-deployment-check.json), [recording facts](recording-facts-v3.json),
[scene manifest](scene-manifest-v3.json) and [export checks](v3-export-check.json).
No new sandbox-containment acceptance is claimed for these presentation changes.

## Owner actions

Record the voiceover from [narration-v2.txt](narration-v2.txt), align it with
[subtitles-v2.srt](subtitles-v2.srt), finish the audio/edit and watch the complete
export. Confirm the signed-in event form's upload limits, upload the final video
and slides, and **submit by Sunday November 8, 2026 at 16:00 ET**, the owner's target.
Save the submission receipt. No voice track, upload or submission is claimed here.

## Cursor and camera polish

Maria’s opening, match and SMS holds now use a locked camera. The separate expanded
match view is captured before the hold; the main drawer never opens and closes the
breakdown while the viewer reads. The cursor stays parked off the drawer text.
The mid-run Group insert starts after the pointer has settled. Approval is re-recorded
with one smooth, bounded move to the button, a genuine click and no panel-centre sweeps.
That approval/Ready pair uses a separate saved-sample session with the identical
Maria SMS; it starts no review or inference. The measured Group/trace run is unchanged.
The new title and end-card tagline is **SalesDesk: Your AI enterprise sales analyst**;
the maintained VO script and captions include “enterprise”.
