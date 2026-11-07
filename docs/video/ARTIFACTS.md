# SalesDesk video artifacts

## Current: v2

- [Captioned 2:45 cut](salesdesk-v2.mp4) and [clean cut](salesdesk-v2-nosubs.mp4).
- [Fourteen-scene contact sheet](_review/v2-contact.png).
- [Recording hand-off](RECORDING.md), [clean VO](narration-v2.txt), [captions](subtitles-v2.srt).
- [Verified facts](recording-facts-v2.json), [source take manifest](scene-manifest-v2.json), [export checks](v2-export-check.json).
- Animated HTML cards in `card-v2-*.html`; rendered MP4s in `cards-v2/`.
- Public scene takes in `scenes/v2-*.mp4`, 2× stills in `stills/v2-*.png`.
- Both exports are silent; owner records VO, finishes the edit and submits.

## Previous 3:00 kit

# SalesDesk video files

This package follows the three-minute [video plan](video-plan.md).
Start with [RECORDING.md](RECORDING.md) for the clean narration and editing instructions.

| Asset | Files |
| --- | --- |
| Captioned silent rough cut | [rough-cut.mp4](rough-cut.mp4) |
| Clean silent rough cut | [rough-cut-nosubs.mp4](rough-cut-nosubs.mp4) |
| Verified video properties | [rough-cut-check.json](rough-cut-check.json) |
| Submission slide deck | [SalesDesk-slides.pdf](SalesDesk-slides.pdf), [HTML source](SalesDesk-slides.html), [Markdown contents](../slides.md) |
| Clean narration | [narration.txt](narration.txt), [RECORDING.md](RECORDING.md) |
| Captions | [subtitles.srt](subtitles.srt), [styled ASS derivative](subtitles.ass) |
| Shot timing and still index | [scene-manifest.json](scene-manifest.json) |
| Recorded run | [recorded-run.json](recorded-run.json) |
| Fully live inference measurement | [measured-run.json](measured-run.json), [ledger audit](inference-accounting.json) |
| Fonts and license | `fonts/InterVariable.woff2`, `fonts/InterVariable-Italic.woff2`, `fonts/Inter-SemiBold.ttf`, `fonts/Inter-LICENSE.txt` |

## Cards

All are 1920×1080 PNGs, rendered from HTML by Playwright at deviceScaleFactor 1:

- [Transparent title](cards/01-title.png) and [blurred Group composite](cards/01-title-composited.png).
- [Honest jump cut](cards/02-jumpcut.png), with the recorded run's measured time.
- [Before / after](cards/03-before-after.png).
- [Architecture](cards/04-architecture.png), plus `cards/04-architecture-build-1.png`
  through `cards/04-architecture-build-7.png` for the progressive diagram. The edit reveals the first six steps at one per second,
  then holds the full diagram for eight seconds.
- [End card](cards/05-end.png).

## Screen scenes

All are real app output from the public HTTPS URL, 1440×900, H.264, 30 fps:

| File | Length | Content |
| --- | ---: | --- |
| [scene1.mp4](scenes/scene1.mp4) | 14 s | Fresh saved Group view |
| [scene3.mp4](scenes/scene3.mp4) | 22 s | Real Run click, reset and six analysing tiles |
| [scene4.mp4](scenes/scene4.mp4) | 20 s | Finished Group; cursor follows narrated numbers |
| [scene5.mp4](scenes/scene5.mp4) | 8 s | Open Sandy |
| [scene6.mp4](scenes/scene6.mp4) | 38 s | Maria, timeline, match, trade, SMS and Email |
| [scene7.mp4](scenes/scene7.mp4) | 17 s | Approve Sandy, real Ready and download |
| [scene7-csv.mp4](scenes/scene7-csv.mp4) | 3 s | Byte-identical exported CSV, plain-text file viewer |
| [scene8.mp4](scenes/scene8.mp4) | 12 s | Enable schedule, close page, hold real final frame |

The final edit uses scene 7 for 14 seconds, the CSV preview at 2:06–2:09, then the
remaining three seconds of real Ready footage before Schedule at 2:12.
[crm-tasks.csv](scenes/crm-tasks.csv) is the actual approved 40-row synthetic export.

There are **33 crisp 2880×1800 stills** in `stills/`, one per choreography beat.
Their exact filenames and capture times are in `scene-manifest.json`.

## Reproduction

- [record_demo_scenes.py](../../scripts/record_demo_scenes.py): real public journey,
  smooth visible cursor, stills, source video and verification.
- [render_demo_assets.py](../../scripts/render_demo_assets.py): PNG cards and PDF deck.
- [assemble_demo_video.py](../../scripts/assemble_demo_video.py): exact 180-second edit,
  zooms, crossfades, fades, caption styling and ffprobe checks.

Raw WebM recordings, session cookies and operator scratch files stay under ignored
`.local/video-prep/`. Video and slide files are ready for the owner's voiceover,
final edit, upload and submission; no submission receipt exists.
