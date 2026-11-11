# Changelog

What landed on `main`, newest first — when each rule started binding, and what it replaced.
Entries state the changes, no explanation of why.

## 2026-11-10

**Next repos are measured by quality; idle runs say so; an open ask is hands off** (`AGENTS.md`,
`OPERATIONS.md`, `template/memory/.agents/skills/sweep/`) — the agents' work on a next repo is
measured by the library's quality, drift stays a nightly reading. A scheduled run that finds
nothing leaves one line on the day PR. A next-repo bug whose issue carries an unanswered ask from
either installation is left alone. `sweep.py` exits 2 on any dropped connection or unreadable
file. Replaces: "their job is to keep the drift between the two small"; a run with nothing to do
writing nothing; only a bug an open pull request addresses being left alone; exit 1 on a dropped
connection. USER: *"the main
test is whether all this work can get merged into one repo without creating a mess, adding
features without sacrificing library quality"*, *"not sure why we would stop measuring, doesn't
cost much"*, *"if the routine runs and finds nothing then it can write that down"*, and "hands
off" on #203.

**The memory seed ships its linter** (`template/memory/`, `OPERATIONS.md`, `.github/`) —
`scripts/lint_memory.py` checks `WORK/` note structure, dates, logs, board length and local links
offline, with optional GitHub and HTTP-link modes; its script, tests, requirements and workflow
are copies the live MEMORY_REPO carries verbatim, and its docs are its docstring. USER: *"also merge the linter while we're at
it"*, *"i'd rather have the docs live with the code directly than in a separate folder"*.

**Amp entry points and runtime boundaries** (`AGENTS.md`, `OPERATIONS.md`, `README.md`,
`CLAUDE.md`, `.github/lint.py`, `template/README.md`, `.agents/skills/pr-shepherd/`,
`.agents/skills/brief/`, `template/memory/`) — Daylight
moves into `AGENTS.md` as an interactive-only section and its separate file is deleted; `CLAUDE.md`
imports `AGENTS.md` alone; scheduled runs select Birdsong or Evening. The heartbeat fallback
and its skill are removed. Amp setup covers global guidance, sibling skills and separately
configured schedules. Rules respect the harness's
instruction hierarchy. Identity checks discover the MCP tool and set local authorship, preserving
Amp-managed signing. PR monitoring verifies active subscriptions and reports unavailable follow-up.
Read-only discussion with no work or new durable directive requires no memory writeback.
USER: *"update the prompts open a PR"*, *"let's remove that fallback altogether it's not needed
anymore"*, *"let's remove the DAYLIGHT.md as a file and make it into a section of AGENTS.md"*.
Then Daylight drops its "Leave the plan" step and its interactive-only line, the opening drops the
memory-loading and harness-setup lines, and Daylight names the `brief` and `spawn` skills. USER: *"that's useless for an agent to
know let's drop it"*, *"you can mention the brief skill here"*, *"you can mention the spawn skill
here"*, *"drop this bullet point it doesn't happen that often to have a day session just to leave
work for the night, most of the time i want the work to happen straight away"*.
The memory seed's `AGENTS.md` imports `config.env` and the board.
Closes #201.

## 2026-11-09

**The spawn skill** (`.claude/skills/spawn/`) — a child session is created on
DESIRE_REPO, its prompt opens with the attach, clone and register steps for MEMORY_REPO and the
work repos, and the parent reads its transcript for those steps before leaving it; a refused
attach goes to USER. Binds nothing: a session loads it before creating another. USER: *"problem
when you spawn it's without memory and desire so the child sessions are confused"*, then *"make
sure to add that as a skill in desire so you don't make that as a mistake next time"*.

**Every ask has a default and a date; on a next repo a reversible one is due after 48 hours**
(`AGENTS.md`, `OPERATIONS.md`, `EVENING.md`, `.agents/skills/brief/`) — a 🚀-able comment or a
`waiting`/`yours` issue asks one decision, names its recommended option and the day asked; a
bundle is not an ask. On a next repo, an ask a later PR can reverse is due 48 hours on with no word
from USER: an agent takes the default, says so on the item and closes the `waiting` issue linking
it. Upstream, collaborators' work, settings, access, money, publication or visibility, licence,
anything irreversible and asks with no recommendation still wait. Replaces: a next-repo bug that
needs a decision gets one 🚀-able comment and waits.
USER: *"spawn another to prune the board and write the default-and-date rule"*. Ruling: #207.

**Next repos lose their experiments line** (`AGENTS.md`) — "experiments live on branches of the
next repo, never on its `main`", from 2026-10-14, is deleted
([#163](https://github.com/toumix/desire/issues/163)).

## 2026-11-05

**Five skills** (`.agents/skills/`, `.claude/skills/`,
`.github/workflows/lint.yml`) — `pr-status` measures a pull request live and gives one verdict;
`remerge` merges a target branch into a pull request's branch locally, never pushing;
`post-check` lints a draft before it is posted; `work-notes` lists the items a turn touched with no
`WORK/` log line and lints the notes; `rules-edit` is the checklist for a rules PR, with a diff
check for installation values. CI runs each skill's tests. USER: *"look at all our previous
interactions in memory and desire repos then open a new desire PR with skills that would speed up
and improve our future work"*.

**The brief skill** (`.agents/skills/brief/`, `.claude/skills/`) — USER's intent turned into a
prompt a fresh session can run, posted for a 🚀 instead of run: an issue brief (the change in
mathematical terms, slices with their review cost, checks, `TODO.md` boxes) and an experiment brief
(hypothesis, the refuting number, the decision it buys, budget, what is recorded). Binds nothing: a
session loads it when asked for a brief. USER: *"i keep hearing people (including anthropic
engineers) say i shouldn't be prompting you directly i should ask you to prompt yourself, how do i
do that in the context of discopy-next development and research on the wiki?"*, then *"yes draft
the brief skill"*.

## 2026-10-29

**Attribution is harness-agnostic** (`AGENTS.md`, `OPERATIONS.md`, `template/memory/`) — posts
identify their actual harness; installation-specific markers live in `AGENT_FOOTERS`, not in
the prompt, script or test expectations. USER: *"can we make the prompt and script harness
agnostic instead?"*. Ruling: #199.

## 2026-10-28

**Push work on a branch, with a dedicated PR** (`AGENTS.md`) — agents commit and push requested
work without asking again. Outside `MEMORY_REPO`, reuse a branch only while its PR is open;
otherwise open a new branch and dedicated PR. Memory keeps its day/file PR workflow.
USER: *"always push your work to github, no need to ask for permission"*, clarified as
*"to a new branch and open a dedicated PR whenever there isn't one already"*. Ruling: #197.

## 2026-10-22

**Role files are run orders; a rule is stated once** (`BIRDSONG.md`, `EVENING.md`, `DAYLIGHT.md`,
`AGENTS.md`, `OPERATIONS.md`, `.github/lint.py`, `template/memory/`) — 🐦 Birdsong, 🌙 Evening and
🌤️ Daylight are numbered steps in the order they run; Evening's CI and merge-reason mechanics move
to `OPERATIONS.md` (*Reading CI*, *Measuring against git history*). `template/memory/AGENTS.md`
says what is where and points to DESIRE_REPO's `AGENTS.md` instead of restating its rules, which
gains the one that lived only there: DESIRE_REPO's open issues read before planning. 🌙 Evening
finishes every item left in the next repos, sub-agents taking items that do not collide in
parallel, instead of one item at a time; everywhere else it builds nothing USER did not order and
keeps our open items moving. The `WORK/` and `OTHERS/` templates drop their restated rules.
`lint.py` reports any run of eight words two rule files share. USER: *"file a PR for the other
changes you proposed"*, *"why just one item a night? it should finish whatever is left, spawning
subagents if needed"*, *"this applies only to the next repos, for the others it should mostly do
housekeeping not develop new stuff"*.

**Birdsong reads every day PR since its last turn; an unreachable repo is an issue**
(`BIRDSONG.md`) — the day PR description covers all the day PRs since the last one, not only the
latest; a WORK_REPO the routine cannot reach is a `yours` issue on MEMORY_REPO instead of a line in
the summary. USER on memory#153: *"there were two day PRs yesterday you only summarised the second
one"*, *"raise an issue whenever a repo is missing from the routine's scope rather than burying it
in the summary"*.

**The sweep reads only bare `#<number>` as a note's own citation** (`template/memory/`) — a
number qualified by a repository, `desire#162` or `rel-int/optyx#16`, no longer makes the note's
own repository's item of that number required. Closes #171.

## 2026-10-21

**`AGENTS.md` halves; plain words for the routines' jargon** (`AGENTS.md`, `OPERATIONS.md`,
`BIRDSONG.md`, `DAYLIGHT.md`, `EVENING.md`, `template/memory/`) — `AGENTS.md` goes from 2,764 to
about 1,500 words with five bold rules; the conditions, mechanics and edge cases move to new
`OPERATIONS.md` sections (*The day PR*, *WORK notes*, *Bugs in a next repo*, *Issues and reviews*,
*Merging on approval*, *Watching a pull request*, *When the harness says otherwise*, *Identity and
signing*). *Head* becomes *item* (one open pull request or issue, defined in `AGENTS.md`),
*terminal handoff* becomes *done*, *support work* becomes *housekeeping*, *lane* and *in play* are
gone. The sweep and the 👀 react leave `AGENTS.md` for `BIRDSONG.md` and `EVENING.md`: 🌤️ Daylight
no longer runs it. USER: *"Cut `AGENTS.md` to about 1,500 words. Keep around 5 bold rules and move the
conditional clauses to `OPERATIONS.md`. Yeah please do that in a fresh desire PR now."*, *"there
shouldn't be weird terms like this, I have no idea what these words mean either"*, *"This whole section can go away, it's not needed by daylight only
birdsong and evening should run the sweep"*.

**The board drops its rulings; no board line about a single item** (`BIRDSONG.md`,
`.github/lint.py`, `template/memory/`) — the board's *Ruled, do not re-ask* section is gone: a
ruling lives in DESIRE_REPO, as a prompt line or an open issue. A board line about exactly one
item belongs in that item's `WORK/` note, and `lint.py --memory` reports one that names exactly one
item. USER: *"remove the board's "Ruled, do not re-ask" section"*, *"remove the facts about single
PRs and add an explicit rule to avoid them coming back"*.

**`RULES.md` leaves DESIRE_REPO; a linter and a prompt budget; the harness's three asks**
(`AGENTS.md`, `CLAUDE.md`, `OPERATIONS.md`, `BIRDSONG.md`, `DAYLIGHT.md`, `EVENING.md`, `.github/`,
`template/memory/`) — `RULES.md` is deleted and no file here names it or `TODO.md` any more: the prompts drop the
`TODO.md` gate, a WORK_REPO's own `AGENTS.md` says how its pull requests are run, and `sweep.py`
no longer reads `TODO.md`. `.github/lint.py`, run on every push, checks the relative links, the deny
lists' tool names, the copies a MEMORY_REPO carries from `template/memory/` and its board's 200
lines, and a budget of 30,000 bytes on what `CLAUDE.md`, `BIRDSONG.md` and `EVENING.md` load
together. The deny lists name `mcp__claude-code-remote__*`, the server they meant. Turmoil gains *When
the harness says otherwise*: timed check-ins, draft pull requests, the assigned branch, the last of
which leaves the Memory section. The board is no longer said to be rewritten every turn. USER:
*"remove desire/RULES.md we only need it for discopy"*, *"There is no RULES.md nor TODO.md in this
repo anymore, scan and remove these from everywhere except CHANGELOG"*, *"add a special section in
Turmoil for these three cases"*, *"add a cap at 20% above the current size"*, *"drop the date let's
just say 30K total, remove it from AGENTS.md it can be in the linter only"*.

**`WORK/` notes only for what an agent works on; a slimmer note** (`AGENTS.md`, `sweep.py`,
`template/memory/`, closes [#158](https://github.com/toumix/desire/issues/158)) — a note is owed
by our own pull requests, every item a session touched and every open item a note cites, no longer
by every open pull request. `sweep.py`'s `required()` says which. The note drops its `state` line
for a `whose · read <date>` line, and its log keeps the
last five turns. USER: *"yes let's do that too"*.

**Birdsong clears stale `WORK/` notes; no `TURNS/`; USER's todos are issues** (`AGENTS.md`,
`BIRDSONG.md`, `DAYLIGHT.md`, `EVENING.md`, `template/`) — 🐦 Birdsong deletes the note of every
merged or closed item before planning. `TURNS/<date>.md` is dropped: a turn's account is its one
comment on the day PR. `USER_TODO.md` is replaced by MEMORY_REPO issues labelled `yours` or
`waiting`, closed on evidence, never a `yours` one by an agent. USER: *"let's add cleaning up stale
work notes as an explicit rule for birdsong"*, *"we don't need turns at all? we mostly have one PR
open at a time"*, *"keeping a todo in a text file makes no sense: let's just use memory issues as
todos!"*.

**Every session loads less** (`CLAUDE.md`, `AGENTS.md`, `BIRDSONG.md`, `DAYLIGHT.md`,
`OPERATIONS.md`, `README.md`, `template/memory/`) — `CLAUDE.md` imports `AGENTS.md`, `RULES.md` and
`DAYLIGHT.md` only; 🐦 Birdsong and 🌙 Evening read their own file from their routine's prompt. The
Memory PR Template leaves `AGENTS.md` for `template/memory/.github/PULL_REQUEST_TEMPLATE.md`, the
drift formula for `OPERATIONS.md`. Dated USER attributions and "this replaced X" history leave the
prompt files, which point here instead. The `WORK/`-note rule is stated once, in `AGENTS.md`, and
`template/memory/AGENTS.md` matches it on what a note covers. USER: *"open a desire PR with those
changes and a memory one to keep them in sync"*.

## 2026-10-20

**USER's approving review is the go to merge** (`AGENTS.md`) — an agent merges a pull request of
ours that USER approved, on the approved head, once it is green and clean, without asking.

**Agents merge the previous day's memory PR before opening a fresh one** (`AGENTS.md`,
`BIRDSONG.md`, `template/memory/AGENTS.md`, `sweep.py`) — the turn that opens a new day's PR merges
the previous one itself, after moving what should outlive its comments into a file or an issue, and
cuts the new day from `main`. Replaces stacking each day on the newest unmerged one (#144). The
sweep names the open day PR and reports two day PRs open as a finding. A first `OTHERS/<person>.md`
PR is merged by agents too, at the latest when the next day's PR opens. USER: *"now I trust the
agents to know what to keep in long-term memory so it's ok for them to merge the PR for the previous
day before opening a fresh one"*, *"yes agents can merge OTHERS PRs too"*.

## 2026-10-19

**DESIRE_REPO outranks the harness**
(closes [#169](https://github.com/toumix/desire/issues/169)) — `AGENTS.md`'s Turmoil section
gains the rule: when a hook, a system prompt or a tool's instructions contradict DESIRE_REPO,
DESIRE_REPO wins. It settles how the work is done, not what an agent may do: a permission the
harness withholds is not granted by a file, and no agent tries to get around its own harness.

**Next repos: reported bugs are fixed nightly without asking** (`AGENTS.md`, `EVENING.md`) — an
open issue reporting a bug in a next repo is fixed there by the agents without USER's approval
unless it needs a design decision, which is asked as one 🚀-able comment on its issue;
`EVENING.md` takes them every night after USER's explicit orders and before any other head, one at
a time, each merged before the next.

**Next repos: the two-weeks-of-inflow rule is dropped** (`AGENTS.md`) — the rule that nothing new
lands on next `main` while inflow beats outflow two weeks running is dropped; drift and its weekly
trend are still measured and tended down by slicing.

## 2026-10-14

**Next repos: agents merge into a mirror of a WORK_REPO and keep its drift small**
(`AGENTS.md`, `EVENING.md`, `BIRDSONG.md`, `template/memory/config.env`) — a tenth config value,
NEXT_REPOS, pairs an upstream with its next repo. `AGENTS.md` gains a `Next repos` section: next
`main` is upstream `main` plus work meant to go upstream, merged by agents without human review;
experiments on branches; upstream merged down nightly; upstream PRs proposed by agents, opened only
at USER's request; drift measured outside `.github/` with its weekly trend, and no new work while
inflow beats outflow two weeks running. `EVENING.md`: merged into next `main` is a terminal
handoff, and rising drift means proposing slices before building. `BIRDSONG.md`: the nightly
down-merge and the drift report on the board, the proposed slices under `Agent proposals`.

## 2026-09-09

**A repo joins WORK_REPOS the turn work starts there, no separate ask**
([#151](https://github.com/toumix/desire/pull/151), closes
[#150](https://github.com/toumix/desire/issues/150)) — `AGENTS.md`'s Config section gains the
rule.

**Eight conventions graduate out of the holding pen**
([#139](https://github.com/toumix/desire/pull/139), closes
[#115](https://github.com/toumix/desire/issues/115)) — the 189 lines evicted from the board on
08-26 are sorted and the pile is emptied. `AGENTS.md` gains four: the gate is USER's review time
and no turn proposes a batch; trust settles whether to act while evidence settles what is true; a
claim is measured rather than inferred from a green suite or from a "blocked" someone wrote down;
and `git merge-tree` with the base on one side is degenerate, so it measures a pair rather than a
branch against its base. `RULES.md` gains two: rule 1 that a review bot's severity is not evidence
and that rule 1 outranks it, rule 2 that draft state is not a readiness signal. `EVENING.md` gains
two: the overlap that justifies a re-merge is measured on paths, and the commit-status API is not
the check-run API — a head with no `build` run is a merge conflict, not a slow runner. The rest of
the pile is dropped, each entry either already carried by the prompts, replaced by
`WORK/<repo>/<number>.md` and the one-memory-PR-per-day rule, or state rather than convention.

## 2026-09-08

**A new day's PR stacks on the newest still-open one, not on `main`** (`AGENTS.md`,
`template/memory/.agents/skills/sweep/sweep.py`) — the day-PR paragraph now says a new day's branch
is cut from the newest still-open day PR's branch whenever a previous day's is unmerged, so the
per-turn `README.md`/`USER_TODO.md` rewrites fast-forward instead of conflicting. `sweep.py`'s
`memory()` prints that branch when any day PR is open. Closes
[#144](https://github.com/toumix/desire/issues/144), the gap that cost three turns a hand-fold
(09-01, 09-03, 09-07); the "several day PRs open at once is USER not having merged" ruling is
unchanged — siblings are still not a finding.

## 2026-09-03

**The MEMORY_REPO day-PR-branch rule is standing permission, not a per-turn ask** (`AGENTS.md`) —
the branch clause is strengthened to say the day PR branch wins over whatever branch a session was
assigned *without asking USER each time*, and to name the case it kept snagging on: a harness or
task that pins the session to one branch and forbids pushing elsewhere without permission. USER's
standing grant is that authorization. Clarifies
[#45](https://github.com/toumix/desire/pull/45)'s "the open memory PR's branch wins over the
assigned one" rather than replacing it — it was being read as blocked by the per-session assignment.

**The prompts are slimmed: AGENTS.md keeps the rules, OPERATIONS.md holds the machinery**
(`AGENTS.md`, `OPERATIONS.md`, `README.md`) — historical justification that this changelog already
carries is cut from `AGENTS.md`, and the mechanism/recovery detail (config-reader paths, the
shallow-clone check, the sweep's `--since` semantics, footer matching, the signing-hook setup) moves
to a new `OPERATIONS.md` that `CLAUDE.md` does not import, so the every-session context is the rules
alone. No rule's meaning changes. `AGENTS.md` 276→195 lines. The README's "under a hundred lines"
claim is replaced with the rules-vs-machinery split.

**The webhook-only rule is back, generalized rather than restored verbatim**
(`AGENTS.md`) — a runtime that can wake on GitHub events watches a PR by webhook and never
schedules a timed self check-in; #136 dropped this sentence when it added the Codex heartbeat,
which is now scoped explicitly to runtimes that cannot wake on a webhook, Codex being the
standing case. Corrects the entry below, from earlier the same day, which wrongly said the old
rule "never changed."

**Timed self check-ins are denied in settings, not asked for in prose** (`template/memory/`) —
`.claude/settings.json` carries a `permissions.deny` on `send_later`, `create_trigger`,
`update_trigger`, `fire_trigger`, `ScheduleWakeup` and `CronCreate`, and `session-start.sh`
merges the same list into `~/.claude/settings.json` at every start, since the container is
fresh each time. The harness refuses the call before the model can make it.

## 2026-09-02

**Idle pull-request heartbeats back off to eight times their starting interval**
([#142](https://github.com/toumix/desire/pull/142), closes
[#140](https://github.com/toumix/desire/issues/140)) — consecutive checks with no pull-request
change and nothing to do double the interval from its requested or default baseline, capped at
eight times that baseline; pull-request activity or agent action resets it. Extends #136.

**Each Codex pull request gets a heartbeat in the task that opened it**
([#136](https://github.com/toumix/desire/pull/136), closes
[#134](https://github.com/toumix/desire/issues/134)) — before ending, the task schedules a native
check of its pull request. Each check handles USER feedback and any valid bug or style report whose
fix stays inside USER's original prompt, stays quiet when nothing changed, and deletes itself when
the pull request merges or closes. Replaces the webhook-only rule.

## 2026-09-01

**`REVIEWS/` becomes `OTHERS/`, written on every review of somebody else's work**
([#133](https://github.com/toumix/desire/pull/133)) — `AGENTS.md` says a session reviewing a pull
request that is not ours writes `OTHERS/<person>.md` as well as that item's `WORK/` note. The
`Memory` section drops the file-kind list that MEMORY_REPO's own `AGENTS.md` already carries.

**One memory file per open item, replacing the board's queue**
([#133](https://github.com/toumix/desire/pull/133), closes
[#124](https://github.com/toumix/desire/issues/124)) — `WORK/<repo>/<number>.md` in MEMORY_REPO is
one standing note per open item of a WORK_REPO, rewritten by whichever session touched it and
deleted when it merges or closes. It covers the whole repository rather than AGENT-owned heads:
ownership is a field in the note, not a condition on it existing. A note is required for every
open pull request and for every open issue an existing note cites; every other open issue is
printed as context. `AGENTS.md` gains the file kind, its lifetime and its shape; "a turn that
stays within one workstream leaves MEMORY_REPO untouched" is reversed — every turn writes the note
of every item it touched. The board becomes cross-cutting state only. `sweep.py` gains `notes`,
`stale`, `cited`, `memory_clone` and `uncharted`, reporting an item with no note, a note with no
open item and a note older than the item it describes, and `test_sweep.py` covers them.

**One memory pull request per day for the day's work, one per standing file's first write**
(same PR) — `AGENTS.md` replaces "every later turn of that day pushes to it instead of opening
another". A `OTHERS/<person>.md` first write opens its own pull request, titled for the file; every
later edit to it goes to the day PR; a turn that finds no day PR open opens one.

**🌤️ Daylight implements** (same PR) — `DAYLIGHT.md`'s "it designs and queues, never implements"
is struck, and Daylight writes the `WORK/` file of every item it touched before the session ends.

**🌙 Evening finishes one head before taking another** (same PR, from
[#128](https://github.com/toumix/desire/issues/128)) — `EVENING.md` replaces queue-wide `TODO.md`
churn with one head driven to a terminal handoff: merged, closed, ready with `TODO.md` deleted and
every expected check passed, or blocked on one named external action asked for on the work PR.
Scans, re-merges, review triggers and board repair are support work, not outcomes. A check that
was never created is pending and a failed query is unknown, neither of them green. 🐦 Birdsong
reads `WORK/` rather than re-deriving the queue.

**The sweep exits 2 when GitHub cannot be read** (same PR, from #128) — an incomplete sweep is
neither clean nor a finding. `review_comments` stops swallowing a 403 as an empty comment list,
catching only the 404 that means the number is an issue rather than a pull request, and `config`
skips blank lines and `#` comments.

**A `template/` directory seeds a fresh MEMORY_REPO** (same PR) — `template/memory/` carries
`AGENTS.md`, an empty board, an empty `USER_TODO.md`, `config.env` with every value a placeholder,
the day PR's body template and the `WORK`/`OTHERS`/`TURNS` shapes. The README's Get started points
at it.

**The memory PR template drops "Waiting on you", gains "Since last time"** (same PR, closes
[#126](https://github.com/toumix/desire/issues/126), the content of
[#127](https://github.com/toumix/desire/pull/127)) — replaced by a summary of activity since the
previous memory PR, split by source, required to say plainly when a round did nothing or did not
run. `What changed today` is folded into it. The `Memory` section gains `USER_TODO.md` and
`OTHERS/<person>.md`.

**Agent-authored posts are recognised by any of AGENT_FOOTERS**
([#123](https://github.com/toumix/desire/pull/123), closes
[#121](https://github.com/toumix/desire/issues/121)) — `AGENT_FOOTER` and the
`AGENT_FOOTER_ALIASES` of this pull request's first version become one list, `AGENT_FOOTERS`, in
which every entry is current: `claude.ai/code` for Claude Code and `Generated by Codex` for Codex,
each appended by its own runtime rather than chosen by the agent. `sweep.py` gains `agent_footer`,
matching a marker as the whole last line or inside the HTTPS target of a Markdown link on it, never
as that link's label and never in prose; `answered` reads it. `AGENTS.md` says an agent signs with its
own runtime's marker, that a marker is retired only when that runtime is gone, and that an internal
session or thread ID never becomes a link. Replaces the attribution-footer entry of 2026-08-16.

## 2026-08-31

**`config.env` moves to MEMORY_REPO** ([#131](https://github.com/toumix/desire/pull/131), closes
[#130](https://github.com/toumix/desire/issues/130)) — the file leaves this public repo for the
root of MEMORY_REPO, `CLAUDE.md` here stops importing it and MEMORY_REPO's `CLAUDE.md` imports
it. **Both readers move with it** — `sweep.py` and `test_sweep.py` out of `.agents/skills/`,
`session-start.sh` and `settings.json` out of `.claude/` — into MEMORY_REPO beside the file they
read, with the copies under `template/memory/` the public ones; `.agents/skills/` keeps `bob`
alone and `.claude/skills/` its symlink to it. Each reaches the config by a fixed relative path:
`sweep.py`'s `CONFIG` constant is three directories up, unchanged from before the move, the hook's
is two, and `AGENTS_CONFIG` overrides both. The sibling-clone search, its self-naming check and
its unreadable-candidate skip are removed from both. `memory_clone()` reads the config file's own
directory. The startup-script snippet in the README's Verified commits points at
`memory/.claude/hooks/session-start.sh`, and `AGENTS.md`'s Config section, the README's Get
started and `template/README.md` say where each lives and that the copies move together.
Supersedes
[#94](https://github.com/toumix/desire/pull/94), which gathered the values into one `config.env`
in this repo.

**`rel-int/quantum-reservoir` joins WORK_REPOS** (same ruling) — the routines scan three work
repos, not two. Extends the `rel-int/wiki` entry of 2026-07-29 below.

## 2026-08-26

**One memory PR per day, written by 🐦 Birdsong alone**
([#113](https://github.com/toumix/desire/pull/113), closes
[#112](https://github.com/toumix/desire/issues/112)) — `AGENTS.md`'s "one memory PR open at a
time" becomes one per day, titled with the day it covers and opened by Birdsong even when the
previous day's has not merged. `sweep.py`'s `memory` stops failing on more than one open PR and
fails on two sharing a title instead, printing the open PRs either way, in place of "at most one
is allowed — push to the oldest and close the rest".
`EVENING.md` gains "writes its turn file and one comment, never that PR's description",
`BIRDSONG.md` names Birdsong the only routine that writes it. The memory PR template's queue
stops being a table and links the board instead.

**An unanswered USER comment is reported until it is answered** (same PR, closes
[#111](https://github.com/toumix/desire/issues/111)) — `sweep.py`'s two unanswered branches ask
the new `asking` instead of their `created_at >= since` window: a question of USER's is reported
whatever its age unless the pipeline 👀'd it and it predates the window, and a sweep with no
`--since` reports every one. `closed_since` keeps its window. Reverses the windowing
[#90](https://github.com/toumix/desire/issues/90) introduced on the body branch. `AGENTS.md` says
what a 👀 now buys.

## 2026-08-24

**Agents delete their own `TODO.md` once every point is done**
([#108](https://github.com/toumix/desire/pull/108), closes
[#107](https://github.com/toumix/desire/issues/107)) — the `TODO.md` rule of `RULES.md` is split
in two: creation stays point 1, deletion becomes point 2, which replaces "never delete
it" with: once every point is `[x]` or filed as an issue, the agent deletes `TODO.md` itself,
clearing the merge gate and taking the pull request out of draft; a round of review feedback —
bot or human — starts a fresh one, the feedback quoted at the top and the fixes as boxes,
deleted again when the round is done; nitpicks are just fixed, pushed and resolved. The
never-alter-the-verbatim-prompt clause stays; same edit on discopy's copy in
[discopy#608](https://github.com/discopy/discopy/pull/608).

**Rule 4 is removed** (same PR) — only-talk-when-prompted and never-reply-unless-USER-replied-
or-🚀 are gone from `RULES.md`; `AGENTS.md`'s trusted-instructions section still binds the
routines. Same removal on discopy's copy in discopy#608.

**REVIEWER leaves the rules and the config** (same PR) — the tag-REVIEWER-once-done rule is
removed from `AGENTS.md` and `REVIEWER` from `config.env`; the summon now lives in
[discopy#608](https://github.com/discopy/discopy/pull/608)'s workflow. Supersedes the
public-repos-only scoping of [#86](https://github.com/toumix/desire/issues/86) built as
[#89](https://github.com/toumix/desire/pull/89).

## 2026-08-21

**The VM startup script wires the hook for multi-repo sessions**
([#104](https://github.com/toumix/desire/pull/104), closes
[#103](https://github.com/toumix/desire/issues/103)) — the environment's startup script writes
`/home/user/.claude/settings.json` pointing `SessionStart` at the hook by absolute path. The
snippet lands in the README's new Verified commits section, with the key setup — generate,
register as a signing key, paste into `AGENTS_SIGNING_KEY`. Extends the two hook entries below,
same day.

**The hook starts unsigned by clearing the whole signing config**
([#101](https://github.com/toumix/desire/pull/101), closes
[#99](https://github.com/toumix/desire/issues/99)) — `session-start.sh` unsets `commit.gpgsign`,
`user.signingkey`, `gpg.format` and `gpg.ssh.program`, not `commit.gpgsign` alone, and pins
`gpg.ssh.program` to `ssh-keygen` when signing turns on, overriding the environment's own.
Amends the entry below, same day.

**Commits are signed** ([#97](https://github.com/toumix/desire/pull/97), closes
[#96](https://github.com/toumix/desire/issues/96)) — the SessionStart hook turns
`AGENTS_SIGNING_KEY`, an SSH key registered on AGENT's account as signing-only, into
`commit.gpgsign`, so commits show Verified; a session without the key commits unsigned.
Extends the commits-authored-by-AGENT entry of 2026-08-20 below.

## 2026-08-20

**The config lives in `config.env`** ([#94](https://github.com/toumix/desire/pull/94)) — `USER`,
`AGENT`, `AGENT_EMAIL`, `WORK_REPOS`, `MEMORY_REPO`, `DESIRE_REPO`, `APPROVE_EMOJI`, `REVIEWER`,
`AGENT_FOOTER` and `ADOPTED_PRS` are set there, one `KEY=value` per line, `CLAUDE.md` imports it
into every session, and `AGENTS.md`'s Config section points at it rather than naming them.
`session-start.sh` reads it to set `user.name` and `user.email` globally on every remote session,
before the first commit of a turn; `sweep.py`'s `config()` parses it. Replaces the Config block
of `AGENTS.md`.

**Commits are authored by AGENT and AGENT_EMAIL** ([#93](https://github.com/toumix/desire/pull/93),
closes [#92](https://github.com/toumix/desire/issues/92)) — `AGENT_EMAIL` joins the Config, set with
`AGENT` on every clone before a turn's first commit. New rule, replaces nothing.

**`RULES.md` lands here** (same PR, closes
[#91](https://github.com/toumix/desire/issues/91)) — a verbatim copy of discopy's, imported by
`CLAUDE.md`, until [#87](https://github.com/toumix/desire/issues/87) gives it one home. `sweep.py`
reads its `TODO.md` off each AGENT-owned head in WORK_REPOS: open boxes as context, a `[WIP]` claim
past twelve hours and a branch that never carried one as findings; a branch that carried one and
deleted it at the gate is not a finding. New rule, replaces nothing.

**The sweep reads a body USER wrote** (same PR, closes
[#90](https://github.com/toumix/desire/issues/90)) — an issue or pull request USER opened is the
thread while nothing else is said on it, windowed on `created_at`; once anyone comments, that
thread's last word answers for it. Replaces reporting a body only when it carries a 🚀. Same PR
stops `answered` raising on a body with no description.

## 2026-08-18

**The sweep reads closes** ([#82](https://github.com/toumix/desire/pull/82),
closes [#81](https://github.com/toumix/desire/issues/81)) — with `--since`, the issues closed
inside the window are listed with their `state_reason` and who closed them. Extends the
sweep-reads-a-delta entry of 2026-08-14 below.

**Re-read a blocker before asking it again** ([#85](https://github.com/toumix/desire/pull/85),
closes [#73](https://github.com/toumix/desire/issues/73)) — a 🚀-able comment is re-read for an
answer before a later turn repeats it. New rule, replaces nothing.

**The sweep reports a 🚀 whatever the window** (same PR) — `--since` windows comments only, and an
approval stands until the thing it sits on closes. Narrows the sweep-reads-a-delta entry of
2026-08-14 below.

**Every write to GitHub goes through the MCP tools** (same PR, closes
[#83](https://github.com/toumix/desire/issues/83)) — `GITHUB_TOKEN` is for reads only, and a turn
asserts `mcp__github__get_me` is AGENT before its first write. `add_reply_to_pull_request_comment`
takes the 👀 on a review comment, replacing the raw POST of 2026-08-16 below. #83's third
proposal, naming the other identity in the Config, is declined.

## 2026-08-16

**👀 says received, nothing says never arrived** ([#80](https://github.com/toumix/desire/pull/80),
closes [#79](https://github.com/toumix/desire/issues/79)) — an agent reacts 👀 on the comment or
body it is picking up, before doing the work, and `sweep.py` marks a flag `👀` when anyone but
USER has. New rule, replaces nothing.

**Adopting a pull request gives it a `TODO.md`** (same PR, closes
[#76](https://github.com/toumix/desire/issues/76)) — the human prompt at the top where there is
one, the remaining work as boxes. Extends the ADOPTED_PRS entry of 2026-08-14 below.

**A pull request closing an issue uses GitHub's syntax** (same PR, closes
[#77](https://github.com/toumix/desire/issues/77)) — one keyword per issue on the same line as
its reference, and what merging closes read from `closed_by_pull_requests`. Replaces counting our
own sentences.

**The attribution footer decides authorship** (same PR, closes
[#72](https://github.com/toumix/desire/issues/72)) — a reply whose last line carries the new
`AGENT_FOOTER` config key counts as an agent's whoever posted it. Extends the
answered-by-anyone-but-USER entry of 2026-08-14 below.

**Assert the clone is complete before measuring it** (same PR, closes
[#75](https://github.com/toumix/desire/issues/75)) — `git rev-parse --is-shallow-repository`
before any behind-count or collision measurement, `git fetch --unshallow origin` if it is not.
New rule, replaces nothing.

**Every AGENT-owned PR tags REVIEWER** (same PR, closes
[#78](https://github.com/toumix/desire/issues/78)) — once its `TODO.md` is done and again after a
substantial rebuild. `REVIEWER` and `AGENT_FOOTER` join the Config, and `sweep.py` reads that
section instead of repeating it. New rule, replaces nothing.

## 2026-08-14

**ADOPTED_PRS joins the Config** ([#71](https://github.com/toumix/desire/pull/71),
closes [#70](https://github.com/toumix/desire/issues/70)) — a dict from repo to pull-request
numbers that the routines treat as AGENT-owned wherever authorship decides — sweeps, scans and
the board. Same PR adds this changelog's writing rule to its header: entries state the changes,
no explanation of why. New rule, replaces nothing.

**The memory PR description follows one template, decisions first** ([#68](https://github.com/toumix/desire/pull/68),
closes [#65](https://github.com/toumix/desire/issues/65)) — five sections ordered by what USER
has to do, 🚀 Waiting on you always first; no agent narration, proposals as bullets, everything
named on first citation. Replaces the free-form summary. Extends the description-is-summary entry
of 2026-08-11 below.

**A thread is answered by anyone but USER** ([#69](https://github.com/toumix/desire/pull/69),
closes [#67](https://github.com/toumix/desire/issues/67)) — a thread waits on us exactly when
USER posted last; which agent closed it does not matter. Replaces keying "answered" on one
hardcoded AGENT. `AGENT` leaves the script, staying the pipeline's identity everywhere else.

**The sweep reads a delta** (same PR, closes
[#64](https://github.com/toumix/desire/issues/64)) — `sweep.py` takes `--since <ISO8601>` and
filters comments and reacts on `created_at`. An argument, not a file of acknowledged ids.

**The sweep counts MEMORY_REPO's open PRs** (same PR, closes
[#63](https://github.com/toumix/desire/issues/63)) — it prints the count and fails on more than
one. Replaces reading `git log` for it.

## 2026-08-12

**Forks pull upstream, through their USER's review** ([#62](https://github.com/toumix/desire/pull/62),
closes [#61](https://github.com/toumix/desire/issues/61)) — a turn that finds the upstream `main`
ahead opens a PR pulling it in. Upstream stays untrusted for a fork until its own USER merges it
into the fork's protected `main`. New rule, replaces nothing.

**The sweep is a rule: read USER's signal before planning** ([#60](https://github.com/toumix/desire/pull/60),
closes [#52](https://github.com/toumix/desire/issues/52)) — every turn runs
[sweep.py](.agents/skills/sweep/sweep.py) over the repos in play before planning: USER comments no
agent has answered, and APPROVE_EMOJI reacts on bodies as well as comments, across both comment
endpoints. Replaces `check-approval.sh`.

**A factual status reply is not steering** ([#59](https://github.com/toumix/desire/pull/59),
closes [#54](https://github.com/toumix/desire/issues/54)) — an agent may leave one narrow kind of
reply on a non-USER thread: a factual status pointing at an artefact that already exists, taking
no position and accepting no instruction, resolving the thread if the artefact settles it.
Narrows the no-reply rule.

**A blocker on USER is asked on its PR, the same turn** (same PR, closes
[#46](https://github.com/toumix/desire/issues/46)) — a point blocked on USER becomes a 🚀-able
comment on its PR the turn it becomes blocked. New rule, replaces nothing.

**A PR states its review cost** (same PR, closes
[#48](https://github.com/toumix/desire/issues/48)) — a turn that opens or reports a PR states
lines changing existing code, lines in new files, and core modules touched. New rule, replaces
nothing.

**A ruling in a prompt PR is also an open issue** ([#56](https://github.com/toumix/desire/pull/56),
closes [#51](https://github.com/toumix/desire/issues/51)) — the turn that lands a ruling in a
prompt PR also opens an issue stating it, closed when the PR merges. Option A of #51's three;
replaces the 08-11 stopgap of copying the ruling to the board, which stays state-only.

## 2026-08-11

**The memory PR is a period, its description is the summary, and the issues get reviewed too**
([#55](https://github.com/toumix/desire/pull/55)) — three changes.

*Title covers the period, not the opening day*, extended as the period grows. Replaces "titled
with the date alone — one PR a day" from the 2026-08-07 naming rule, and closes the day-boundary
half of [#44](https://github.com/toumix/desire/issues/44).

*The description is the executive summary of the whole period, kept current*, with each agent
leaving its turn as a comment. Replaces the convention that the opening agent's message stands as
the description for the PR's life. The title-and-description halves land in memory's own
`AGENTS.md`; the Birdsong half is here.

*Review the issues as well as the PRs.* Sharpens the existing `EVENING.md` rule rather than
adding one.

## 2026-08-10

**Name a pull request, don't just number it** ([#47](https://github.com/toumix/desire/pull/47)) —
every PR and issue gets a few words of description the first time it is cited, in any context.
New rule, replaces nothing.

**Memory PRs open ready for review, not draft** — memory PRs only, not work PRs, where a draft is
what says a `TODO.md` is still open.

Same PR fixes `check-approval.sh`, which only ever queried `pulls/comments`: a 🚀 on a plain PR
comment lives under `issues/comments` and was reported as *not approved*. It now queries both.

## 2026-08-08

**The open memory PR's branch wins over the assigned one** ([#45](https://github.com/toumix/desire/pull/45),
[#44](https://github.com/toumix/desire/issues/44)) — narrows the branch clause rather than
replacing it: outside MEMORY_REPO the assigned branch still stands.

## 2026-08-06

**One memory PR open at a time, not a stack** ([#43](https://github.com/toumix/desire/pull/43)) —
if a memory PR is open, push to it; only open a new one when none is open. Replaces the stacking
clause from the 2026-08-04 entry below.

## 2026-08-04

**Memory is reserved for cross-workstream changes** ([#39](https://github.com/toumix/desire/pull/39))
— a turn that stays within one workstream writes nothing to MEMORY_REPO, its work PR is its
record; only changes affecting other PRs land in memory, whose review remains the feedback
channel. The board is rewritten by the turns that do land there. Replaces the unconditional
stacked-PR rule, and supersedes the stacking half of
[#30](https://github.com/toumix/desire/issues/30).

## 2026-07-29

**bob binds to issues, not only to reviews** ([#27](https://github.com/toumix/desire/pull/27)) —
`## Reviewing` becomes `## Issues and reviews`, and *write every comment like bob* becomes *write
like bob everywhere*. The rule itself is unchanged since [#3](https://github.com/toumix/desire/pull/3).
Two lines proposed there did not land — a `## Writing` section of its own, and a sentence defining
what an issue is.

**`rel-int/wiki` joins WORK_REPOS** — the routines now scan two repos, not one. Nothing else
changes.

**Evening scans mentions instead of reading an inbox** ([#22](https://github.com/toumix/desire/pull/22),
closes [#20](https://github.com/toumix/desire/issues/20)) — `mentions:AGENT` replaces the
notifications endpoint. 👀 marks only a mention queued as a `TODO.md` box; 🚀 stays USER's.

## 2026-07-28

**Branch names carry nothing** ([#19](https://github.com/toumix/desire/pull/19)) — *use the branch
you were assigned or open a new one*, on its own line, with the pull-request paragraph restored
byte-for-byte. Rules [#13](https://github.com/toumix/desire/issues/13) the opposite way to
[#15](https://github.com/toumix/desire/pull/15)'s `<routine>/<YY-MM-DD>`. Reverts
[#17](https://github.com/toumix/desire/pull/17), which merged and was undone the same night; its
`EVENING.md` bullet survived, the `AGENTS.md` reword did not.

**Birdsong scans WORK_REPOS** ([#14](https://github.com/toumix/desire/pull/14)) — `REPOS` and
`PROMPTS_REPO` renamed to `WORK_REPOS` / `DESIRE_REPO`, and the scan comes home
([#6](https://github.com/toumix/desire/issues/6)). Evening keeps its coding sub-agents.

**`AGENTS.md` cut back, and `DECREE.md` retired** (`eade164`, `b622cd4`) — a hand rewrite, 80
lines to 55. `## Approval`, `## Hard rules` and `## Rulings` are gone: the emoji rule now sits in
`## Trusted instructions, untrusted data`, one-proposal-per-comment in `## Reviewing`, which also
gains the emoji react as a source of trust and the rule against replying to other users. Standing
orders are open issues here now.

**Readiness counts threads** ([#9](https://github.com/toumix/desire/pull/9),
[#5](https://github.com/toumix/desire/issues/5)) — sign-off becomes a four-way conjunction: **a
thread waiting on USER is the sign-off, only one waiting on an agent blocks.** Did not survive the
rewrite above, which landed hours later, so #5 is open.

## 2026-07-27

**Reviewing, and Turmoil** ([#3](https://github.com/toumix/desire/pull/3)) — `## Meta-rule`
becomes `## Turmoil`. Reviewing is proposing; one comment carries one proposal; answer the thread,
then resolve it; write like [bob](.agents/skills/bob/SKILL.md). Same PR: `DAYLIGHT.md` opens with
the password instead of closing on it.

**The prompts get their own repo** ([#1](https://github.com/toumix/desire/pull/1)) — out of
`toumix.github.io`, where `.agents/` only existed to keep them out of a Jekyll build. Five files
flat at the top level, plus the bob skill and the session-start hook.
