# BIRDSONG.md

🐦 Birdsong plans the day, asynchronously, before USER opens any 🌤️ Daylight session. It runs
these steps in order:

1. **Run the sweep**, and 👀 what it picks up
   ([`OPERATIONS.md`](OPERATIONS.md#reading-the-sweep)), while the previous day PR is still open.
2. **Open the day.** Merge the previous day PR on MEMORY_REPO and open today's
   ([`OPERATIONS.md`](OPERATIONS.md#the-day-pr)).
3. **Clear the notes.** Delete the `WORK/` note of every item the sweep finds merged or closed, in
   every WORK_REPO, and write the missing ones. A WORK_REPO it cannot reach is an issue on MEMORY_REPO
   naming the repo, labelled `yours`, not a line in the summary.
4. **Read where each item stands** from its `WORK/` note. Who did what since its last turn is the
   diff of `WORK/` plus the comments of every day PR since then, however many there were. Verify live only what it states as fact: each
   WORK_REPO's default-branch SHA, and the open AGENT-owned PRs, which the sweep checks against
   `WORK/`.
5. **Merge down.** Merge each upstream `main` into its next repo, and report the drift and its
   trend on the board ([`OPERATIONS.md`](OPERATIONS.md#measuring-drift)). The upstream slices it
   proposes, with what each costs to read, go under `Agent proposals`.
6. **Review** the open issues and pull requests, in WORK_REPOS and DESIRE_REPO, and plan the day.
7. **Update the board**: what collides with what and what merge order is forced, nothing else.
8. **Write the day PR's description**, the only routine that does, to the shape in MEMORY_REPO's
   `.github/PULL_REQUEST_TEMPLATE.md` ([public copy](template/memory/.github/PULL_REQUEST_TEMPLATE.md)).
   Keep it as short as the day can be said: an honest activity account that answers "did Evening
   even launch" on its own, covering every day PR since the last description, and linking the
   board and MEMORY_REPO's open issues rather than repeating them.
9. **Look at the pipeline itself**, and file on DESIRE_REPO any issue it finds with it.
10. **Close the turn**: the `WORK/` notes it touched, and one comment on the day PR. The PR review is
    USER's feedback, not its own.
