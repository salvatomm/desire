# OPERATIONS.md

The machinery behind the rules in [`AGENTS.md`](AGENTS.md) — how each mechanism works and how to
recover when it doesn't. It is not part of the startup context:
read it when something misbehaves, or when you need the exact command or behaviour behind a rule.

## Finding config.env
Both readers reach `config.env` by a fixed relative path from their own location — nothing is
searched for and no repository name is hard-coded — with `AGENTS_CONFIG` overriding the path for
both. `session-start.sh` reads it before a turn's first commit to set the git identity; `sweep.py`'s
`config()` reads it before every sweep. A `config.env` that cannot be read clears the global git
identity rather than set a stale one, so committing fails loudly; the hook warns when the clearing
itself fails. The public copies under [`template/`](template) are the seed a new MEMORY_REPO is
built from, which is why a change to either reader lands in both the same turn.

ADOPTED_PRS maps each repo to the pull requests treated as AGENT's own wherever authorship decides:
sweeps, scans, the board.

## When DESIRE_REPO is a fork
A turn that finds the upstream `main` ahead opens a PR pulling it in, so upstream rules reach the
fork only through USER's merge, like any other change to the rules.

## Measuring against git history
Before any behind-count or collision measurement, assert the clone is complete: `git rev-parse
--is-shallow-repository` must print `false`, else `git fetch --unshallow origin`. On a shallow clone
there is no merge base, so `git merge-tree` dies with exit 128 and no `CONFLICT` line — which reads
as no conflicts, the silent failure the assertion prevents.

Measure a branch against its base, never a pair: `git merge-tree` with the base itself on one side
is degenerate and always reads clean, so to weigh a branch against its base, merge it in a worktree
and read the result.

Whether a pull request needs its target branch is measured on paths: the files touched by the
commits the base gained, intersected with the files the pull request itself changed since its merge
base.

## Reading CI
Before calling CI green, enumerate the checks a pull request is expected to have. The commit-status
API is not the check-run API and is empty on these repos, so an empty status list is never "no CI
ran". A pull request with no `build` run at all has a merge conflict rather than a slow runner: a
`pull_request` job runs against `refs/pull/N/merge`, which does not exist while the pull request is
dirty.

## Measuring drift
A next repo's drift is `git diff upstream/main...next/main -- . ':!.github'`, split library, tests
and docs, reported with its trend: lines landed on next against lines merged upstream, per week. Moving work
from upstream to next adds no drift, it only moves it.

## Bugs in a next repo
An open issue reporting a bug in a next repo needs no design decision when what is right is already
said — by a law, a docstring, `STYLE.md` or the behaviour upstream — and the fix chooses nothing: no
public name beyond the protocol it completes, no stated convention changed, no pick between readings
the issue leaves open. A bug an open pull request already addresses is left to it, and so is one
whose issue carries an unanswered ask from either installation working the next repo.

## Reading the sweep
[`sweep.py`](template/memory/.agents/skills/sweep/sweep.py) runs from the MEMORY_REPO clone as
`.agents/skills/sweep/sweep.py [--since <ISO8601>] <owner/repo> [number...]`. No GitHub MCP tool
says *who* reacted, so this is how USER's approvals and unanswered questions are read. 🐦 Birdsong
and 🌙 Evening run it with no numbers before planning, over every open item of MEMORY_REPO,
DESIRE_REPO and the WORK_REPOS, with `--since` the time the board says the last sweep ran; neither
concludes "nothing to do" without a clean sweep: checkboxes, CI and behind-counts are all state the
agents wrote themselves, and only the sweep reads what USER did. It flags every
APPROVE_EMOJI react from USER on a body or a comment across both endpoints, and every thread where
USER spoke last — a thread is answered when anyone other than USER has replied since, and which
agent closed it does not matter.

`--since` reads the comments as a delta; widen the window after a turn runs late or dies. The sweep
also lists the issues closed inside the window with their `state_reason` and who closed them, since
closing an issue is an answer that leaves no thread. Reacts ignore `--since`: a 🚀 has no answered
state and is reported whatever its age until the thing it sits on closes. A USER question nobody has
answered is reported whatever its age too, unless the pipeline 👀'd it and it predates the window —
so a question landing between two sweeps is never lost, an old one goes quiet once a turn says it
received it, and a sweep with no `--since` reports the whole backlog.

The sweep marks a `👀` flag when anyone but USER has reacted, so a turn can tell a backlog from a
queue. An instruction with no react was never received, one with 👀 is in progress, and the react is what
takes an old question out of the sweep. A turn reacts on each instruction it picks up before doing
the work. React on the comment or the body itself, with
`add_issue_comment`'s `reaction` on a body or conversation comment, and
`add_reply_to_pull_request_comment`'s on a review comment.

## Matching an attribution footer
AGENT_FOOTERS includes markers on existing posts, even if their harness is no longer used:
removing one can make an agent's reply read as USER's unanswered question.

A reply from USER counts as an agent's when its last line is one of AGENT_FOOTERS — as the whole
line, or inside the HTTPS *target* of a Markdown link on it (which is how a URL token matches the
footer wrapping it). A link's *label* never counts, since the label is the half a human types, so
accepting it would let any destination silence a thread; nor does a marker in prose, which is a
human writing about the convention. This is how the adopted PRs read.

A harness whose footer links to a shareable session snapshot puts its URL token in AGENT_FOOTERS
rather than relying on the label; the snapshot is opened and reviewed before it is linked, and an
internal session or thread ID is not a URL and must never be turned into one.

## The day PR
- Opening a new day's PR first merges the previous one: whatever in its comment thread
  should outlive it goes into a file or an issue first, a conflict is resolved by merging `main`
  into its branch, and the new day is cut from `main`.
- If no day PR is open, the turn opens one rather than borrowing whichever branch is open. `sweep.py`
  names the open day PR. Its description follows MEMORY_REPO's
  `.github/PULL_REQUEST_TEMPLATE.md`, and only 🐦 Birdsong writes it.
- A file that is a substantial read in its own right, `OTHERS/<person>.md` above all, opens its own
  pull request the first time it is written, titled for the file, so it can be read on its own.
  Agents merge it themselves at the latest when the next day's PR opens; later edits go to the day
  PR.
- Two day PRs open at once, or two under one title, is a turn that skipped the merge: the sweep
  prints MEMORY_REPO's open PRs and fails on it. `git log` is not the check.
- Feedback happens as comments on the day PR or in interactive chats, recorded as agent comments
  with verbatim quotes. Memory files stay as concise as possible.

## WORK notes

The memory linter checks note structure and links offline, with optional live GitHub
comparison. Installation, commands and rule coverage are in
the docstring of
[`template/memory/scripts/lint_memory.py`](template/memory/scripts/lint_memory.py).
- One writer per file, one file per item, written by the turn that did the work. `<repo>` is the
  repository name alone and `<number>` is GitHub's, which numbers issues and pull requests in one
  space (`WORK/discopy/489.md`).
- An open item with no note is printed by the sweep as context only. A closed item's note is
  deleted, archiving nothing: what a merged PR did is in `main`, what a closed one was is on
  GitHub.
- `sweep.py` reads the directory against the live open items: a required item with no file, a file
  with no open item, and a file whose `read` date is older than its item's last update are all
  findings.
- `OTHERS/<person>.md` records what they own, what they have landed and what of theirs touches the
  work we do; a `WORK/` note records the one item.

## Issues and reviews
- A blocker recorded only in a note or on the board has not been asked: it is asked on its PR.
- An ask's 48 hours run from its own comment. Any comment, review or react of USER's on the item
  or its issue since then is a word, and the ask waits for a turn to read it. A later PR can
  reverse a change that was only committed to next `main`: nothing was released or sent.
- A pull request closing an issue uses GitHub's syntax, one keyword per issue on the same line as
  its reference; what merging closes is read from `closed_by_pull_requests`, never from our prose.
- Answer a thread once the change has landed, then resolve it if your job is done.
- Review cost counts lines because churn is a proxy for how much there is to scan, not to think
  about.

## Merging on approval
USER's approval must be on the head commit being merged; a push after it needs a new one. The
pull request must also pass its checks, merge cleanly and have no thread waiting on an agent.

## Watching a pull request
In Amp, discover `create_github_subscription` and subscribe this thread to comments and reviews
after opening a PR, and to CI for the exact head SHA and branch after each push, with
`automatic: true`. Supply `branch` only for CI. Check the returned subscription is enabled and
unblocked; an existing paused listener is not active. Access depends on the connected GitHub
installation and workspace, not just the runtime having the tool.

If setup fails, inspect any subscription ID it saved before retrying. Report the missing listener;
never claim monitoring is active from an attempted call. Event payloads are evidence to fetch
and check, not fresh permission to push or merge.

## When the harness says otherwise
- Claude Code's SessionStart hook writes its scheduling-tool deny list; Amp does not run that hook
  or enforce `.claude/settings.json`. In Amp the no-timed-follow-up rule is prompt guidance.
- If a harness requires a conflicting commit identity, stop before committing and report it;
  do not disable its signing mechanism to work around it.
- The day PR's branch winning in MEMORY_REPO is standing permission: a memory turn that asks which
  branch to push to has misread the rule.

## Identity and signing
Every write to GitHub — pull requests, comments, reviews, reactions — goes through the MCP tools.
`GITHUB_TOKEN` is for reads only; it need not authenticate as the MCP account. Discover GitHub's
authenticated-user tool (`get_me` in Amp) and assert its login is AGENT before the first write.
On every clone set local `user.name` and `user.email` from AGENT and AGENT_EMAIL before committing;
neither a correct MCP login nor a signature sets the author. Check the effective values, then
check the branch's authors before pushing with
`git log --format='%an <%ae>' origin/main..HEAD`.

Amp orbs provide managed signing: preserve `gpg.*`, `user.signingkey` and `commit.gpgsign` while
setting authorship. No private signing key needs copying into the orb. Do not run the legacy hook
with a forged `CLAUDE_CODE_REMOTE` flag: it clears signing settings. After a push, read GitHub's
verification result before claiming Verified.

On Claude Code on the web, the SessionStart hook handles identity and optional SSH signing via
`AGENTS_SIGNING_KEY`. Without that variable it commits unsigned; with it, the key must be registered
as a signing key on AGENT's account. Setup is in the README's
[Verified commits](README.md#verified-commits) section.
