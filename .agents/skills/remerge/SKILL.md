---
name: remerge
description: Merge a pull request's target branch into its branch locally, the safe way, without pushing. Use when an open pull request is behind or dirty against its target, before re-checking or merging it, and with --dry-run to measure whether it would merge.
---

# Remerge

First read the WORK_REPO's own rules for shared branches (for example its `RULES.md`): history is
append-only, so a branch takes its target by merge, never by rebase or force-push. The clone must
be complete: [OPERATIONS.md](../../../OPERATIONS.md#measuring-against-git-history).

Check the pull request's branch out in a worktree under its own name, so `origin/<branch>`
exists, and name the branch the pull request targets, read from the pull request itself: a
stacked pull request targets another branch, not `main`.

```bash
python3 <DESIRE_REPO clone>/.agents/skills/remerge/remerge.py <worktree> <base> --dry-run
python3 <DESIRE_REPO clone>/.agents/skills/remerge/remerge.py <worktree> <base> \
    --check '<the repo lint and test commands>' --trailer '<attribution line>'
```

Run from the MEMORY_REPO clone, or pass `--config <path to config.env>` (or set `AGENTS_CONFIG`):
a real run refuses to commit unless git's identity is AGENT and AGENT_EMAIL.

What it does, in order:
1. Unshallows the clone and fetches `origin/<base>` and `origin/<branch>`; stops on uncommitted
   changes or when `origin/<branch>` has commits the worktree lacks.
2. Prints `up to date` when the branch already contains the base.
3. `--dry-run` merges in memory (`git merge-tree`), reports what a real run would meet and
   writes nothing.
4. A real run is `git merge --no-ff --no-commit`. A conflict in `CHANGELOG.md` alone resolves to
   the base's file plus the blocks the branch added since the merge base, each placed after the
   line it followed; a block the base already has is dropped. Any other conflict aborts.
5. Lists every line in the merged tree that still imports or uses a module or a top-level name
   the base deleted or renamed since the merge base.
6. Aborts if any file's own change on the branch was lost or grew in the merged tree; a change
   the base already made the same way does not count.
7. Runs `--check` in the worktree, aborts if it fails, then commits `Merge <base> into <branch>`,
   a line on how `CHANGELOG.md` was resolved when it was, and the trailers.

Exit codes: 0 merged or up to date, 1 stale names to fix (dry run: also conflicts), 2 stopped
or unreadable, 3 a change lost or grown, 4 the check failed. Exit 1 on a real run has committed;
every other stop aborts the merge and leaves the branch as it was.

Gotchas:
- It never pushes. Push with `git push origin HEAD` only after fixing what step 5 lists and
  rerunning the checks; if it says the base moved again, run it again first.
- A push voids an approval on the old commit
  ([OPERATIONS.md](../../../OPERATIONS.md#merging-on-approval)): it prints the old and new SHA
  for the comment asking again. A review bot may not re-review a push that only merges the base.
- It stops on a `CHANGELOG.md` the branch edited rather than only added to, or whose added block
  has no unique place in the base's file: resolve that by hand, keeping both sides' meaning,
  never with `--ours`, `--theirs` or a union driver.
- A dated heading the branch added keeps its own date; move the entry under the right one.
- Step 5 reads one line at a time: a name inside a multi-line import list is missed.
