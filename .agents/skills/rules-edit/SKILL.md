---
name: rules-edit
description: Change DESIRE_REPO's rule files (AGENTS.md, OPERATIONS.md, the role files, template/, CHANGELOG.md) in one review round. Use before writing any rules PR, and again before every push to it, review rounds included.
---

# Rules edit

The ceremony itself is in [Turmoil](../../../AGENTS.md#turmoil); the merge gate is
[Merging on approval](../../../OPERATIONS.md#merging-on-approval). This is the order that keeps
a rules PR to one round.

1. **Look for the ruling first.** Search DESIRE_REPO's open issues with `Ruling` in the title,
   and grep [`CHANGELOG.md`](../../../CHANGELOG.md) for the topic's key words. If one exists,
   build on it and cite it; do not open a second issue or ask USER again.
2. **Quote USER verbatim**, with the link. Change only what those words cover:
   - a deletion stays a deletion: delete the line, put nothing in its place;
   - no clause about something USER did not raise (no new `never`, `rather than`, `instead of`);
   - no reason, history or provenance in a rule ([AGENTS.md](../../../AGENTS.md)): USER's quote
     goes in the changelog entry;
   - a rule lives in one file and the others link it: `lint.py` fails on any 8-word run two rule
     files share;
   - no installation values (USER, AGENT, repo names, private links): the repo is forkable.
3. **Keep copies in step.** When a file under [`template/`](../../../template) changes, change
   its copy in the MEMORY_REPO clone the same turn
   ([Finding config.env](../../../OPERATIONS.md#finding-configenv)), and run
   `lint.py --memory <MEMORY_REPO clone>`, which fails on a listed copy that differs.
4. **After a rename or a cut, re-read every changed sentence whole**: articles (`a item`), a
   condition the old wording carried, a name that still appears elsewhere.
5. **Write the changelog entry.** Copy the shape of the top entries of
   [`CHANGELOG.md`](../../../CHANGELOG.md), under a `## YYYY-MM-DD` heading for today at the top:

   ```markdown
   **<the rule as it now reads>** (`<file>`, `<file>`) — <what changed, no why>. USER:
   *"<verbatim quote>"*. Ruling: #<issue>.
   ```

6. **Check, before every push**, from the MEMORY_REPO clone so `config.env` is found:

   ```shell
   python3 <DESIRE_REPO clone>/.github/lint.py
   python3 <DESIRE_REPO clone>/.agents/skills/rules-edit/rules_diff.py origin/main \
       --repo <DESIRE_REPO clone>
   ```

   `rules_diff.py <base>` reads commits only, `git diff <base>...HEAD` (`--head REF` for another branch,
   `--config FILE` or `AGENTS_CONFIG` for another config). Exit 0 clean, 1 findings, 2 a read
   failed (`n/a`, not clean).
   - **Finding**: an added line outside `CHANGELOG.md` naming USER, AGENT, AGENT_EMAIL, an owner
     of WORK_REPOS or MEMORY_REPO, or one of their repo names as a word or `name#N`. A repo name
     the base already uses as a plain word (`memory`) is not one. Reword it; `--allow WORD` only
     for a word the repo uses in its plain sense.
   - **Advisories**, each to read, not to obey: a reason word in an added changelog line; a new
     comment in `.py`, `.sh` or `.yml`; a new `never`/`instead of` clause, to hold against USER's
     quote; a removed `only`/`every`/`never`/`unless`/`once` clause no sentence on the branch still
     says; a backticked name or `def` that left a file and is still used elsewhere; a changelog
     entry missing, not at the top, or not under the date of the last commit.
7. **Merge `main` in before asking for approval**, and again whenever another rules PR lands
   first. Re-run step 6 on the merge.
