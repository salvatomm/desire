#!/usr/bin/env python3
"""A verdict on pull requests from live GitHub data, read-only.

Usage: pr_status.py [--gate] [--json] [--config FILE] [--cited FILE --repo
                    owner/repo] [--threads FILE] <owner/repo#N>...
Exit 0 ready, GO, merged or closed (with --gate: GO only), 1 findings,
2 a read failed or a verdict is incomplete.
"""
import argparse
import base64
import concurrent.futures
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
TARGET = re.compile(r"^([\w.-]+/[\w.-]+)#(\d+)$")
CITE = re.compile(r"([\w./-]*)#(\d+)")
LIST = re.compile(r"[\s,/]*(and|or|→|->)?[\s,/]*")
BOX = re.compile(r"\[( |x|X|WIP)\]")
FOOTER_LINK = re.compile(r"\[[^\]]*\]\((https://[^\s)]+)\)")
PASSED = {"success", "neutral", "skipped"}
SAYS_OPEN = re.compile(r"(?<![\w-])(open|ready|waits|waiting|draft)\b", re.I)
SAYS_CLOSED = re.compile(r"(?<![\w-])(closed|merged|landed)\b", re.I)


class Unread(Exception):
    """A GitHub read that failed."""


def config(path):
    """config.env as a dict, the comma lists split."""
    setup = {}
    for line in pathlib.Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"config.env: no key in {line!r}")
        setup[key.strip()] = value.strip()
    for key in ("WORK_REPOS", "AGENT_FOOTERS"):
        setup[key] = [v.strip() for v in setup.get(key, "").split(",")
                      if v.strip()]
    return setup


def request(url, data=None):
    """The JSON at `url`, or Unread; a 404 is returned as None."""
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "pr-status", "Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404 and data is None:
            return None
        raise Unread(f"HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise Unread(type(error).__name__) from None


def get(repo, path, key=None):
    """A REST resource of `repo`, every page when it is a listing."""
    results, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        body = request(f"{API}/repos/{repo}/{path}{sep}per_page=100&page={page}")
        items = body.get(key, []) if key and body else body
        if not isinstance(items, list):
            return items
        results += items
        if len(items) < 100:
            return results
        page += 1


THREADS = """query($o:String!,$r:String!,$n:Int!,$c:String){repository(owner:$o,
name:$r){pullRequest(number:$n){reviewThreads(first:100,after:$c){pageInfo{
hasNextPage endCursor}nodes{isResolved comments(last:1){nodes{author{login}
body url}}}}}}}"""


def agent_footer(body, setup):
    """Whether `body`'s last line is, or links to, one of AGENT_FOOTERS."""
    line = ((body or "").strip().splitlines() or [""])[-1].strip().strip("_*")
    targets = FOOTER_LINK.findall(line)
    return any(line == marker or any(marker in t for t in targets)
               for marker in setup.get("AGENT_FOOTERS", []) if marker)


def last_comment(thread):
    """(resolved, login, body, url) of a GraphQL or MCP review thread."""
    if "is_resolved" in thread:
        last = (thread["comments"] or [{}])[-1]
        return (thread["is_resolved"], last.get("author", ""),
                last.get("body", ""), last.get("html_url", ""))
    last = (thread["comments"]["nodes"] or [{}])[-1]
    return (thread["isResolved"], (last.get("author") or {}).get("login", ""),
            last.get("body", ""), last.get("url", ""))


def split_threads(threads, setup):
    """Unresolved threads as (waiting on an agent, waiting on USER) urls: on
    USER when the agent spoke last, AGENT or USER with a footer."""
    on_agent, on_user = [], []
    for thread in threads:
        resolved, login, body, url = last_comment(thread)
        if resolved:
            continue
        agent = login == setup["AGENT"] or (
            login == setup["USER"] and agent_footer(body, setup))
        (on_user if agent else on_agent).append(url)
    return on_agent, on_user


def checks(runs, expected, now):
    """(passed, failed, pending) names of the newest run of each name, every
    expected name never created counted as pending, a running one with its
    minutes."""
    newest, passed, failed, pending = {}, [], [], []
    for run in sorted(runs, key=lambda run: run["id"]):
        newest[run["name"]] = run
    for name, run in sorted(newest.items()):
        start = datetime.datetime.fromisoformat(
            (run.get("started_at") or now.isoformat()).replace("Z", "+00:00"))
        if run["status"] != "completed":
            pending.append(f"{name} {int((now - start).total_seconds() // 60)}m")
        else:
            (passed if run["conclusion"] in PASSED else failed).append(name)
    pending += [f"{name} never created" for name in sorted(expected)
                if name not in newest]
    return passed, failed, pending


def todo_counts(text):
    """Counts of TODO.md's [ ], [WIP] and [x] boxes."""
    found = BOX.findall(text)
    return {"open": found.count(" "), "wip": found.count("WIP"),
            "done": found.count("x") + found.count("X")}


def approval(reviews, user):
    """The commit USER's latest deciding review approved, None if it did not."""
    mine = [r for r in reviews if (r.get("user") or {}).get("login") == user
            and r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")]
    if not mine or mine[-1]["state"] != "APPROVED":
        return None
    return mine[-1]["commit_id"]


def verdict(s):
    """(verdict, reasons) from a measured status; 'n/a' fields are unknown."""
    if s["state"] in ("merged", "closed"):
        return s["state"], []
    agent = []
    if s["draft"]:
        agent.append("draft")
    if s["mergeable"] == "dirty":
        agent.append("conflict" + (", no checks ran" if s["ran"] is False
                                   else ""))
    if s["mergeable"] == "behind":
        agent.append("behind base")
    if s["checks"] != "n/a":
        _, failed, pending = s["checks"]
        agent += [f"failed {', '.join(failed)}"] if failed else []
        agent += [f"pending {', '.join(pending)}"] if pending else []
    if s["todo"] not in (None, "n/a"):
        agent.append("TODO.md present")
    if s["threads"] != "n/a" and s["threads"][0]:
        agent.append(f"{len(s['threads'][0])} thread(s) on agent")
    if agent:
        return "waiting-on-agent", agent
    unknown = [k for k in ("mergeable", "checks", "expected", "todo",
                           "threads", "approval", "compare") if s[k] == "n/a"]
    if unknown or s["mergeable"] == "unknown":
        return "incomplete", [f"n/a {', '.join(unknown) or 'mergeable'}"]
    if s["threads"][1]:
        return "waiting-on-USER", [f"{len(s['threads'][1])} thread(s) on USER"]
    if s["approval"] != s["sha"]:
        return "ready", [f"approval on {s['approval'][:7]}, not the head"
                         if s["approval"] else "no approval from USER"]
    if s["mergeable"] not in ("clean", "has_hooks"):
        return "ready", [f"approved head but {s['mergeable']}"]
    return "GO", []


def attempt(read, *args):
    """`read(*args)`, or 'n/a' when it fails."""
    try:
        return read(*args)
    except Unread:
        return "n/a"


def mergeable(repo, number, wait):
    """The pull request, re-read while mergeable_state is unknown."""
    for tries in range(5):
        if tries:
            wait(2)
        pull = get(repo, f"pulls/{number}")
        if pull is None:
            raise Unread("HTTP 404")
        if pull["state"] != "open" or pull.get("mergeable_state") != "unknown":
            break
    return pull


def expected(repo, base):
    """Required check names from branch protection and rulesets on `base`,
    none when it is unprotected."""
    branch = get(repo, f"branches/{base}")
    if branch is None:
        raise Unread("HTTP 404")
    if not branch.get("protected"):
        return []
    required = (branch.get("protection") or {}).get(
        "required_status_checks") or {}
    names = set(required.get("contexts") or [])
    for rule in get(repo, f"rules/branches/{base}") or []:
        if rule.get("type") == "required_status_checks":
            names |= {c["context"] for c in
                      rule["parameters"]["required_status_checks"]}
    return sorted(names)


def threads(repo, number):
    """Every review thread of the pull request, via GraphQL."""
    owner, name = repo.split("/")
    nodes, cursor = [], None
    while True:
        body = request(f"{API}/graphql", json.dumps({"query": THREADS, "variables": {
            "o": owner, "r": name, "n": number, "c": cursor}}).encode())
        if not body or body.get("errors") or not body.get("data"):
            raise Unread("GraphQL")
        page = body["data"]["repository"]["pullRequest"]["reviewThreads"]
        nodes += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return nodes
        cursor = page["pageInfo"]["endCursor"]


def measure(repo, number, setup, now, given=None, wait=time.sleep):
    """Every field of one pull request's status, 'n/a' where unread;
    `given` holds review threads read elsewhere."""
    pull = mergeable(repo, number, wait)
    sha, base = pull["head"]["sha"], pull["base"]["ref"]
    state = "merged" if pull.get("merged") else pull["state"]
    s = {"pr": f"{repo}#{number}", "sha": sha, "at": now.strftime(
        "%Y-%m-%dT%H:%MZ"), "state": state, "draft": pull["draft"],
         "mergeable": pull.get("mergeable_state") or "n/a"}
    if state != "open":
        s["by"] = (pull.get("merged_by") or {}).get("login")
        s["verdict"], s["reasons"] = state, []
        return s
    runs = attempt(get, repo, f"commits/{sha}/check-runs", "check_runs")
    s["expected"] = attempt(expected, repo, base)
    s["ran"] = None if runs in ("n/a", None) else bool(runs)
    s["checks"] = "n/a" if runs in ("n/a", None) else checks(
        runs, s["expected"] if s["expected"] != "n/a" else [], now)
    diff = attempt(get, repo, f"compare/{base}...{sha}")
    s["compare"] = "n/a" if diff in ("n/a", None) else (
        diff["behind_by"], diff["ahead_by"])
    body = attempt(get, repo, f"contents/TODO.md?ref={sha}")
    s["todo"] = body if body in ("n/a", None) else todo_counts(
        base64.b64decode(body["content"]).decode(errors="replace"))
    raw = given if given is not None else attempt(threads, repo, number)
    s["threads"] = raw if raw == "n/a" else split_threads(raw, setup)
    reviews = attempt(get, repo, f"pulls/{number}/reviews")
    s["approval"] = "n/a" if reviews in ("n/a", None) else approval(
        reviews, setup["USER"])
    s["verdict"], s["reasons"] = verdict(s)
    return s


def field(value, text):
    """`text(value)`, or 'n/a' for an unread value."""
    return "n/a" if value == "n/a" else text(value)


def line(s, full=False):
    """One text line for a measured status."""
    head = f"{s['pr']} @{s['sha'] if full else s['sha'][:7]} {s['at']} "
    if s["state"] != "open":
        return head + s["state"] + (f" by {s['by']}" if s.get("by") else "")
    parts = [
        field(s["compare"], lambda c: f"{c[0]} behind/{c[1]} ahead"),
        "checks " + field(s["checks"], lambda c: "{} passed, {} failed, {} "
                          "pending".format(*map(len, c))),
        "threads " + field(s["threads"], lambda t: f"{len(t[0])} on agent, "
                           f"{len(t[1])} on USER"),
        "TODO.md " + field(s["todo"], lambda t: "absent" if t is None else
                           "[ ]{open} [WIP]{wip} [x]{done}".format(**t)),
        "approval " + field(s["approval"], lambda a: "none" if not a else
                            "on head" if a == s["sha"] else f"on {a[:7]}")]
    why = f" ({'; '.join(s['reasons'])})" if s["reasons"] else ""
    return (head + f"{s['state']}{' draft' if s['draft'] else ''} {s['mergeable']}, "
            + "; ".join(parts) + f" -> {s['verdict']}{why}")


def refs(text, default, setup):
    """(line number, words, repo, number) for each item cited in `text`,
    `words` the 60 characters after it, up to the next citation. A bare
    number listed right after a named one, `a/b#1, #2`, is that repo's, any
    other is `default`'s."""
    names = {r.split("/")[-1]: r for r in setup["WORK_REPOS"] + [
        setup.get("MEMORY_REPO", ""), setup.get("DESIRE_REPO", "")] if r}
    for at, row in enumerate(text.splitlines(), 1):
        found, named, end = list(CITE.finditer(row)), default, 0
        for match, after in zip(found, found[1:] + [None]):
            prefix = match[1].strip("/.")
            named = named if LIST.fullmatch(row[end:match.start()]) else default
            end = match.end()
            repo = (prefix if "/" in prefix else names.get(prefix)
                    if prefix else named)
            named = repo if prefix else named
            words = row[match.end():after.start() if after else None][:60]
            if repo:
                yield at, words, repo, int(match[2])


def contradicts(row, state):
    """Whether a line's words call an item the opposite of `state`."""
    said = bool(SAYS_OPEN.search(row)), bool(SAYS_CLOSED.search(row))
    return said == ((False, True) if state == "open" else (True, False))


def item_state(repo, number):
    """'open', 'closed by X' or 'merged by X' for one item."""
    issue = get(repo, f"issues/{number}")
    if issue is None:
        raise Unread("HTTP 404")
    who = (issue.get("closed_by") or {}).get("login", "unknown")
    if issue["state"] == "open":
        return "open"
    merged = (issue.get("pull_request") or {}).get("merged_at")
    return f"{'merged' if merged else 'closed'} by {who}"


def cited(path, default, setup):
    """Print each cited item's live state by its line; True when all read."""
    found = list(refs(pathlib.Path(path).read_text(), default, setup))
    keys = sorted({(repo, number) for _, _, repo, number in found})
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        cache = dict(zip(keys, pool.map(
            lambda key: attempt(item_state, *key), keys)))
    advisory = []
    for at, words, repo, number in found:
        state = cache[repo, number]
        print(f"{path}:{at}: {repo}#{number} {state}")
        if state != "n/a" and contradicts(words, state.split()[0]):
            advisory.append(f"{path}:{at}: {repo}#{number} is {state}, the line"
                            f" says: {words.strip()}")
    if advisory:
        print("advisory, lines whose words may disagree:\n  "
              + "\n  ".join(advisory))
    return "n/a" not in cache.values()


def saved_threads(raw):
    """The review threads of saved MCP `get_review_comments` answers, one or
    a list of its pages; None when a page says more follow."""
    paged = isinstance(raw, list) and raw and "review_threads" in raw[0]
    pages = raw if paged else [raw]
    last = pages[-1] if isinstance(pages[-1], dict) else {}
    if (last.get("pageInfo") or {}).get("hasNextPage"):
        return None
    return [t for page in pages for t in (
        page.get("review_threads", []) if isinstance(page, dict) else page)]


def main(arguments):
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="*")
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--cited")
    parser.add_argument("--repo")
    parser.add_argument("--threads")
    parser.add_argument("--config", default=os.environ.get(
        "AGENTS_CONFIG") or "config.env")
    args = parser.parse_args(arguments)
    matches = [TARGET.match(t) for t in args.targets]
    if not all(matches) or not (matches or args.cited) or (
            args.threads and len(matches) != 1) or (
            args.cited and not args.repo):
        parser.error("targets are owner/repo#N, one with --threads; "
                     "--cited needs --repo")
    try:
        setup, given = config(args.config), None
        missing = {"USER", "AGENT"} - set(setup)
        if missing:
            raise KeyError(f"config.env sets no {', '.join(sorted(missing))}")
        if args.threads:
            given = saved_threads(json.loads(
                pathlib.Path(args.threads).read_text()))
            if given is None:
                raise ValueError("--threads: save every page of the answer")
        complete = not args.cited or cited(args.cited, args.repo, setup)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    now = datetime.datetime.now(datetime.timezone.utc)
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        futures = [pool.submit(measure, m[1], int(m[2]), setup, now, given)
                   for m in matches]
    statuses = []
    for target, future in zip(args.targets, futures):
        try:
            statuses.append(future.result())
            s = statuses[-1]
            print(json.dumps(s) if args.json else line(s, args.gate))
        except Unread as error:
            print(f"{target} n/a ({error})")
            complete = False
    good = ("GO",) if args.gate else ("GO", "ready", "merged", "closed")
    if not complete or any(s["verdict"] == "incomplete" for s in statuses):
        return 2
    return 0 if all(s["verdict"] in good for s in statuses) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
