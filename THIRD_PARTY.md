# Third-party materials

The initial source files were newly authored for ProofDesk; no application source was
copied from a private repository or a template generator. Planning references are linked
in the documentation; they are not bundled into the application.

Runtime dependencies and development tools are recorded in `uv.lock` and
`frontend/package-lock.json`. Their upstream licenses continue to apply independently
of this repository's MIT license. React, Vite, FastAPI and their tooling are dependencies,
not original ProofDesk work. Preserve their required notices when distributing bundles.

Before adding sample repositories, documents, images, model outputs or third-party code,
record the source, license/permission, author attribution and modifications here. Public
accessibility alone is not permission to redistribute. No external sample dataset is
included in the initialization baseline.

## Local execution slice — 2026-11-03

All controller/runner/validation code, probes, synthetic document and expected output
were authored for this public project. No private application image, code, customer
record or external sample dataset was reused. The deterministic fixture is not a model
output. No snippets were copied from the following implementation references.

- Task runtime: [Docker Official Python image](https://hub.docker.com/_/python), Python
  3.12 slim Bookworm, digest pinned in [infra/task-image.txt](infra/task-image.txt).
  Python carries the PSF license; the Debian base, GNU tar and other bundled programs
  retain their own licenses. The image is pulled, not vendored or relicensed as MIT.
  [Official image build sources](https://github.com/docker-library/python) and
  [Python license](https://docs.python.org/3/license.html).
- New dev-only dependency: [jsonschema](https://github.com/python-jsonschema/jsonschema)
  4.26.0 (MIT), for record schema tests. Transitive additions in `uv.lock`: attrs 26.1.0,
  jsonschema-specifications 2025.9.1, referencing 0.37.0 and rpds-py 2026.9.1 (all MIT,
  checked against installed package metadata). No new Python runtime dependency.
- Implementation references checked 2026-11-03: [Docker run constraints](https://docs.docker.com/engine/containers/run/),
  [Docker cp archive semantics](https://docs.docker.com/reference/cli/docker/container/cp/),
  and [jsonschema validation API](https://python-jsonschema.readthedocs.io/en/stable/validate/).
- Skill-required competition refresh on 2026-11-03: [official event](https://lablab.ai/ai-hackathons/vultr-hackathon)
  and [LabLab terms](https://lablab.ai/terms-of-use). No account activation, terms acceptance,
  credit redemption, provisioning, publication or submission was performed in this slice.

## Bounded inference workflow — 2026-11-03

The Vultr adapter, budget accounting, workflow, tests, additional synthetic documents,
answers and canned response parser are original ProofDesk code/data. No external sample
dataset or model output was imported. The offline parser is fixture source, not generated
code. No new runtime or development dependency was added; HTTP and process deadlines use
Python's standard library. No provider SDK, automatic retry layer or alternate provider.

Official technical API references checked for this implementation on 2026-11-03 (no
snippets copied): [Vultr chat-completions contract](https://api.vultrinference.com/docs/reference/create-chat-completion),
[request/context/output limits](https://api.vultrinference.com/docs/concepts/limits),
[quickstart and usage](https://api.vultrinference.com/docs/get-started/quickstart), and
[Vultr model/API FAQ](https://docs.vultr.com/products/compute/serverless-inference/faq).
No new competition/market research, account access, credit redemption or paid call was
performed; current model availability/prices must be verified before live authorization.
