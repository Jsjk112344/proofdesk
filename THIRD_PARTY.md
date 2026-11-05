# Third-party materials

The initial source files were newly authored for SalesDesk; no application source was
copied from a private repository or a template generator. Planning references are linked
in the documentation; they are not bundled into the application.

Runtime dependencies and development tools are recorded in `uv.lock` and
`frontend/package-lock.json`. Their upstream licenses continue to apply independently
of this repository's MIT license. React, Vite, FastAPI and their tooling are dependencies,
not original SalesDesk work. Preserve their required notices when distributing bundles.

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
answers and canned response parser are original SalesDesk code/data. No external sample
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

## First-live preflight — 2026-11-03

Official [Qwen 3.8 Flash Next model/pricing page](https://api.vultrinference.com/docs/models/qwen3.8-flash-next),
[public model metadata](https://api.vultrinference.com/v1/models/qwen3.8-flash-next),
[completion-token contract](https://api.vultrinference.com/docs/reference/create-chat-completion),
and [reasoning accounting](https://api.vultrinference.com/docs/concepts/reasoning)
were checked for the exact proposed request. Public catalog metadata is saved only in
ignored local preflight evidence; no example implementation was copied.

The catalog identifies [NVIDIA Qwen3.8-Flash-Next-NVFP4](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4)
as its model source. Public tokenizer data/configuration and chat template were downloaded
to ignored `.local/live-preflight/` for input-accounting inspection, not vendored or
relicensed. The upstream model card lists NVIDIA Open Model License and Qwen Community
License 1.0 terms. No weights were downloaded and no external template code was executed.
Hugging Face [Tokenizers](https://github.com/huggingface/tokenizers) was used through
an ephemeral `uv run --with tokenizers` environment for the local token-count check;
it is not a SalesDesk runtime dependency and the dependency locks were unchanged.
The [official event](https://lablab.ai/ai-hackathons/vultr-hackathon) and
[LabLab terms](https://lablab.ai/terms-of-use) were refreshed as required by the skill.
No registration, terms acceptance, credit redemption, publication or submission occurred.

## Web journey and private Vultr preparation — 2026-11-05

All web queue, session scoping, worker integration, React UI, tests and deployment scripts
are original SalesDesk work. No private product code, console screenshot, customer record
or external sample document was imported. Both actual Vultr responses were rejected;
no provider-returned source was committed or presented as verified generated code.

- New dev-only HTTP testing dependency: [HTTPX](https://github.com/encode/httpx) 0.28.1
  (BSD-3-Clause), with HTTPcore 1.0.9 (BSD-3-Clause) and certifi 2026.10.23 (MPL-2.0),
  licenses checked from installed metadata. Dependency locks record these tools; no new
  application runtime dependency was added.
- Trusted UI checks use [Playwright](https://playwright.dev/docs/docker) 1.64.1 and the
  corresponding Microsoft container image, plus the exact `playwright@1.64.1` npm
  package inside a separate test image. Upstream Playwright is Apache-2.0; bundled browser/
  OS components retain their licenses. No browser binary or model weights are vendored.
  Tests use a mocked API and do not call models or browse external sites.
  Prettier 3.6.2 (MIT) was invoked as a pinned ephemeral formatting tool; it was not added
  to application dependencies or the deployment bundle.
- Official references refreshed: [Vultr reasoning/token accounting](https://api.vultrinference.com/docs/concepts/reasoning),
  [public model catalog](https://api.vultrinference.com/v1/models/qwen3.8-flash-next),
  [Docker Ubuntu installation context](https://docs.docker.com/engine/install/ubuntu/),
  [Future of Work challenge](https://lablab.ai/ai-hackathons/vultr-hackathon), and
  [LabLab terms](https://lablab.ai/terms-of-use). No snippets copied. Server Docker was
  installed from the existing host's Ubuntu repositories; system package licenses remain
  upstream. The owner supplied the VM and SSH access; no new cloud resource was created.

## Sales agent reorientation — 2026-11-05 (second continuation)

All retrieval, evidence, contract, drafting, prospect-store, agent, worker, CLI, API,
React workspace, synthetic prospect pages, tests and browser-check code are original
SalesDesk work. The three synthetic prospect websites under `fixtures/prospects/` are
invented for this project; no real company, person or page was copied. No new runtime or
development dependency was added; HTTP retrieval, DNS and TLS use Python's standard library.

Official references checked (no snippets copied):
[Vultr chat-completion contract](https://api.vultrinference.com/docs/reference/create-chat-completion)
(response `model` may differ from request; `message.reasoning`; `completion_tokens_details`;
`reasoning.enabled`; `response_format`), [reasoning concept](https://api.vultrinference.com/docs/concepts/reasoning),
[limits](https://api.vultrinference.com/docs/concepts/limits),
[public model list and metadata](https://api.vultrinference.com/v1/models) (unauthenticated
GET, saved as ignored receipts), and the [event page](https://lablab.ai/ai-hackathons/vultr-hackathon)
(redirects to lablab.build). The UI followed the general guidance of the Apache-2.0
"impeccable" design skill (product register) as process guidance; no design tokens, assets
or code were copied from it or from any other project. The actual HTTP retrieval check used
the IANA `https://example.com/` page as a public, weak-evidence target.
