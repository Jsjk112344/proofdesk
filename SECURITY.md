# Security

## Current status

The scaffold exposes only a local health endpoint and development screen. It has no
authentication, agent runner, research tools, public execution endpoint or send integration.
It is not a production deployment or a verified sandbox.

## Planned trust boundaries

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
