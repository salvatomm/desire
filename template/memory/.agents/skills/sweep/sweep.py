#!/usr/bin/env python3
"""Sweep open PRs and issues for USER signal the pipeline has not acted on:
bodies and threads where USER spoke last, APPROVE_EMOJI reacts from USER, the
issues closed inside the window, MEMORY_REPO's open-PR count, the state of
each AGENT-owned `TODO.md` and whether every open item of a WORK_REPO has its
`WORK/<repo>/<number>.md` note in MEMORY_REPO. A finding is marked 👀 when the
pipeline has reacted to say it received it. config.env is the ground truth for
USER, the repos and the emoji, and it sits at the root of this clone;
AGENTS.md's rules say what to do with a finding.

Usage: sweep.py [--since <ISO8601 UTC, e.g. 2026-08-18T00:00:00Z>] <owner/repo>
                [number...]
       # no numbers: every open PR and issue; --since windows the closes
       # and quiets a question the pipeline already 👀'd
Exit 0 and "clean" on a clean sweep, exit 1 with one line per finding, exit 2
when GitHub could not be read — an incomplete sweep is neither clean nor a
finding, and reading it as clean is how a live 🚀 goes unanswered. Open
`TODO.md` boxes are printed as context and do not make the sweep dirty.
"""
import base64
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

BOX = re.compile(r"^\s*[-*] \[([^]]*)\]")
CLAIM = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?"
                   r"(?:Z|[+-]\d{2}:?\d{2})?)?")
STALE = datetime.timedelta(hours=12)
CONFIG = pathlib.Path(__file__).parents[3] / "config.env"
FOOTER_LINK = re.compile(r"\[[^\]]*\]\((https://[^\s)]+)\)")


def find_config():
    """`config.env` at the root of the clone this file lives in. This script
    is in MEMORY_REPO because the config is, so there is nothing to search
    for: one is three directories up from the other, in the live repo and in
    the template alike. AGENTS_CONFIG overrides, which is how the tests point
    at one of their own."""
    return pathlib.Path(os.environ.get("AGENTS_CONFIG") or CONFIG)


def config(path):
    """config.env as a dict, so that the pipeline is configured in one place
    and this script hard-codes no repo and no agent. A value is everything
    after the first `=`; WORK_REPOS is a comma-separated list and ADOPTED_PRS
    space-separated `repo:number,number` entries; AGENT_FOOTERS a
    comma-separated list of the markers that identify an agent-authored post,
    each one current. Blank lines and `#` comments are skipped — the file is
    written by hand and the seed ships commented — while any other line
    carrying no `=` raises rather than parsing to a key nothing will look up,
    and a key the file does not set is absent, so a caller reading it raises
    too."""
    setup = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"config.env: no key in {line!r}")
        setup[key.strip()] = value.strip()
    if "WORK_REPOS" in setup:
        setup["WORK_REPOS"] = setup["WORK_REPOS"].split(",")
    if "AGENT_FOOTERS" in setup:
        setup["AGENT_FOOTERS"] = [
            marker.strip() for marker in setup["AGENT_FOOTERS"].split(",")
            if marker.strip()]
    if "ADOPTED_PRS" in setup:
        setup["ADOPTED_PRS"] = {
            repo: [int(number) for number in numbers.split(",") if number]
            for entry in setup["ADOPTED_PRS"].split()
            for repo, _, numbers in [entry.partition(":")]}
    return setup


def get(repo, path):
    """A GitHub REST resource, every page of a listing. A page holds 100 and
    `discopy/discopy` had 153 open items the day this stopped reading one page:
    the tail is the oldest, so a 🚀 on an old issue was invisible for good.
    Unauthenticated GETs work on public repos but are rate-limited to 60/hr;
    GITHUB_TOKEN or GH_TOKEN is used when set."""
    results, page = [], 1
    while True:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/{path}"
            + ("&" if "?" in path else "?") + f"per_page=100&page={page}",
            headers={"User-Agent": "sweep",
                     "Accept": "application/vnd.github+json"})
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(request) as response:
            items = json.load(response)
        if not isinstance(items, list):  # a single issue, comment or user
            return items
        results += items
        if len(items) < 100:
            return results
        page += 1


def review_comments(repo, number, body):
    """An issue has no review comments, and the item itself says so: GitHub
    numbers issues and pull requests in one space and puts a `pull_request`
    key on the ones that are pulls, which `item` has already read. So the
    pulls/ endpoint is never asked about an issue at all, rather than asked
    and forgiven a 404.

    That distinction used to be the status code, and it is not ours to
    rely on: behind a gateway the same request answers 403, which this
    raises — rate-limited or forbidden is a listing nobody read, and
    swallowing it as no comments is what makes an unreadable thread look
    answered. Reading it as "not a pull request" instead would be the same
    bug wearing the other mask. Asking one fewer request per issue is the
    smaller half of the reason."""
    if "pull_request" not in body:
        return []
    return get(repo, f"pulls/{number}/comments")


def reactors(repo, kind, target, emoji, cache):
    """Who reacted with `emoji` on a body or comment, and when. The counts come
    with the target, so only the ones carrying it cost a request, and the
    listing is cached since both emojis are read off the same one."""
    if not target["reactions"][emoji]:
        return []
    if kind not in cache:
        cache[kind] = get(repo, kind)
    return [reaction for reaction in cache[kind] if reaction["content"] == emoji]


def closed_since(repo, since):
    """The issues closed inside the window, with why and by whom. USER answers
    some questions by closing the issue, which leaves no thread to read and no
    open item to walk. One listing per repo, which carries the closer as well
    as the reason; without a window there is no delta, hence nothing."""
    for issue in get(repo, f"issues?state=closed&since={since}") if since else []:
        if "pull_request" in issue or issue["closed_at"] < since:
            continue
        closer = issue.get("closed_by") or {}
        reason = f" {issue['state_reason']}" if issue["state_reason"] else ""
        yield (f"#{issue['number']} closed{reason} by "
               f"{closer.get('login', 'unknown')}: " + issue["html_url"])


def approved(repo, kind, target, setup, cache):
    """Whether USER's APPROVE_EMOJI is on the target. No `since`: a react has no
    answered state, so a window hides a live approval as readily as an old one,
    and every approval on a swept target is reported whatever its age."""
    return any(
        reaction["user"]["login"] == setup["USER"]
        for reaction in reactors(
            repo, kind, target, setup["APPROVE_EMOJI"], cache))


def seen(repo, kind, target, setup, cache):
    """" 👀" when the pipeline has reacted to say it received the instruction,
    "" when nothing has: a flag alone cannot tell the two apart. No `since` —
    an old 👀 still says received."""
    return " 👀" if any(
        reaction["user"]["login"] != setup["USER"]
        for reaction in reactors(repo, kind, target, "eyes", cache)) else ""


def agent_footer(body, setup):
    """Whether `body`'s last line is one of AGENT_FOOTERS.

    There is no single signature and there cannot be: the marker is whatever
    each agent's own runtime appends, which the agent does not choose. Claude
    Code emits `_Generated by [Claude Code](https://claude.ai/code)_` on every
    post it makes, Codex emits its own line, and both mean the same thing —
    AGENT posted this from USER's handle. So every marker in the list is
    current, none is historical, and retiring one is what would make our own
    replies read as USER's unanswered questions.

    A marker counts two ways and no others: as the whole final line, or inside
    the HTTPS target of a Markdown link on that line — which is how a URL token
    matches the footer wrapping it. A link's *label* never counts, however
    exactly it reads: `[Generated by Codex](https://anywhere-at-all)` would
    otherwise let any destination silence a thread, and the label is the half a
    human types. A runtime that wants its linked footer recognised puts the URL
    token in this list, the way `claude.ai/code` already is. Nor does a marker
    count in prose: a line merely mentioning one is a human writing about the
    convention, not an agent following it.
    """
    line = ((body or "").strip().splitlines() or [""])[-1].strip().strip("_*")
    targets = FOOTER_LINK.findall(line)
    return any(line == marker or any(marker in target for target in targets)
               for marker in setup.get("AGENT_FOOTERS", []) if marker)


def answered(comment, setup):
    """Whether anyone but USER wrote this, the footer deciding for an agent
    post from USER's account. An issue with no description has a `None` body."""
    return (comment["user"]["login"] != setup["USER"]
            or agent_footer(comment["body"], setup))


def asking(repo, kind, target, setup, since, cache):
    """The 👀 flag when `target` is a question of USER's still waiting on us,
    `None` when it is not: either somebody answered it, or the pipeline reacted
    👀 to say it is in hand and `since` puts it before the window. Unanswered is
    a condition rather than an event, so the window never hides one on its own —
    a sweep with no `--since` reports every last question, and a 👀 is what
    quiets an old one."""
    if answered(target, setup):
        return None
    flag = seen(repo, kind, target, setup, cache)
    return None if flag and target["created_at"] < since else flag


def memory(repo):
    """MEMORY_REPO holds one open PR per day, checked whatever the window since
    it is an invariant rather than a delta. Several open at once is USER not
    having merged the past days, which is theirs and no finding of ours; two
    under one title is a day written twice, which is ours. The count and the
    URLs are printed either way, so a turn sees what is waiting to be merged
    without the sweep calling it dirty. When any are open the newest is named
    as the branch to cut a new day's PR from, not `main`, so unmerged days
    stack rather than conflict on `README.md`/`USER_TODO.md` (desire#144)."""
    open_prs = get(repo, "pulls?state=open")
    print(f"{repo}: {len(open_prs)} open PR(s)"
          + "".join("\n  " + pr["html_url"] for pr in open_prs), file=sys.stderr)
    if open_prs:
        newest = max(open_prs, key=lambda pull: pull["created_at"])
        print(f"{repo}: base a new day's PR on {newest['head']['ref']!r}"
              f" ({newest['title']!r}, the newest still open), not main, so"
              " unmerged days stack rather than conflict (desire#144)",
              file=sys.stderr)
    days = {}
    for pull in open_prs:
        days.setdefault(pull["title"], []).append(pull["html_url"])
    return [f"{repo}: {len(urls)} open PRs titled {title!r}, one a day is the"
            " rule — push to one and close the rest: " + ", ".join(urls)
            for title, urls in days.items() if len(urls) > 1]


def heads(repo, cache):
    """Every open pull request by number. `TODO.md` is read off the head
    commit, which the listing already carries, so the whole repo costs one
    request rather than one per pull request."""
    if "heads" not in cache:
        cache["heads"] = {pull["number"]: pull
                          for pull in get(repo, "pulls?state=open")}
    return cache["heads"]


def contents(repo, path, ref):
    """A file at one commit, `None` when that commit does not carry it: a
    missing `TODO.md` is a finding here rather than an error. Undecodable bytes
    are replaced rather than raised, since one unreadable file would otherwise
    abort the whole sweep. `validate=True` is wrong here — GitHub wraps the
    base64 it serves, which the strict decoder rejects."""
    try:
        blob = get(repo, f"contents/{path}?ref={ref}")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    return base64.b64decode(blob["content"]).decode(errors="replace")


def claimed(box):
    """When a `[WIP]` box was claimed, `None` when it carries no readable date.
    Rule 3 stamps `@<SessionID>-<yyyy-MM-dd HH:mm>`, in practice with an offset
    or a `Z` and sometimes a range, so the first date on the line wins and a
    naive one is read as UTC."""
    stamp = CLAIM.search(box)
    if not stamp:
        return None
    text = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2",
                  stamp.group().replace(" ", "T").replace("Z", "+00:00"))
    try:
        when = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(
        tzinfo=datetime.timezone.utc)


def cleared(repo, head, cache):
    """Whether this branch carried a `TODO.md` and deleted it, which is what
    clears the merge gate. Both cases read as missing at the head, and the
    diff cannot tell them apart either: adding a file and deleting it again
    nets out to nothing. The branch's own commits touching the path do, once
    the ones it inherits from `main` are taken out. Asked only of a branch
    already known to have no `TODO.md`."""
    if "cleared" not in cache:
        cache["cleared"] = {commit["sha"] for commit in get(
            repo, "commits?sha=main&path=TODO.md")}
    return any(commit["sha"] not in cache["cleared"] for commit in get(
        repo, f"commits?sha={head}&path=TODO.md"))


def elapsed(age):
    """An age in whole hours, in days once there are two of them: the window
    is twelve hours and the claims that break it run to weeks."""
    hours = int(age.total_seconds() // 3600)
    return f"{hours // 24} days" if hours >= 48 else f"{hours} hours"


def owned(repo, number, body, setup):
    """Whether the pipeline is answerable for this pull request: AGENT opened
    it or ADOPTED_PRS lists it, the same test the board and the scans use.
    Nobody else's branch owes us a `TODO.md`, and neither does one in
    DESIRE_REPO or MEMORY_REPO — the rule binds where the work happens."""
    return "pull_request" in body and repo in setup["WORK_REPOS"] and (
        body["user"]["login"] == setup["AGENT"]
        or number in setup.get("ADOPTED_PRS", {}).get(repo, []))


def todo(repo, number, body, setup, cache):
    """The `TODO.md` findings on one AGENT-owned pull request. Its boxes are
    the mutex between parallel agents and deleting the file is what clears the
    merge gate, so it is the one file that says whether a pull request is
    finished and nothing else in the sweep reads it. Open boxes are printed
    the way MEMORY_REPO's PR count is — work left is the normal state of a
    branch, not a finding — while a claim past Rule 3's twelve hours and a
    branch that never carried the file are reported."""
    if not owned(repo, number, body, setup):
        return []
    head = (heads(repo, cache).get(number)
            or get(repo, f"pulls/{number}"))["head"]["sha"]
    text = contents(repo, "TODO.md", head)
    if text is None:
        return [] if cleared(repo, head, cache) else [
            f"#{number} never carried a TODO.md, so it cannot reach sign-off: "
            + body["html_url"]]
    boxes = [(mark.group(1).strip(), line) for line in text.splitlines()
             for mark in [BOX.match(line)] if mark]
    if opened := [line for mark, line in boxes if not mark]:
        print(f"{repo}#{number}: {len(opened)} of {len(boxes)} TODO.md"
              " point(s) open", file=sys.stderr)
    findings = []
    for mark, line in boxes:
        if "WIP" not in mark.upper():
            continue
        when = claimed(line)
        age = None if when is None else (
            datetime.datetime.now(datetime.timezone.utc) - when)
        if age is not None and age < STALE:
            continue
        findings.append(
            f"#{number} stale [WIP] claim, "
            + ("no readable date" if age is None else
               f"{when:%Y-%m-%d} ({elapsed(age)} old)")
            + ", reclaim it: " + body["html_url"])
    return findings


def item(repo, number, setup, since, cache):
    """The findings on one PR or issue: USER's APPROVE_EMOJI on the body or on
    any comment, and every thread where USER spoke last. GitHub splits comments
    across two endpoints, review comments threaded by in_reply_to_id and the
    conversation tab flat; both are swept, and so are the bodies. A body USER
    wrote is the thread when nothing else was said on it, which is the shape a
    standing order arrives in; once anyone comments, that thread's last word
    answers for it and the body would only report it twice. `asking` decides
    which of the two are still waiting on us."""
    findings, threads, body = [], {}, get(repo, f"issues/{number}")
    kind = f"issues/{number}/reactions"
    if approved(repo, kind, body, setup, cache):
        findings.append(
            f"#{number} {setup['APPROVE_EMOJI']} from {setup['USER']} on the"
            f" body: {body['html_url']}" + seen(repo, kind, body, setup, cache))
    comments = [(comment, comment.get("in_reply_to_id", comment["id"]), "pulls")
                for comment in review_comments(repo, number, body)]
    comments += [(comment, number, "issues")
                 for comment in get(repo, f"issues/{number}/comments")]
    for comment, thread, endpoint in comments:
        threads.setdefault((endpoint, thread), []).append(comment)
        kind = f"{endpoint}/comments/{comment['id']}/reactions"
        if approved(repo, kind, comment, setup, cache):
            findings.append(
                f"#{number} {setup['APPROVE_EMOJI']} from {setup['USER']}:"
                f" {comment['html_url']}"
                + seen(repo, kind, comment, setup, cache))
    for (endpoint, _), thread in threads.items():
        asked = thread[-1]  # both endpoints list oldest first
        kind = f"{endpoint}/comments/{asked['id']}/reactions"
        flag = asking(repo, kind, asked, setup, since, cache)
        if flag is not None:
            findings.append(
                f"#{number} unanswered {setup['USER']} comment:"
                f" {asked['html_url']}" + flag)
    kind = f"issues/{number}/reactions"
    flag = None if threads else asking(repo, kind, body, setup, since, cache)
    if flag is not None:
        findings.append(
            f"#{number} unanswered {setup['USER']}"
            f" {'pull request' if 'pull_request' in body else 'issue'}:"
            f" {body['html_url']}" + flag)
    return findings + todo(repo, number, body, setup, cache)


def notes(have, want):
    """The two ways `WORK/` and the live open items disagree: an item nobody
    wrote a note for, and a note whose item is merged or closed. Pure, because
    it is the whole rule — the board's queue drifted for a week precisely
    because no test could be written against a paragraph of prose."""
    return sorted(want - have), sorted(have - want)


def stale(read, updated):
    """The notes whose item moved after the note was last read, by whole days:
    a note read on the morning its head is pushed to is current, one carrying
    last week's date over a head that moved yesterday is not. `read` maps a
    number to the date its note states, `updated` to the item's `updated_at`.
    A note with no readable date is stale by construction — it cannot say when
    it was true."""
    return sorted(number for number, day in read.items()
                  if number in updated
                  and (day is None or day < updated[number][:10]))


READ = re.compile(r"\bread (\d{4}-\d{2}-\d{2})")


def cited(texts):
    """Every `#<number>` an existing note mentions. Forming a view on one item
    pulls in what it references, which is how an issue earns a note without a
    human deciding it has: a note that says a head waits on a ruling names the
    issue, and that issue is then in play."""
    return {int(number) for text in texts
            for number in re.findall(r"#(\d+)", text)}


def memory_clone():
    """Where MEMORY_REPO is checked out: the directory holding the `config.env`
    we are configured by, since that file lives at its root — normally the
    clone this script is in. `None` when it carries no `WORK/`, so a sweep run
    against a memory repo that has no notes yet still sweeps, cannot check
    them, and says so rather than reporting every item as missing one."""
    root = find_config().parent
    return root if (root / "WORK").is_dir() else None


def uncharted(repo, setup, cache):
    """What `WORK/<repo>/` and the repo's open items say about each other.

    The notes cover the whole repository, not our own slice of it: someone
    else's pull request collides with ours, and an issue nobody answered is
    the reason a head is stuck. Ownership is a field inside the note, not a
    condition on it existing.

    A note is **required** for every open pull request, and for every open
    issue an existing note cites — forming a view on one item is what pulls in
    what it references. Every other open issue is printed as context and does
    not make the sweep dirty: a note that only restated GitHub would be the
    board's queue again, one file per row instead of one table.

    Three findings: an item with no note, a note whose item is closed, and a
    note older than the item it describes."""
    if repo not in setup["WORK_REPOS"]:
        return []  # the rule binds where the work happens
    root = memory_clone()
    if root is None:
        print(f"{repo}: MEMORY_REPO carries no WORK/, notes unchecked",
              file=sys.stderr)
        return []
    name = repo.split("/")[-1]
    directory = root / "WORK" / name
    files = {int(note.stem): note for note in directory.glob("*.md")
             if note.stem.isdigit()} if directory.is_dir() else {}
    texts = {number: note.read_text() for number, note in files.items()}
    read = {number: (READ.search(text).group(1) if READ.search(text) else None)
            for number, text in texts.items()}
    items = get(repo, "issues?state=open")
    updated = {item["number"]: item["updated_at"] for item in items}
    pulls = {item["number"] for item in items if "pull_request" in item}
    want = pulls | (cited(texts.values()) & set(updated))
    unread = sorted(set(updated) - want - set(files))
    if unread:
        print(f"{repo}: {len(unread)} open issue(s) nobody has a note on, none"
              " of them cited by one: "
              + ", ".join(f"#{number}" for number in unread), file=sys.stderr)
    missing, _ = notes(set(files), want)
    _, orphan = notes(set(files), set(updated))  # open at all, not required
    link = f"https://github.com/{repo}/issues/"
    return [f"{repo}#{number} has no WORK/{name}/{number}.md, so nothing says"
            f" where it stands: {link}{number}" for number in missing
            ] + [f"{repo}: WORK/{name}/{number}.md outlived its item, which is"
                 f" closed — delete it: {link}{number}" for number in orphan
            ] + [f"{repo}: WORK/{name}/{number}.md was read {read[number]} and"
                 f" {number} moved since, so it may be stale: {link}{number}"
                 for number in stale(read, updated)]


def sweep(repo, numbers, since, setup):
    """One line per finding, empty when the sweep is clean."""
    cache, findings = {}, []
    if repo == setup["MEMORY_REPO"] and not numbers:
        findings += memory(repo)
    if not numbers:
        findings += uncharted(repo, setup, cache)
        findings += closed_since(repo, since)
        numbers = sorted({
            issue["number"] for issue in get(repo, "issues?state=open")})
    for number in numbers:
        findings += item(repo, number, setup, since, cache)
    return findings


def main(arguments):
    since = ""  # ISO 8601 UTC sorts lexicographically, so "" is the epoch
    if arguments and arguments[0] == "--since":
        _, since, *arguments = arguments
    try:
        findings = sweep(arguments[0], [int(n) for n in arguments[1:]], since,
                         config(find_config()))
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"{arguments[0]}: GitHub unreadable, the sweep is incomplete and"
              f" says nothing about this repo: {error}", file=sys.stderr)
        return 2
    print("\n".join(findings) if findings else "clean", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
