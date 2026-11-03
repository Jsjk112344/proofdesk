# Vultr deployment plan

No resources are provisioned. No production deployment configuration is supplied yet.

The local CLI uses the official Python 3.12 slim Bookworm image pinned in
[task-image.txt](task-image.txt). Pull it explicitly with
`docker pull "$(cat infra/task-image.txt)"` from the repository root. There is no custom
image build and no private application image reuse. Execution uses `--pull=never`.
The controller verifies cgroup v2, seccomp, resource settings and tmpfs capacities before
sending task code. Tested locally on Linux/arm64 through Colima; other runtimes must pass
the same checks. See [local commands](../README.md) and [security limits](../SECURITY.md).
Image refreshes require deliberate digest changes and rerunning the execution tests.

Proposed starting topology: one control VM for web/API/controller/state and one runner VM
for disposable task environments, with one active task initially. Measure resource needs
before selecting region and instance sizes. Use Vultr Serverless Inference for agent calls.

Before provisioning, record current compute/storage/inference prices, confirmed credits,
maximum authorized spend, usage caps, judging availability and cleanup ownership privately.
Credits advertised by the event are not proof of redemption or inference coverage.

Before public execution: HTTPS, authentication, authorization, request/job quotas, restricted
runner access, bounded images/commands, validated artifacts, monitoring and tested cleanup.
An application container alone does not establish task containment.

Deployment automation, Vultr runner setup, storage/backup setup and public smoke checks
will be added with the corresponding implementation. Do not expose local development servers
as the hackathon production application.
