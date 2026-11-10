# desire

> *Lilacs out of the dead land, mixing*
> 
> *Memory and desire, stirring*

Software engineering prompts inspired by the asymmetric board game Root:

- 🐦 [Birdsong](BIRDSONG.md) plans, asynchronously, before the day starts
- 🌤️ [Daylight](AGENTS.md#daylight) activates in every interactive session you open
- 🌙 [Evening](EVENING.md) reviews and implements, overnight, what you approved

[AGENTS.md](AGENTS.md) is the operating base they all follow: the two layers of memory, what
authorizes a change — with the values it runs on in `config.env`, which lives in your
MEMORY_REPO. It is kept to the rules themselves because every line of it is loaded into every
session; the machinery behind them, needed only when something misbehaves, lives in
[OPERATIONS.md](OPERATIONS.md), which is not. Some guiding principles:

- **Asynchronous feedback via GitHub PRs**, you don't need an interactive chat to get stuff done.
- **Synchronous feedback via chat sessions**, but they start with the bigger picture in mind.
- **Agents open issues when the rules clash**, at your request they open a PR with updated rules.

## Get started

1) Open a new GitHub account for your agents, add it as collaborator to your fork for this repo.
2) Create a new **private** GitHub repo (e.g. called `memory`) and seed it from
   [`template/`](template/): the board, the standing note each open item gets, the day PR's shape,
   the sweep, and a `config.env` in which every value is a placeholder. Fill that file in — `AGENT`
   and `AGENT_EMAIL` for the new account, `USER` for yours, `MEMORY_REPO` for this new repo,
   `DESIRE_REPO` for your fork, and the repos your agents work in under `WORK_REPOS`. It lives
   there and not here because this repo is public and the repos you work in need not be, and the
   sweep is seeded beside it because that is the file it reads.
3) Integrate it to your model provider, adding the `memory` and `desire` repos alongside your work.
   Use the [Amp setup](#amp) below, or have your harness explicitly read `AGENTS.md`. Configure scheduled
   runs separately with `Follow <path-to-desire>/BIRDSONG.md` (before your day) and
   `Follow <path-to-desire>/EVENING.md` (overnight), also loading the operating rules and memory.
   Moving the files to another harness does not migrate the schedules; check their timezone and
   access to every configured repo there.

Nothing in this repo names you: your login, your agent's, and the repos you work in are all in that
one `config.env`, in the repo that is yours. What is here is only the rules.

**Pro tip:** Ask your 🌤️ Daylight session for its password to check it actually loaded the prompt.

## Amp

Amp loads `AGENTS.md`. It does not
discover guidance in sibling repositories. Put a loader in Amp's global instructions so it also
applies when the working directory is a WORK_REPO. For orbs with the clones under
`~/workspace/repos/`, use this, adjusting the paths to your layout:

```text
Before the first response or task action, read ~/workspace/repos/desire/AGENTS.md.
For interactive sessions, follow its Daylight section. When explicitly requested, read
~/workspace/repos/desire/BIRDSONG.md or ~/workspace/repos/desire/EVENING.md instead
and do not execute Daylight. Read ~/workspace/repos/memory/AGENTS.md,
~/workspace/repos/memory/config.env and ~/workspace/repos/memory/README.md,
and the needed notes under ~/workspace/repos/memory/WORK/.
If any required file is unavailable, say so.
```

Daylight is part of the shared operating file, but only interactive sessions execute it.
Never place private config values in public guidance.

Skills in the sibling clones need discovery too. Add their `.agents/skills/` directories to
`amp.skills.path` and reload skills, or install them as personal/workspace skills. Confirm the
expected names appear in the session's skill list. A script such as the sweep can instead be run
by its explicit path; a linked skill can be read explicitly if it is not registered.

Use Amp's orb setup mechanism for dependency installation; `.claude/` startup hooks and permission
denies are Claude Code-specific. Follow [Identity and signing](OPERATIONS.md#identity-and-signing)
for authorship without replacing Amp's managed signer, and
[Watching a pull request](OPERATIONS.md#watching-a-pull-request) for event delivery.

## Verified commits

**Optional** — everything above works without this. What it buys: every commit the agents push
is signed so it shows the **Verified** badge. Authorship is required independently of signing.
Amp uses its managed signer; the setup below is only for Claude Code on the web, where the
SessionStart hook handles both:

1) Generate a passphrase-free SSH key: `ssh-keygen -t ed25519 -f ~/.ssh/agents_signing -N ''` —
   under `~/.ssh`, never in a checkout, where a broad `git add` could commit it.
2) Register `~/.ssh/agents_signing.pub` on `AGENT`'s account as a **signing key** — not an
   authentication key: leaked, it can only forge the badge, revoked by deleting the public half.
3) Paste the private key into `AGENTS_SIGNING_KEY` in the environment's variables; a session
   without it commits unsigned rather than failing.
4) Paste this into the environment's startup script. A multi-repo session opens in the parent
   directory of its clones, so no repo is the project directory, `memory/.claude/settings.json`
   never loads, and the hook silently does not run — no identity, no signing. A workspace-level
   settings file wires it by absolute path, so it pins where the `memory` clone lands. The hook
   ships with the seed and reads the `config.env` beside it, so both are in the one repo that
   names you:

```sh
mkdir -p /home/user/.claude
cat > /home/user/.claude/settings.json <<'EOF'
{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"/home/user/memory/.claude/hooks/session-start.sh"}]}]}}
EOF
```
