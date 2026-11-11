# template

The seed of a MEMORY_REPO. Nothing here is loaded by a session: it is copied once, into a fresh
private repository, and then it is that repository's to rewrite — with these exceptions,
`.agents/skills/sweep/`, `.claude/`, and the memory linter (script, tests, dependencies
and CI workflow), which run identically in both places. **A
change to these lands in this copy and in the live one the same turn**: this is the public half,
so it is the one anyone can read, and the two drifting apart is code nobody can review.

The two clones sit side by side, and these run from the directory holding them — the same layout
a session opens in:

```sh
cd "$(dirname "$(pwd)")"          # from inside desire; skip if you are already beside it
gh repo create <you>/memory --private
git clone https://github.com/<you>/memory && cp -r desire/template/memory/. memory/
"${EDITOR:-vi}" memory/config.env   # every value is a placeholder
cd memory && git add -A && git commit -m "Seed the memory" && git push
```

Then fill `config.env` — it is the one file that names you, your agent account and the repos they
work in, and it is why nothing else in `desire` needs to. It is commented, and the readers skip
`#` lines, so the notes stay in the file you edit.

Both readers find `config.env` by counting directories up from themselves — three for the sweep,
two for `.claude/hooks/session-start.sh` — which is your memory clone's root once it is seeded,
and this template's root before that, so `pytest .agents/skills/sweep/` passes here as it will
there. Nothing is searched for and no repository name is hard-coded anywhere.

On Claude Code on the web, the hook sets the commit identity from `AGENT` and `AGENT_EMAIL`, and signs when
`AGENTS_SIGNING_KEY` is in the environment. `.claude/settings.json` runs it when this repo is the
project directory; a multi-repo session has no project directory, so point at it by absolute path
instead — [the root README](../README.md#verified-commits) has the snippet.

For Amp, use the [global loader and skill setup](../README.md#amp) instead. Leave managed signing intact and set the agent author locally on each clone.

What you get is empty on purpose. `README.md` is a board with no state on it yet, and the two `TEMPLATE.md` files are shapes rather than content — the
first turn writes the real thing. Leave the templates in place: they are what an agent reads when
it writes its first `WORK/` file, and deleting them costs you the shape.

`memory/.github/PULL_REQUEST_TEMPLATE.md` is the day PR's shape, the one 🐦 Birdsong writes.
