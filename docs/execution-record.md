# Local execution record v1

[execution-record.schema.json](execution-record.schema.json) is the machine-readable
JSON Schema (2020-12). Records and artifacts live only under ignored
`.local/executions/<uuid>/`. The controller saves a `running` record before Docker create,
then atomically replaces it with `succeeded`, `failed` or `interrupted`. A host crash may
leave `running`; `cleanup` changes it to `failed` / `controller_abandoned` and records
verified absence. Atomic replacement is not a database or power-loss durability guarantee.

Each run stores these controller-owned fields:

| Fields | Meaning |
| --- | --- |
| `id`, `container_name`, timestamps, `scenario` | Identity, UTC observation times and fixture/probe label |
| `source_kind` | Always `deterministic_synthetic_fixture`; no model generated the task |
| `execution_kind` | `local_docker` identifies the attempted runner, not proof that dispatch succeeded |
| `revision` | Controller git commit and dirty flag at start; local tests during development can be dirty |
| `input_sha256`, `script_sha256`, `expected_sha256` | SHA-256 of exact saved `input.txt`, `script.py` and canonical `expected.json` bytes |
| `image`, `evidence.image_id` | Pinned repository digest and resolved platform image ID |
| `limits`, `evidence.policy`, `evidence.preflight` | Fixed requested limits, Docker inspect values, and pre-task kernel/environment measurements |
| `exit_code`, `failure_reason` | Null if not observed; stable failure codes distinguish task exit, validation, deadline and infrastructure errors |
| `validated_artifacts` | Only accepted output: relative path, MIME type, byte count, SHA-256 and exact validation contract |
| `cleanup` | Whether the controller observed container absence; failure reasons remain even after later recovery |
| `probe_check` | Optional CLI expectation result and synthetic host canary hashes, separate from task success |

`task.log` contains bounded untrusted stdout followed by stderr when the exec call returns.
Timeout/output-limit paths discard incomplete output and retain their specific reason.
Unvalidated archives are discarded; rejected files are never written to the host.
Accepted JSON must have exactly the keys, primitive types, nested structure and values
in `expected.json`. For extraction, that contract is the checked-in
[expected output](../fixtures/extraction/expected.json), including `synthetic: true`,
integer quantities/prices, the two listed items and `total_cents: 1600`.
For successful containment probes it is exactly `{"blocked": true}`. Their scripts and
controller policy evidence explain the scope of those observations.

An intentionally incorrect task can have exit code zero, status `failed`, reason
`artifact_schema_or_content_mismatch`, no validated artifacts, and `cleanup.removed: true`.
A missing Docker binary has status `failed`, reason `docker_unavailable`, no exit code or
artifacts, and unverified cleanup. No host execution is attempted in either case.

Tests validate records against the schema using the dev-only `jsonschema` dependency.
This record describes real Docker attempts using synthetic scripts. It is not fixture
replay, evidence of model reasoning, or evidence of a Vultr deployment.
