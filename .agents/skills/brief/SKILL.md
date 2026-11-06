---
name: brief
description: Turn USER's few lines of intent into a prompt that a fresh session can run with no memory of this one, and post it for USER to read and 🚀 instead of running it. Two shapes, an issue brief (a change to a code repo, a next repo above all) and an experiment brief (a run whose result goes to a write-up). Use when USER says "write the issue / brief / prompt for X", "don't implement", or hands over an idea too large to run in one sitting; before Evening or another session picks it up.
---

# Brief

USER writes the intent; the agent writes the prompt; USER reads the prompt, which is cheaper than
reading a diff; another session runs it. A brief is design, so it is never delegated
([DAYLIGHT.md](../../../DAYLIGHT.md)), and writing one runs nothing: no code, no run, no branch.

## Before writing

1. **Copy USER's words verbatim**, with the link if they were posted. They head the brief and are
   never edited: in a repo that keeps a `TODO.md`, they become its verbatim prompt.
2. **Read what the brief will touch**: the files on today's `main`, the item's `WORK/` note, open
   items it collides with (the board), the target repo's own `AGENTS.md`. A brief written from
   memory carries yesterday's code into every step after it.
3. **Ask, do not guess.** A sentence of USER's that reads two ways is a question in the session
   (or a 🚀-able comment), not a choice the brief makes quietly.

## Issue brief

For a change to a code repo. In this order:

- **Intent**: USER's words, quoted.
- **The change in mathematical terms**: the structure, the law or the construction, with a
  reference when there is one; then the data structures that carry it, and whether they fit or
  must move. A change that will not state this way is not ready to brief.
- **Where**: files and classes by path, the level of the hierarchy each change belongs at, and
  what is out of scope.
- **Slices**: each one pull request that a reader finishes in one sitting, in merge order, with
  its review cost (lines changing existing code, lines in new files, core modules touched).
- **Done**: the checks that must pass, by command, and the test or property that would fail on
  today's `main` and pass after. "CI green" alone is a proxy.
- **Boxes**: the slices as `[ ]`, ready to become the `TODO.md` of the first branch.

In a next repo, say whether the work is meant for upstream; if so, the slices are also the
upstream pull requests USER may later ask for.

## Experiment brief

For a run whose result is written up, e.g. a notebook page. In this order:

- **Intent**: USER's words, quoted.
- **Hypothesis**, and **the result that would refute it**, as a number, written before anything
  runs. A brief without one reports whatever it finds as success.
- **What it decides**: which next step each outcome picks. An experiment that cannot change a
  decision is not run.
- **Baseline and controls** at matched budget, and the metric, continuous where possible.
- **Budget**: compute, wall-clock timeout per call, retries, seeds, a kill rule, all bounded by
  the target repo's own rules on where runs go and how credentials are used.
- **Recorded with the result**: source and config hashes, seeds, run ids, where the summary lands.
  Data and weights never go in git.

For training runs, load `experiment-ladder` too where it is installed: it splits the budget into
rungs, and each rung gets its own brief.

## The stand-alone test

Before posting, read the brief as a session that has seen nothing else. Each `#N` says what it is,
each path exists, each check is a command, and nothing says "as discussed". If the brief cannot
stand alone, the design is not finished: go back to USER, not forward to code.

## Posting

- One brief is one issue on the repo where it runs, or one comment on the item it extends, so
  USER can 🚀 it whole ([Issues and reviews](../../../AGENTS.md#issues-and-reviews)). Never a
  batch of briefs in one turn.
- Write like [bob](../bob/SKILL.md): the brief is read by USER first, the runner second.
- Run `post-check` on the draft before posting it, where that skill is installed.
- The 🚀 makes it the plan, not its premises true: the session that runs it re-reads the files it
  names before the first edit, and a premise that no longer holds goes back to the brief, not
  around it.
- Record the brief in the item's `WORK/` note; the session that runs it starts from that note.
