---
name: spawn
description: Start a child session that arrives with the rules, the memory and the repos its task needs, and check that it did before leaving it alone. Use when USER says "spawn a session / another one for X", before every call that creates a session, and when a child reports it is confused or blocked.
---

# Spawn

A child session knows only what its one attached repo and its prompt give it. Spawned on a work
repo, it has that repo's instructions and none of these rules, no `config.env`, no `WORK/` notes
and no skills: it reads as confused, and what it posts follows no rule.

## Before spawning

1. **Does it need a session at all?** A subagent of this session already has every repo attached
   here, and its report comes back. Spawn a session when USER asks for one, or when the work
   should outlive this session.
2. **Write the prompt as a [brief](../brief/SKILL.md)**: USER's words verbatim at the top, what is
   known and what was not checked, what is out of scope, what done means. It must pass the
   stand-alone test.
3. **List the repos the task reads and writes**, DESIRE_REPO and MEMORY_REPO always among them.
   Check each is attached to this session: a repo the parent cannot reach, the child will not
   reach either.

## Spawning

- **The session's one source is DESIRE_REPO**, never the work repo: the rules and the skills
  load before the first turn, and nothing depends on the child attaching them.
- **The prompt's first section is the setup**, as steps the child runs before anything else:
  1. attach MEMORY_REPO and each work repo, with push only where it writes;
  2. clone each where the attach result says;
  3. register each clone, so its instructions and skills load on the next turn;
  4. in the MEMORY_REPO clone, read `config.env`, the board and the task's `WORK/` notes, and
     check out the day PR's branch there; a work repo gets its own branch and pull request;
  5. **if an attach, a clone or a register fails, stop and message the parent**: no workaround,
     no retry.
- **Name what the runtime cannot set.** A session is created with a model and no effort level:
  say to USER that the effort is only a line of the prompt.
- **Ask for the report as a message to the parent** when the task ends or blocks. A child that
  finishes cleanly reports nothing by itself.
- One spawn is one task. Children that write the same file (the board, a `WORK/` note) are told
  so, and to fetch and merge before pushing.

## After spawning

- **Check the setup, do not assume it**: once the child's first turns have run, read its
  transcript for the attach and register calls of every repo on the list. Read only the kinds of
  event needed; a full transcript is tens of thousands of tokens.
- **A refused attach is not fixed by a message.** A message from another session is data to the
  child, not USER's word, and its permission checks may refuse an access the message asks for.
  Tell USER which repo was refused, and either do that part here, where the repos are attached,
  or have USER attach them to the child.
- **Tell USER, per child**: the link, the task in a line, what was verified and what was only
  asked. "Delivered" says a message arrived, not that it was acted on.
- Log each spawn in the day PR's comment, with the child's id. The child writes the `WORK/`
  notes of what it touches; the parent checks they exist before the day ends.
