#!/usr/bin/env python3
"""Mechanical checks on a draft GitHub post, read-only; see SKILL.md.

Exit 0 clean, 1 findings, 2 a read failed.
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
KEYWORD = re.compile(r"(?<![\w-])(close[sd]?|fix(?:e[sd])?|resolve[sd]?)(?![\w-])",
                     re.I)
REF = re.compile(
    r"(?:https?://github\.com/(?P<url>[\w.-]+/[\w.-]+)/(?:issues|pull)/"
    r"|(?<![\w./-])(?P<full>[\w.-]+/[\w.-]+)#"
    r"|(?<![\w./-])(?P<short>[\w.-]+)#"
    r"|(?<![\w/&#])#)(?P<number>\d+)\b")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])?\s*")
FOOTER_LINK = re.compile(r"\[[^\]]*\]\((https://[^\s)]+)\)")
LIST = re.compile(r"[\s,;]*(?:(?:and|or|&|\+)\s+)?" + REF.pattern)
TARGET = re.compile(r"^([\w.-]+/[\w.-]+)#(\d+)$")
NOUN = re.compile(r"[:\s]*(?:issues?|prs?|pull requests?|bugs?)\s+", re.I)
FENCE = re.compile(r"\s*(`{3,}|~{3,})(.*)")
CLOSING = """query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){
pullRequest(number:$n){closingIssuesReferences(first:100){totalCount nodes{number
repository{nameWithOwner}}}}}}"""


class Unread(Exception):
    """A read that failed."""


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
    """The JSON at `url`, or Unread naming the failure."""
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "post-check", "Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise Unread(f"HTTP {error.code}") from None
    except (OSError, ValueError) as error:
        raise Unread(type(error).__name__) from None


def is_public(repo):
    """True, False, or the reason GitHub could not say."""
    try:
        return not request(f"{API}/repos/{repo}")["private"]
    except Unread as error:
        return str(error)
    except (KeyError, TypeError):
        return "no visibility field"


def prose(text):
    """`text` with fenced and inline code blanked, line numbers kept."""
    lines, fence = [], ""
    for line in text.splitlines():
        run = FENCE.match(line)
        if run and not fence:
            fence = run[1]
        elif run and run[1][0] == fence[0] and len(run[1]) >= len(fence) \
                and not run[2].strip():
            fence = ""
        if run or fence:
            lines.append("")
            continue
        lines.append(re.sub(
            r"`[^`]*`", lambda m: " " * len(m[0]), line))
    return lines


def ref_key(match, default):
    """`owner/repo#N` for a REF match, `name#N` for a short one."""
    repo = match["url"] or match["full"]
    if repo:
        return f"{repo}#{match['number']}"
    if match["short"]:
        return f"{match['short']}#{match['number']}"
    return f"{default}#{match['number']}"


def closes(lines, default):
    """(findings, keys): bad closing references, and the ones that link."""
    findings, keys = [], []
    for at, line in enumerate(lines, 1):
        for word in KEYWORD.finditer(line):
            rest = line[word.end():]
            ref = REF.match(rest, re.match(r"[:\s]*", rest).end())
            if not ref and (noun := NOUN.match(rest)) and REF.match(
                    rest, noun.end()):
                findings.append(f"closes: line {at}: '{word[0]}' is followed by "
                                f"'{noun[0].strip(': ')}', not a reference; "
                                "GitHub links none")
                continue
            if not ref:
                if REF.search(rest) or rest.strip()[-1:] not in ("", ":"):
                    continue
                after = next((x for x in lines[at:] if x.strip()), "")
                if REF.match(BULLET.sub("", after, 1)):
                    findings.append(f"closes: line {at}: '{word[0]}' has its "
                                    "reference on the next line; GitHub links none")
                continue
            if ref["short"]:
                findings.append(f"closes: line {at}: '{word[0]} {ref[0]}' needs "
                                "owner/repo#N; GitHub links none")
                continue
            keys.append(ref_key(ref, default))
            tail, extra = rest[ref.end():], 0
            while more := LIST.match(tail):
                extra, tail = extra + 1, tail[more.end():]
            if extra:
                findings.append(f"closes: line {at}: '{word[0]}' is followed by "
                                f"{extra + 1} references; GitHub links the first"
                                " only: one keyword per reference")
    return findings, keys


def mentions(lines, default, words=6):
    """(line, key, context) for the first mention of each reference."""
    seen = set()
    for at, line in enumerate(lines, 1):
        for match in REF.finditer(line):
            key = ref_key(match, default).lower()
            if key in seen:
                continue
            seen.add(key)
            before, after = line[:match.start()], line[match.end():]
            pre = " ".join(before.split()[-words:])
            post = " ".join(after.split()[:words])
            gap = " " * (bool(pre) and before[-1:].isspace())
            tie = " " * (bool(post) and after[:1].isspace())
            yield at, match[0], f"{pre}{gap}{match[0]}{tie}{post}"


def footer_count(line, setup):
    """How many AGENT_FOOTERS markers `line` carries, as sweep reads them, a
    bare HTTPS URL line read as a link target."""
    line = line.strip().strip("_*")
    targets = FOOTER_LINK.findall(line) or re.findall(r"^https://\S+$", line)
    return sum((line == marker) + sum(marker in t for t in targets)
               for marker in setup["AGENT_FOOTERS"] if marker)


def footer(text, setup):
    """Findings on the attribution footer of `text`."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ["footer: the body is empty"]
    count = footer_count(lines[-1], setup)
    found = [] if count == 1 else [
        f"footer: last line carries {count} AGENT_FOOTERS markers, not 1"]
    found += [f"footer: a footer also stands earlier: {line.strip()!r}"
              for line in lines[:-1] if footer_count(line, setup) and (
                  line.strip().strip("_*") in setup["AGENT_FOOTERS"]
                  or len(FOOTER_LINK.sub("", line).split()) <= 3)]
    return found


def named(repo, line):
    """Whether `line` names `repo` as owner/repo or as name#N."""
    name = repo.split("/")[-1]
    return bool(re.search(rf"(?<![\w.-]){re.escape(repo)}(?![\w-])"
                          rf"|(?<![\w./-]){re.escape(name)}#\d+", line, re.I))


def mentioned(texts, setup, target, known=()):
    """{repo: public?} for each WORK_REPOS or MEMORY_REPO repo the texts name."""
    repos = {*setup["WORK_REPOS"], setup.get("MEMORY_REPO", "")} - {
        "", target, *known}
    return {repo: is_public(repo) for repo in sorted(repos)
            if any(named(repo, line) for text in texts for line in text)}


def leaks(lines, where, visibility, patterns):
    """Findings for private-repo mentions and denylist hits in `lines`."""
    found = []
    for at, line in enumerate(lines, 1):
        for repo, public in visibility.items():
            if public is not True and named(repo, line):
                why = "private" if public is False else f"unreadable ({public}),"\
                    " so private"
                found.append(f"private: {where} line {at}: names {repo} ({why})")
        found += [f"deny: {where} line {at}: matches /{p.pattern}/"
                  for p in patterns if p.search(line)]
    return found


def denylist(path):
    """The compiled regexes of a denylist file, one per line."""
    lines = pathlib.Path(path).read_text().splitlines()
    return [re.compile(x.strip()) for x in lines
            if x.strip() and not x.lstrip().startswith("#")]


def commits(repo_dir, span):
    """(sha, author, email, signature, message) of each commit in `span`."""
    out = subprocess.run(
        ["git", "-C", repo_dir, "log", "--format=%H%x00%an%x00%ae%x00%G?%x00%B%x1e",
         span], capture_output=True, text=True, check=False)
    if out.returncode:
        raise Unread((out.stderr.strip().splitlines() or ["git"])[0])
    return [tuple(entry.strip("\n").split("\0", 4))
            for entry in out.stdout.split("\x1e") if entry.strip()]


def identity(entries, setup, signed):
    """(findings, notes) on the author and signature of each commit."""
    found, unsigned = [], []
    want = f"{setup.get('AGENT')} <{setup.get('AGENT_EMAIL')}>"
    for sha, name, email, signature, _ in entries:
        if f"{name} <{email}>" != want:
            found.append(f"commit {sha[:7]}: author {name} <{email}>, not {want}")
        if signature in ("B", "R"):
            found.append(f"commit {sha[:7]}: signature status {signature}")
        unsigned += [sha[:7]] if signature == "N" else []
    line = [f"unsigned: {len(unsigned)} commits: {' '.join(unsigned)}"] * bool(
        unsigned)
    return (found + line, []) if signed else (found, line)


def closing_refs(target):
    """The issues GitHub links to close from pull request `owner/repo#N`."""
    match = TARGET.match(target)
    owner, name = match[1].split("/")
    body = request(f"{API}/graphql", json.dumps({"query": CLOSING, "variables": {
        "o": owner, "r": name, "n": int(match[2])}}).encode())
    if body.get("errors") or not (body.get("data") or {}).get("repository"):
        raise Unread("GraphQL")
    refs = body["data"]["repository"]["pullRequest"]["closingIssuesReferences"]
    nodes = refs["nodes"]
    if refs["totalCount"] > len(nodes):
        raise Unread(f"{refs['totalCount']} closing references, read {len(nodes)}")
    return {f"{n['repository']['nameWithOwner']}#{n['number']}".lower()
            for n in nodes}


def compare(linked, named):
    """Findings where GitHub's closing references differ from the body's."""
    named = {key.lower() for key in named}
    return ([f"verify: GitHub links {k}, the body names no keyword for it"
             for k in sorted(linked - named)]
            + [f"verify: the body closes {k}, GitHub does not link it"
               for k in sorted(named - linked)])


def public_scan(args, setup, lines, entries):
    """(findings, complete) for private repos and denylist hits, code included."""
    try:
        patterns = denylist(args.denylist) if args.denylist else []
    except (OSError, UnicodeError, re.error) as error:
        print(f"denylist: n/a ({error})")
        return [], False
    texts = [lines] + [entry[4].splitlines() for entry in entries]
    visibility = mentioned(texts, setup, args.target, args.public)
    found = leaks(lines, "body", visibility, patterns)
    for sha, *_, message in entries:
        found += leaks(message.splitlines(), f"commit {sha[:7]}", visibility,
                       patterns)
    return found, True


def verify(args, keys):
    """(findings, complete) comparing GitHub's closing references."""
    try:
        return compare(closing_refs(args.verify_closes), keys), True
    except (Unread, KeyError, TypeError) as error:
        print(f"verify: n/a ({error})")
        return [], False


def check(args, setup, text):
    """(findings, notes, complete) for the parsed arguments and draft."""
    lines = prose(text)
    pr_repo = TARGET.match(args.verify_closes)[1] if args.verify_closes else None
    findings, keys = closes(lines, pr_repo or args.target)
    notes = [f"first mention: line {at}: {ref}: {context}"
             for at, ref, context in mentions(lines, args.target)]
    complete = bool(setup["AGENT_FOOTERS"])
    findings += footer(text, setup) if complete else []
    if not complete:
        print("footer: n/a (AGENT_FOOTERS is empty)")
    public = True if args.target in args.public else is_public(args.target)
    shown = {True: "public", False: "private"}.get(public)
    print(f"target: {args.target} "
          f"{shown or f'unreadable ({public}), treated as public'}")
    entries = []
    if args.range:
        try:
            if not (setup.get("AGENT") and setup.get("AGENT_EMAIL")):
                raise Unread("AGENT or AGENT_EMAIL is not in config.env")
            entries = commits(args.repo_dir, args.range)
        except Unread as error:
            print(f"commits: n/a ({error})")
            complete = False
        found, more = identity(entries, setup, args.signed)
        findings, notes = findings + found, notes + more
    raw = text.splitlines()
    steps = [public_scan(args, setup, raw, entries)] if public is not False else []
    steps += [verify(args, keys)] if args.verify_closes else []
    for found, done in steps:
        findings, complete = findings + found, complete and done
    return findings, notes, complete


def main(arguments):
    parser = argparse.ArgumentParser()
    parser.add_argument("body")
    parser.add_argument("--target", required=True)
    parser.add_argument("--config", default=os.environ.get(
        "AGENTS_CONFIG") or "config.env")
    parser.add_argument("--range")
    parser.add_argument("--repo-dir", default=".")
    parser.add_argument("--signed", action="store_true")
    parser.add_argument("--denylist")
    parser.add_argument("--verify-closes")
    parser.add_argument("--public", action="append", default=[])
    args = parser.parse_args(arguments)
    if args.verify_closes and not TARGET.match(args.verify_closes):
        parser.error("--verify-closes takes owner/repo#N")
    try:
        setup = config(args.config)
        text = sys.stdin.read() if args.body == "-" else pathlib.Path(
            args.body).read_text()
    except (OSError, ValueError) as error:
        print(f"n/a ({error})\nincomplete")
        return 2
    findings, notes, complete = check(args, setup, text)
    for line in findings:
        print(line)
    if notes:
        print("advisory:\n  " + "\n  ".join(notes))
    if not complete:
        print("incomplete")
        return 2
    print("clean" if not findings else f"{len(findings)} findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
