---
name: post-check
description: Lint a draft before posting it on GitHub — a pull request body, a comment, an issue, a day PR description, or the commit messages of a branch about to be pushed to a public repo. Checks closing keywords, the attribution footer, private repo names and denylisted words, and lists each item's first mention to check it says what the item is. Use after writing the draft with bob and before every post or push; run it again with --verify-closes after a pull request is opened or its body edited.
---

# Post check

[bob](../bob/SKILL.md) sets the voice; this checks the mechanics. Write the draft to a file, then
run from the MEMORY_REPO clone, so `config.env` is found (else `--config FILE` or `AGENTS_CONFIG`):

```shell
python3 <DESIRE_REPO clone>/.agents/skills/post-check/post_check.py draft.md --target owner/repo \
    [--denylist <MEMORY_REPO clone>/<denylist file>] [--range BASE..HEAD --repo-dir DIR [--signed]]
```

`--target` is the repo the post goes to. `-` reads the draft from stdin. Exit 0 clean, 1 findings,
2 a read failed (that part prints `n/a`; it is not clean).

What it finds:

- **Closing keywords** (`close`, `fix`, `resolve` and their forms), outside code: a keyword
  followed by several references (`Closes #1, #2`), a reference on the next line, and
  `Closes name#N` without the owner. Write `Closes #1` and `Closes #2`. The rule is in
  [Issues and reviews](../../../OPERATIONS.md#issues-and-reviews).
- **Footer**: the last non-empty line carries exactly one AGENT_FOOTERS marker, read as
  [Matching an attribution footer](../../../OPERATIONS.md#matching-an-attribution-footer) says;
  a bare URL line counts as a link target. A second footer line higher up is a finding too.
- **Public target** (skipped when the target is private): every WORK_REPOS or MEMORY_REPO repo
  named as `owner/repo` or `name#N` that is private or that the token cannot read, and every line
  matching a regex of `--denylist` (one per line, `#` comments), code included. The denylist lives
  in MEMORY_REPO; this skill ships none. With `--range`, the commit messages are scanned too. Fix
  every hit before the first post or push.
- **Commits** (`--range`): each author is AGENT <AGENT_EMAIL>; a bad or revoked signature is a
  finding; unsigned commits are listed, and are a finding with `--signed`. See
  [Identity and signing](../../../OPERATIONS.md#identity-and-signing).
- **Advisory, not a finding**: the first mention of each `#N` with the words around it. Read each
  one: if the words do not say what the item is, add a few.

Gotchas:

- A repo that prints `unreadable (HTTP 403), so private` may only be out of this session's reach.
  Check its visibility with the GitHub MCP tools; if it is public, pass `--public owner/repo` and
  run again. Never pass it for a repo you did not check.
- An unreadable target is treated as public, so every check still runs.
- A repo named only in words ("the docs") is not caught.

## After posting

```shell
python3 .../post_check.py draft.md --target owner/repo --verify-closes owner/repo#PR
```

This compares the issues the body's keywords close with the pull request's GraphQL
`closingIssuesReferences`, both ways. Where GraphQL is not readable it prints `n/a` and exits 2:
then read each issue the body closes with the GitHub MCP `issue_read` (`get`) and check its
`closed_by_pull_requests` names the pull request. Fix a mismatch by editing the body, then run
the check again.
