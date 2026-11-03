# Planned acceptance criteria

These are future checks, not a passed test report.

## Useful work

- One public source supports a relevant use case; source and capture date are inspectable.
- A supported demonstration executes and returns actual files, logs and check results.
- A recoverable failure is corrected within the allowed retry count.
- A saved draft uses supported facts and identifies demonstration limitations.
- Reload retrieves the same authorized user's saved work.
- Insufficient evidence, provider failure and rejected fit remain distinct outcomes.

## Boundaries

- Cross-user job/artifact reads are denied.
- Private/metadata network targets and redirect bypasses are blocked.
- A hostile page cannot authorize tools, spend, sending or publication.
- A controlled timeout is killed externally; cleanup is verified after success/failure.
- A host canary remains unchanged and a subsequent legitimate task succeeds.
- Sandboxes receive no credentials, host mounts or runtime control sockets.
- Invalid/oversized/path-traversing artifacts are rejected.
- Editing an approved package invalidates approval; duplicate requests do not resend.
- Missing inference configuration cannot fall back to a non-Vultr model provider.

Record actual commands, outputs and revision for observed checks. Clearly label fault
injection and fixture replay in demonstrations. Security claims cannot exceed observations.
