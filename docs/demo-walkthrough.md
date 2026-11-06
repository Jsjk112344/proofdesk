# Demo walkthrough: one complete experiment

Audience: a sales manager and a judge. Length: about four minutes of clicking. Everything
below exists in the deployed product; recording of the video is pending (not produced).

**Opening question.** "Did these e-mails create additional purchases, and what should we
test next?"

1. **Open the workspace.** The overview leads with that question, the source dataset card
   (publisher, description and catalog links, the three original arms with customers, visits,
   purchases and spend, validation checks, rights note) and the action queue summary. Point
   out that raw rows are never shown: the product serves aggregates and the sandbox does the
   computation.
2. **Save an analysis plan.** "New analysis plan": the comparison is fixed to original arms
   (Mens E-Mail versus No E-Mail), the third arm stays in the overview, the bootstrap seed and
   resamples are recorded, and the plan is saved with a hash. Mention that this is a
   retrospective re-analysis of a known benchmark, saved for reproducibility, not a
   preregistration.
3. **Run the analysis on the server.** Click "Run analysis now". The job appears as scheduled,
   the server's scheduler claims it under a lease and a worker runs the fixed analysis program in
   the disposable Docker sandbox. The page refreshes itself; closing the tab would not stop
   the job. Open "Scheduled work" to show the job, its attempts and events.
4. **Read the result.** Results tab: purchase rate per arm with Wilson whiskers (1.25% of
   21,307 versus 0.57% of 21,306), the difference with its Newcombe interval (+0.68 points,
   95% CI +0.50 to +0.86), visits, spend per assigned customer and the bootstrap interval for
   incremental historical spend (+$0.77 per customer, interval shown). Every card carries the
   metric id, definition, denominator and interval method; the provenance panel lists the
   artifact, execution, program, input and plan hashes and "reconciliation matched". Run it
   again to show the identical artifact hash.
5. **Interpretation.** The reading is labelled "Analyst: Rule-based" (or "Analyst: Live" once
   authorized and successful). It states what the interval position means, alternative
   explanations, unknowns and what the result does not establish (new copy, present-day
   audiences, individual customers, B2B follow-ups, SalesDesk revenue).
6. **Next move.** The proposed repeat experiment with a current, consenting audience and a
   random holdout is editable; saving creates version 2 and clears any older approval. The
   scenario assumptions (audience size, margin, campaign cost) are empty until entered and
   are labelled "entered, not measured"; with all three present a projected contribution and
   ROI appear with the transfer assumption disclosed. Sample-size inputs are explicit too.
7. **Task, approval, schedule.** Create a task for the sales manager, approve proposal v2
   (binds to the proposal and artifact hashes; an approval naming an older version is refused),
   then "Prepare packet now" or set a due time. Close the browser; the worker prepares the
   packet when due, with no model call. Return: the task reads "Ready for review" with the
   packet summary (readiness checks, external prerequisites such as the unavailable 2008 e-mail
   text, and what is not claimed) and a Markdown download.
8. **Review.** Enter the completion evidence and mark the review complete. The action queue
   shows the completed task and both jobs with attempts. Show one real failure path if time
   allows: an interrupted worker requeued once (events list), or a stale approval refused.

**What the demo does not claim.** No campaign was launched, no new responses or sales were
obtained, historical incremental revenue is not SalesDesk revenue, and the rule-based reading
is not a live AI result. The Prospects route remains available as the supporting journey.
