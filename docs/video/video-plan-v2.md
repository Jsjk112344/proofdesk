# SalesDesk demo video v2 (2:45)

Approved direction (Nov 7):

- **Open on Maria's story**, then scale it up to the whole group.
- **Length about 2:45.**
- **Disclaimers off the voiceover and captions.** "Sample dealer group" stays visible on screen, plus one small line on the end card.
- **The middle is an agent trace walkthrough.** The agent's work is followed step by step for one store (Sandy), and Maria comes back as the payoff.

Thesis (everything serves this line): **Dealers don't lose sales for lack of cars. They lose them because nobody connects the lead to the car in time.**

Subtitles: `subtitles-v2.srt`, timed to this plan. Pace is about 150 words per minute.

## Visual rules (apply to every scene)

- **One idea per shot.** Each UI shot is zoomed to at least 1.4× on one element: a number, a card or a sentence. Full-UI wide shots last no more than 2 s, except the map in scene 2.
- **No text walls.** No raw CSV, no lists of more than 3 items, no paragraphs on screen. If the viewer has to read it, it must be large and on screen long enough to read (about 3 words per second).
- **Kinetic text cards.** Use these for the story beats: Inter Bold, 1–7 words, centered, on the dark green brand background. Animate with fade + 8 px rise, 250 ms. Numbers count up.
- **Chapter lower-thirds** in Act 2: "Step 1 · Fan out", "Step 2 · Find who's slipping", "Step 3 · Find the right car", "Step 4 · Write the brief". Bottom-left, slide in, hold for the whole chapter.
- **Audio.** A quiet modern instrumental bed at −26 dB, ducked under the voiceover. A soft whoosh on card transitions. One subtle "ding" when Maria's 98 match appears.
- **Cursor.** Smooth and purposeful, and only moving when something is about to be clicked or pointed at.
- **Captions.** Burn in `subtitles-v2.srt`: white semi-bold text, 60% dark box, bottom center, 42 px. Move them up to avoid lower-thirds in Act 2.

## Timeline

| # | Time | Len | Beat | Visual | Transition in |
|---|---|---|---|---|---|
| **ACT 1: THE PROBLEM** |||||
| 1 | 0:00–0:15 | 15 s | Maria's story | Kinetic text + tight stills from her drawer | Fade from black |
| 2 | 0:15–0:23 | 8 s | Scale it up | Map pull-back, big count-up "1,050 leads at risk" | Zoom-out |
| 3 | 0:23–0:31 | 8 s | Thesis | Two-line kinetic card | Crossfade |
| 4 | 0:31–0:38 | 7 s | Title | Logo + "Your AI sales analyst" over the blurred map | Blur in |
| **ACT 2: THE AGENT AT WORK** |||||
| 5 | 0:38–0:50 | 12 s | Step 1 · Fan out | Click Run; 24 tiles go queued → analysing on Vultr | Hard cut |
| 6 | 0:50–1:02 | 12 s | Step 2 · Find who's slipping | Sandy's trace: leads read → slipping count | Zoom into Sandy |
| 7 | 1:02–1:17 | 15 s | Step 3 · Find the right car | Sandy's trace: cars searched here + sister stores → match score bars | Hard cut |
| 8 | 1:17–1:28 | 11 s | Step 4 · Write the brief | Sandy's trace: Qwen step → brief headline → message count | Hard cut |
| 9 | 1:28–1:32 | 4 s | Time skip | Card: "2 min 18 sec later · all 24 stores done" (real run, shortened) | Quick fade |
| 10 | 1:32–1:58 | 26 s | **Payoff: Maria** | Her drawer: best match 98 → trade-in → full SMS held readable for 6 s | Push-in |
| **ACT 3: THE OUTCOME** |||||
| 11 | 1:58–2:10 | 12 s | Approve | Sandy queue → Approve all → Ready | Hard cut |
| 12 | 2:10–2:22 | 12 s | Group impact | Two big count-up cards: 1,007 matched · $3.4M recoverable gross | Crossfade |
| 13 | 2:22–2:34 | 12 s | Built on Vultr | 4-box animated diagram | Crossfade |
| 14 | 2:34–2:45 | 11 s | Close | End card | Fade to black |

Time split: problem 38 s · agent at work 80 s · outcome and close 47 s.

## Scene detail and voiceover

### 1. Maria's story (0:00–0:15)
- **Visual:** black, then card "Nine days ago…". Next comes a tight still of "Wanted a blue 2024 Toyota RAV4 Hybrid XLE" (2×), then the timeline with the orange "Original vehicle sold · 6 days ago" dot pulsing. Last is the silver RAV4 card with **74 days on lot** highlighted.
- **VO:** "Nine days ago, Maria asked a dealership about a blue RAV4 Hybrid. Her last contact was seven days ago. Six days ago, that car sold. Meanwhile, a silver one sat on the same lot for 74 days."

### 2. Scale it up (0:15–0:23)
- **Visual:** pull back from a single dot on the map to all 24 store markers. A big centered count-up to **1,050** with the label "leads at risk this morning".
- **VO:** "Now multiply that by 24 stores. Every morning, over a thousand leads like Maria are slipping away."

### 3. Thesis (0:23–0:31)
- **Card, line by line:** "Dealers don't lose sales for lack of cars." / "They lose them because nobody connects the lead to the car in time."
- **VO:** the same two sentences.

### 4. Title (0:31–0:38)
- **Visual:** SalesDesk logo, then "Your AI sales analyst", then the small line "Connects every lead to the right car. Every night."
- **VO:** "SalesDesk is an AI sales analyst that makes that connection, every night."

### 5. Step 1 · Fan out (0:38–0:50)
- **Visual:** Group view. The cursor clicks **Run tonight's review now**, then a punch-in on the tile grid as tiles flip to "Analysing on Vultr", six at a time. The counter shows "6 parallel workers on Vultr".
- **VO:** "At 2 AM, SalesDesk starts its review. It splits the group into 24 jobs, one per store, running in parallel in isolated sandboxes on Vultr."

### 6. Step 2 · Find who's slipping (0:50–1:02)
- **Visual:** zoom into the Sandy tile, then Sandy's agent trace (see the session prompt, step 1). The step "Read N open leads" fills, then "Flagged 40 at risk · 25 gone cold" with the count-up.
- **VO:** "Let's follow one store: Sandy. First, the agent reads every open lead and flags the ones going cold: no contact in three days, or the car they wanted is gone."

### 7. Step 3 · Find the right car (1:02–1:17)
- **Visual:** the trace step "Searched N cars here + N at sister stores" fills. Cut to a match breakdown (score bars animating: model, trim, budget, mileage, aged-inventory boost).
- **VO:** "Next, it searches every car on this lot and at nearby sister stores, and scores each one against the request: model, trim, budget, mileage. Cars that have sat the longest get priority."

### 8. Step 4 · Write the brief (1:17–1:28)
- **Visual:** the trace step "Qwen on Vultr Inference" fills. Then the store brief headline in large type, then "40 follow-ups drafted".
- **VO:** "Then Qwen, on Vultr Serverless Inference, writes the store's morning brief and three personal follow-ups, using only recorded vehicle facts."

### 9. Time skip (1:28–1:32)
- **Card:** "2 min 18 sec later" (large), with "All 24 stores reviewed on Vultr" under it. The footage is real and the shortening is visible.
- **VO:** "Two minutes, eighteen seconds later, all 24 stores are done."

### 10. Payoff: Maria (1:32–1:58)
- **Visual:** a push-in on Maria's card in the Sandy queue, then the drawer opens.
  - 1:34: zoom on the best match, with **98** counting up and the ding.
  - 1:42: highlight "Trade-in · 2017 Honda CR-V".
  - 1:46: zoom to the SMS, large and fully readable.
  - 1:46–1:58: hold on the SMS with no captions or voiceover so the viewer reads it.
- **VO:** "Remember Maria? Here's what the agent found: the silver RAV4 Hybrid on her own lot, a 98 out of 100 match. It knows about her CR-V trade-in, and her message is already written."

### 11. Approve (1:58–2:10)
- **Visual:** close the drawer, then a quick scroll of the ranked queue (3 cards). Click **Approve all for Sandy**. Zoom on the green **Ready** pill with its Follow-ups / CRM tasks / Transfers buttons. No CSV.
- **VO:** "At 7 AM, Sandy's manager opens a ranked queue of 40 follow-ups and approves them in one click. Each salesperson gets their tasks and drafts."

### 12. Group impact (2:10–2:22)
- **Visual:** two kinetic number cards, back to back. **1,007** "customers matched to a car in stock", then **$3.4M** "estimated gross back in play".
- **VO:** "Across the group, that's over a thousand customers matched to a car in stock, and an estimated $3.4 million in gross back in play."

### 13. Built on Vultr (2:22–2:34)
- **Diagram (4 boxes, building left to right):** Nightly scheduler (Vultr VM) → 24 sandboxed store jobs (Docker, 6 parallel) → Qwen (Vultr Serverless Inference) → Manager approval.
- **VO:** "It all runs on Vultr: the scheduler and sandboxes on a Vultr VM, and Qwen on Vultr Serverless Inference, with validated drafts for manager review."

### 14. Close (2:34–2:45)
- **End card:** logo, "Every lead. Every store. Every morning.", URL, GitHub. Small grey footer: "Sample dealer group · SalesDesk drafts; people send."
- **VO:** "SalesDesk. Every lead, every store, every morning. Sell more, with your AI sales analyst."

## Facts to verify against the recording before export

- **Maria:** last salesperson contact 7 days ago (no call-count claim); original car sold 6 days ago; silver RAV4 Hybrid XLE, 74 days on lot, match 98; 2017 CR-V trade-in.
- **Group:** 1,050 at risk ("over a thousand"); 1,007 matched; $3,434,800 recoverable gross ("$3.4M").
- **Sandy:** 40 at risk, 25 cold, plus the trace counts (leads read, cars searched here and at sister stores).
- **Run:** recorded public run: 138.317 seconds. 25 accepted Qwen replays, zero new inference calls and $0 new inference cost; compute is separate. Scene 13 makes no cost claim.

## Verified v2 corrections

The public run and exact messages are in `recording-facts-v2.json`. Sandy reads 375
open leads, flags 40 at risk / 25 cold, searches 117 local cars and 1,638 nearby
sister-store cars, and scores 70,200 lead/car pairs. Top store score is 100; Maria's
best match is 98. Qwen supplied three follow-ups; the full queue contains 40 drafts.
Analysis steps share one sandbox pass and complete together after validation.
The public take preserves the saved-response provenance badge. The narrator does
not claim every draft is Qwen-authored or that compute is included in inference cost.
The source has a last-contact timestamp, not a complete call history.
