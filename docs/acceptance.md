# Acceptance criteria and observed local checks

## Local execution slice — observed 2026-11-03

Executed on macOS with Colima Docker Engine 29.5.2, Linux/arm64, cgroup v2 and default
seccomp. The controller and scripts are original deterministic synthetic fixtures.
These observations do not establish model quality, Vultr deployment or every escape boundary.

| Criterion | Observed result |
| --- | --- |
| Valid document extraction | Exact expected structured JSON accepted, including 1,600-cent total |
| Exit zero with wrong output | Rejected with `artifact_schema_or_content_mismatch`, no accepted file |
| Unsafe/oversized artifacts | Live symlink, FIFO, unexpected path and size probes rejected; offline tests also reject traversal, absolute paths, hardlinks, devices and duplicate entries |
| Output quotas | stdout flood and archive flood rejected with `output_limit` |
| Endless task | External five-second deadline produced `task_deadline_exceeded`; container removed |
| CPU/RAM/process/write limits | Pre-task kernel readback matched policy; allocation probe exited nonzero, process probe hit EAGAIN, tmpfs probe hit ENOSPC, root writes failed |
| Network isolation | Only loopback observed; TCP attempts to 192.0.2.1 and 169.254.169.254 failed |
| Host files/socket | Synthetic host canary read/write attempts failed; canary hash unchanged; Docker socket unavailable |
| Credentials | Exact PATH/LANG/HOME environment allowlist verified before code; credential probe passed |
| Lifecycle | Container absence verified after every live case; valid task succeeds afterward |
| Interruption | SIGINT/SIGTERM finalize interrupted records and remove containers; subsequent task succeeds |
| Hard crash | SIGKILL leaves a pending record; explicit recovery removes abandoned container and reconciles record; subsequent task succeeds |
| Missing Docker | Deliberately missing Docker executable produces `docker_unavailable`, null exit code and no artifact, with no task execution |
| Schema | Saved records validated against JSON Schema 2020-12 in offline and live tests |

Reproduce with the commands in [README.md](../README.md). Individual records under
`.local/executions/` capture controller revision/dirty status, input/script hashes, runtime
identity and failures. The development passes used baseline commit `4bcbf91` with the feature
changes present; the committed slice can be rerun to record its own clean revision.
The complete local check commands and evidence IDs are listed in [STATUS.md](../STATUS.md).
Docker tests are opt-in; offline CI does not claim to have run them.

## Planned product criteria

The following remain future checks, not a passed test report. The corresponding local
fixture checks above cover only the narrow execution boundary, not these full product flows.

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
