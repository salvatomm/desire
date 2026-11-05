---
name: work-notes
description: Check that every item AGENT touched this turn has its WORK/<repo>/<number>.md note with a log line from the turn, draft the day-PR comment's item list, and lint every note against the WORK template. Use before ending any turn, Daylight and child sessions included, and after writing or rewriting WORK/ notes.
---

# WORK notes

The rules are [Memory](../../../AGENTS.md#memory) and
[One file per open item](../../../AGENTS.md#one-file-per-open-item), their mechanics
[WORK notes](../../../OPERATIONS.md#work-notes), and the shape
[`template/memory/WORK/TEMPLATE.md`](../../../template/memory/WORK/TEMPLATE.md).

Run from the MEMORY_REPO clone with the day PR's branch checked out. On `main` or the session's
assigned branch the notes written today are missing, and both commands report false findings.
`config.env` is found as `--config FILE`, else `AGENTS_CONFIG`, else `./config.env`.

## Before ending a turn

```shell
date -u +%Y-%m-%dT%H:%M:%SZ        # at the start of the turn: keep it as <since>
python3 <DESIRE_REPO clone>/.agents/skills/work-notes/work_notes.py touched --since <since>
```

It searches every WORK_REPO, MEMORY_REPO and DESIRE_REPO for issues and pull requests involving
AGENT updated since `<since>`, the day PR left out, and prints:

- `owner/repo#N: no note`: an open item with no `WORK/<repo>/<N>.md`. Write it.
- `no log line dated <day> or later`: the note has no line from this turn. Add one.
- `closed, note not deleted`: delete the note.
- `Day-PR comment:` one `- owner/repo#N (title): ` line per touched item. Finish each line with
  what the turn did, drop the ones it only read, and post it as the turn's comment on the day PR.

Exit 0 clean, 1 findings, 2 when `config.env` or a repo could not be read: that repo prints
`n/a (<code>)`; list its items with the GitHub MCP search tools and check their notes by hand.
Fix, commit, push, and run it again until every finding left is for an item this turn did not
touch.

`involves:` covers authoring, commenting, mentions and assignment, at any time: an item AGENT
was in once and someone else updated since is listed too, so skip a finding for an item this turn
did not touch. A push to someone else's pull request, or a review with no comment, is not found:
add those items by hand.

## Linting the notes

```shell
python3 <DESIRE_REPO clone>/.agents/skills/work-notes/work_notes.py lint
```

One line per finding, `WORK/<repo>/<N>.md: <finding>`: a title that is not `# <repo>#<N> — ...`
or names another item, fields other than the template's or out of its order, no `read <date>` on
the first field, more than five log lines or a log not newest-first, and `<field>: copies <kind>`
for CI green or red, a check count, a mergeable state in backticks or a `+N/−M` line count. In the
log, only a line that opens with a mergeable state (`<day>: copies mergeable state`) is flagged.

Exit 0 clean, 1 findings, 2 when there is no `WORK/` beside `config.env` or the template cannot be
read. The field names come from the template itself; `--template FILE` checks against another copy.
