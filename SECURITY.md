# Security

## Current status

The HTTP application still exposes only a health endpoint and development screen.
A separate local CLI executes deterministic synthetic tasks in Docker. It has no
authentication, models, research tools, public execution endpoint or send integration.
Observed local checks are recorded in [STATUS.md](STATUS.md). This is not a production
deployment, microVM boundary, or proof of protection against every container escape.

## Implemented local boundaries

- The controller owns task selection, limits, expected results, validation and records.
  The CLI offers fixed fixtures/probes, not arbitrary public code execution. Every task
  uses a fresh named container and a digest-pinned official Python image, without pulls
  at dispatch. Images declaring volumes are refused.
- UID/GID 65532, all Linux capabilities dropped, `no-new-privileges`, Docker's default
  seccomp, private PID/IPC/cgroup namespaces, read-only root filesystem, no privileged
  mode, devices, bind mounts, volumes, Docker socket, credentials or host networking.
  The trusted Docker daemon and controller are privileged parts of the boundary.
- `--network=none`: loopback only. There is no browser, URL fetch or redirect handling
  yet. This is not a general network proxy or SSRF implementation.
- Processes run through `env -i` with only fixed PATH, LANG and nonexistent HOME.
  No `.env`, controller environment, API key or cloud secret is passed to task processes.
- Externally configured limits: 0.5 CPU bandwidth, 128 MiB RAM with no swap, 32 processes,
  8 MiB `/work`, 1 MiB `/tmp`, 1 MiB shared memory, 1 MiB maximum regular-file size,
  64 file descriptors and no core dumps. Writable task storage is tmpfs; root writes are
  denied. tmpfs uses `noexec,nosuid,nodev`; Python can still interpret source files.
- Before accepting task code, the runner requires Linux/cgroup v2/seccomp, inspects the
  container policy, and verifies UID, environment, CPU/memory/swap/PID kernel values and
  tmpfs capacities inside the container. An unsupported limit fails closed.
- A controller monotonic deadline covers task dispatch and artifact collection: five
  seconds. At expiry the Docker client is killed and the finalizer forcibly removes the
  whole container, including descendants. Setup Docker commands have 15-second bounds;
  cleanup uses up to two 10-second calls. Termination depends on a responsive daemon.
- stdout/stderr are bounded together at 16 KiB; archive transport is bounded at 64 KiB.
  Docker logging is disabled so task output cannot create unbounded daemon log files.
  A limit breach rejects the task and initiates removal, never truncation-as-success.
- Artifact tar streams are never extracted onto the host. The only accepted file path
  is `out/result.json`, a nonempty regular file of at most 16 KiB. Other paths, symlinks,
  hardlinks, devices, FIFOs, sparse files, duplicates and malformed data are rejected.
  JSON rejects duplicate keys/nonfinite constants and must exactly match the controller's
  expected structure, types and values. Exit zero alone never means success.
- Only validated bytes are written to the fixed host filename `result.json`. The archive
  is untrusted and collection is not an atomic filesystem snapshot: descendants may
  still run while tar collects. Validation and saved-byte identity are the boundary.
- Serial execution uses a checkout lock. SIGINT/SIGTERM finalize records and cleanup;
  repeated signals are ignored during finalization. Success requires verified container
  absence. Explicit `cleanup` reconciles SIGKILL/crash leftovers using a checkout-specific
  label, never a global Docker prune. New tasks refuse existing labelled containers.

## Local limitations

The controller, checkout, Docker client/daemon, pinned image and host kernel are trusted.
Ordinary Docker shares the daemon host kernel. The macOS observations used a Colima Linux
VM and do not establish equivalent behavior on Vultr or another runtime. CPU quota was
read back from cgroup v2; this is not a performance benchmark. Synthetic network and file
probes are narrow observations, not exhaustive escape testing.

SIGKILL, power loss or an unavailable daemon can prevent immediate cleanup. The idle
container process sleeps for 60 seconds as a convenience, not a security watchdog.
Restore the same Docker daemon/context and run recovery; retain the checkout path because
labels derive from it. Recovery is not a background service. Unexpected internal failures save a stable
reason; bounded diagnostics can be inspected locally. Logs and records remain untrusted
data and must not be rendered as HTML or executed. Local record retention has no total
quota yet; the operator owns `.local/` disk usage. No private inputs are supported.

## Future trust boundaries

- Controller: credentials, model requests, user/task authorization, budgets and persistence.
- Runner: restricted execution service with approved images and bounded task parameters.
- Task environments: disposable, unprivileged, no credentials or host/socket mounts.
- Browser network: restricted public egress, DNS/IP and redirect checks, no access to
  private networks or cloud metadata. Browser contexts alone are not the isolation boundary.
- Code network: disabled unless a specifically approved operation needs a constrained path.
- Artifacts: validate paths, symlinks, size, type and content before copying or rendering.
  Generated HTML must not execute in the authenticated application's origin.

CPU, memory, process count, wall time and output quotas must be enforced externally to
the model. A finalizer and crash-recovery cleanup must remove task environments.
Model output never authorizes spending, privilege expansion or outbound communication.
Approval must bind to exact message/artifact versions. Changes invalidate that approval.

Isolation does not establish model-provider data privacy. Minimize what is transmitted
and document retention and inference data handling before accepting private inputs.

## Reporting

Use GitHub private vulnerability reporting for this repository when enabled. Avoid
posting credentials, exploit payloads containing private data, or private records in
public issues. If private reporting is unavailable, open an issue requesting a private
contact route without vulnerability details.
