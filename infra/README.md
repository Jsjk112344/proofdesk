# Vultr deployment plan

No resources are provisioned. No production deployment configuration is supplied yet.

Proposed starting topology: one control VM for web/API/controller/state and one runner VM
for disposable task environments, with one active task initially. Measure resource needs
before selecting region and instance sizes. Use Vultr Serverless Inference for agent calls.

Before provisioning, record current compute/storage/inference prices, confirmed credits,
maximum authorized spend, usage caps, judging availability and cleanup ownership privately.
Credits advertised by the event are not proof of redemption or inference coverage.

Before public execution: HTTPS, authentication, authorization, request/job quotas, restricted
runner access, bounded images/commands, validated artifacts, monitoring and tested cleanup.
An application container alone does not establish task containment.

Deployment automation, pinned runner images, storage/backup setup and public smoke checks
will be added with the corresponding implementation. Do not expose local development servers
as the hackathon production application.
