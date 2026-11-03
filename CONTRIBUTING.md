# Contributing

Read [AGENTS.md](AGENTS.md) and [STATUS.md](STATUS.md). Contributions are licensed under
[MIT](LICENSE); submit only work you have the right to publish.

Use synthetic or explicitly permitted examples. Document copied snippets and dependency
licenses in [THIRD_PARTY.md](THIRD_PARTY.md). Keep real research outputs and secrets out of git.

Run the checks in [README.md](README.md) before opening a pull request. Add meaningful
behavior tests as functionality is implemented; fixtures must not make paid calls.
Update implementation status and distinguish observed evidence from planned acceptance.
GitHub CI covers scaffold quality, offline artifact validation and missing-Docker behavior.
Run the opt-in Docker checks in README.md when changing execution code. Those checks use
only local synthetic tasks, never inference or paid services.
