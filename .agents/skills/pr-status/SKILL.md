---
name: pr-status
description: Measure one or more pull requests live and print a verdict line (waiting-on-agent, waiting-on-USER, ready, GO). Use before writing any status word about a PR (green, clean, ready, waiting, blocked) in a WORK note, the board, a PR description or a comment, before merging, and to check the item numbers a board or note cites.
---

# PR status

Run from the MEMORY_REPO clone, so `config.env` is found (else `--config FILE` or `AGENTS_CONFIG`):

```shell
python3 <DESIRE_REPO clone>/.agents/skills/pr-status/pr_status.py owner/repo#N [owner/repo#M ...]
```

One line per pull request: head SHA, the UTC time it measured, state, `mergeable_state`, behind/ahead
of the base, check runs on the head, unresolved review threads split by who must answer, `TODO.md`
boxes, USER's approval, then `-> verdict (reasons)`; a merged or closed one prints only that. Exit 0
on ready, GO, merged or closed, 1 on waiting, 2 when a read failed or the verdict is `incomplete`.

- **Writing status.** Run it first and quote its line, SHA and time included. Never copy a status
  word from an older note. A field that says `n/a` was not measured: do not fill it in.
- **Merging.** Run it with `--gate`, which prints the full 40-character SHA and exits 0 only on GO.
  Merge with that SHA as `expectedHeadSha`. Any push after that needs a new run.
- **Cited items.** `--cited FILE --repo owner/repo` prints the live state of every `#N` in the file
  (open, closed by, merged by) next to the line citing it; a bare `#N` reads as `--repo`, a short
  name as the WORK_REPO it ends. The list it calls advisory is lines whose words may disagree with
  that state: read each one, it is not a finding by itself.
- `--json` prints every field instead of the line.

The rules it measures are [Reading CI](../../../OPERATIONS.md#reading-ci) and
[Merging on approval](../../../OPERATIONS.md#merging-on-approval).

## When the token cannot read

Review threads come from the REST route `pulls/N/ccr/review_threads` where the session serves one,
else from GraphQL. Where neither, or the repo, is readable, the field prints `n/a`
and the verdict is `incomplete` unless something already waits on an agent. Read the same data
through the MCP tools instead, with `mcp__github__pull_request_read` on the pull request:

| method | gives |
|---|---|
| `get` | head SHA, state, draft, `mergeable_state` (read again after 2s while `unknown`) |
| `get_check_runs` | check runs on the head; never `get_status`, which is empty on Actions |
| `get_reviews` | USER's latest APPROVED, CHANGES_REQUESTED or DISMISSED review and its `commit_id` |
| `get_review_comments` | threads with `is_resolved` and their comments |

Threads alone can be handed back: save the `get_review_comments` answer to a file, as a JSON list
of its pages when `pageInfo.hasNextPage` is true, and pass `--threads FILE` with that one pull
request; the rest is read live. A file missing its last page is refused.

Decide in this order, first match wins:

| condition | verdict |
|---|---|
| merged or closed | that state |
| draft; `dirty` or `behind`; a check failed; a check queued, running, or expected and never created; `TODO.md` present; an unresolved thread whose last comment is not the agent's | waiting-on-agent |
| any field unread, or `mergeable_state` still `unknown` | incomplete |
| an unresolved thread whose last comment is the agent's | waiting-on-USER |
| no USER approval on this exact head SHA, or `mergeable_state` neither `clean` nor `has_hooks` | ready |
| otherwise | GO |

A comment is the agent's when AGENT wrote it, or USER's account did and its last line carries an
AGENT_FOOTERS marker, as [Matching an attribution footer](../../../OPERATIONS.md#matching-an-attribution-footer)
says. Expected checks are the required checks of the base branch's rulesets and branch protection.
