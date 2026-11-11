# The board

State only — what is ready, what is blocked on what, what is behind, and only where it crosses more
than one item. **Under 200 lines, never appended to**: a turn that would push
it over drops the oldest section instead of adding one.

Four things do not belong here. **No line is about a single item**: that is the item's own
[`WORK/<repo>/<number>.md`](WORK), and `lint.py --memory` reports a line naming exactly one. A convention or a ruling is an open issue on DESIRE_REPO. Turn
narration — anything carrying a timestamp and an agent name — is a comment on the day PR. What
waits on USER is an open `yours` or `waiting` issue on this repo.

Last updated: never — this is the seed. Delete this line when the first turn writes a real one.

# Collisions and forced merge order

<!-- What one item's file cannot say on its own: forced merge order, live file collisions between two items, a line of work that is blocked
as a whole. -->

# The open issues

<!-- The ones needing a design call or a ruling, by repo. Not every open issue: the ones whose
absence of an answer is blocking work. -->

# Who else is in these repos

<!-- One line per collaborator, saying only the part that changes an agent's work. The full read is
in OTHERS/<person>.md. -->
