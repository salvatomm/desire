# `WORK/<repo>/<number>.md`

The shape of one item's note, named by the repository and the number: `WORK/discopy/489.md`. Which
items get one, who writes it and when it is deleted are in DESIRE_REPO's `AGENTS.md`.

It holds what GitHub cannot say, the five fields below and what each turn did. State, mergeable
state, checks and line counts are read live, never copied here. Five fields with the `read` date on
the first, then the log newest-first. If a field has no answer today, say
so — an empty **needs** is a claim that nothing is blocking it, and the next turn will read it as
one.

```markdown
# <repo>#<number> — <what it is, in half a line>

- **whose** <ours|login>, and whether it is ours to push to · read <date>
- **does** one or two lines. The mathematics before the plumbing
- **needs** the one thing that would move it: a read, a ruling, a merge, a fix — and from whom
- **touches** the modules it changes, and the items it collides with over which files
- **blocks** what waits on it, and what it waits on

- **<date> <phase or person>** what changed, in one line
```

An example, so the density is not a guess:

```markdown
# discopy#489 — let statements and non-strictly-associative products in closed terms

- **whose** ours · read 2026-09-01
- **does** adds `let` to the internal language of closed categories, and drops the assumption that
  the product is strictly associative, so a term can name an intermediate value
- **needs** USER's read. Nothing is waiting on an agent
- **touches** `closed.py`, `biclosed.py`, `test/closed.py` — collides with #442 and #511 on `closed.py`
- **blocks** #443's last box, which wants the `trace(0)` fix this carries

- **2026-09-01 🌙 Evening** resolved 19 review threads — 8 fixed, #693 and #694 filed for two,
  4 design questions left for a human, marked it ready
- **2026-08-27 🌤️ Daylight** designed the `let` encoding with USER, wrote the plan
```

**`read` is the date the note was last true.** The sweep compares it with the item's own last
update, so a note older than its item is reported as possibly stale. A turn that re-reads the item
updates the date; a turn that does not, leaves it.

**The log is the point**, and it keeps the last five turns: what 🐦 Birdsong reads to see where an
item stands, and the durable trace an interactive session leaves of work that stayed on its own PR.
One line per turn, in the past tense, saying what *changed* — not what was scanned or read. Older
lines are in the file's git history.

A merge of the target branch is the one to get right. It is housekeeping, so it never earns its own
clause beside real work: a turn that merged `main` and then fixed three review threads logs the
three threads. But when it is the whole of the turn it is logged, plainly and alone — *"merged
`main`, nothing else"* — because the branch did move and because a night that finished nothing should
read that way.
