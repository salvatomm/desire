# The memory

This private repo is the MEMORY_REPO of 🐦 Birdsong, 🌤️ Daylight and 🌙 Evening. The rules they
follow are public and live in DESIRE_REPO, whose `AGENTS.md` states them and `OPERATIONS.md` their
mechanics — the Memory and One file per open item sections above all; this is the work, so it stays here.
[`config.env`](config.env) at the root is the one file that names USER, AGENT and the repos, and
both the prompts and the tooling read it from here.

What is where:

- [`WORK/<repo>/<number>.md`](WORK) — one note per item, shaped by
  [`WORK/TEMPLATE.md`](WORK/TEMPLATE.md).
- [`README.md`](README.md) — the board, updated in place, its rules at its top.
- [`OTHERS/<person>.md`](OTHERS) — one note per collaborator, shaped by
  [`OTHERS/TEMPLATE.md`](OTHERS/TEMPLATE.md).
- [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) — the shape of the day
  PR's description.
- The open issues — what waits on USER, labelled `yours` or `waiting`.

This file loads the config and the board: @config.env @README.md
