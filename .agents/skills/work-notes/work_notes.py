#!/usr/bin/env python3
"""Check MEMORY_REPO's `WORK/` notes: that every item AGENT touched since a
time has a note with a log line from then, and that every note keeps the
shape of DESIRE_REPO's `template/memory/WORK/TEMPLATE.md`.

Usage: work_notes.py touched --since <ISO8601 UTC> [--config <config.env>]
       work_notes.py lint [--config <config.env>] [--template <TEMPLATE.md>]
Run from the MEMORY_REPO clone, on the day PR's branch. Exit 0 clean, 1 with
findings, 2 when GitHub could not be read.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TEMPLATE = (pathlib.Path(__file__).resolve().parents[3]
            / "template" / "memory" / "WORK" / "TEMPLATE.md")
LOG_LINES = 5
TIMEOUT = 30
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
SINCE = re.compile(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?)?")
ITEM = re.compile(r"^- \*\*(.+?)\*\*")
TITLE = re.compile(r"^# ([\w.-]+)#(\d+) — \S")
READ = re.compile(r"\bread \d{4}-\d{2}-\d{2}\b")
DAY_TITLE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MERGEABLE = r"`(?:clean|dirty|unstable|behind|blocked|mergeable|conflicting)`"
LIVE = [
    ("CI result", re.compile(
        r"\b(?:CI|checks) (?:is |are |was |now |still )?(?:\d+/\d+ )?(?:all )?"
        r"(?:green|red)\b", re.IGNORECASE)),
    ("check count", re.compile(r"\b\d+/\d+ (?:checks|green|passing)\b"
                               r"|\bchecks? \d+/\d+", re.IGNORECASE)),
    ("mergeable state", re.compile(MERGEABLE + r"|\bmergeable_state\b")),
    ("line count", re.compile(r"\+\d[\d,]*\s*/\s*[−-]\d[\d,]*")),
]
LIVE_LOG = re.compile(r"^- \*\*[^*]+\*\*\s*(?:still |again |now )?" + MERGEABLE)


def config(path):
    """config.env as a dict; WORK_REPOS and AGENT_FOOTERS split on commas."""
    setup = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"config.env: no key in {line!r}")
        setup[key.strip()] = value.strip()
    for key in ("WORK_REPOS", "AGENT_FOOTERS"):
        if key in setup:
            setup[key] = [v.strip() for v in setup[key].split(",") if v.strip()]
    return setup


def config_path(given):
    """--config, else AGENTS_CONFIG, else ./config.env."""
    return pathlib.Path(given or os.environ.get("AGENTS_CONFIG") or "config.env")


def rate_wait(code, headers, body, now):
    """Seconds to wait before retrying a rate-limited answer, None if it is not one."""
    if code not in (403, 429):
        return None
    if headers.get("Retry-After", "").isdigit():
        return min(int(headers["Retry-After"]) + 1, 90)
    reset = headers.get("X-RateLimit-Reset", "")
    if headers.get("X-RateLimit-Remaining") == "0" and reset.isdigit():
        return min(max(int(reset) - now, 1), 90)
    return 60 if "rate limit" in body.lower() else None


def request(url, attempts=3):
    """One GitHub GET as JSON, waiting out a rate limit up to `attempts` times."""
    headers = {"User-Agent": "work-notes", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                        timeout=TIMEOUT) as r:
                return json.load(r)
        except urllib.error.HTTPError as error:
            wait = rate_wait(error.code, error.headers,
                             error.read().decode(errors="replace"), time.time())
            if wait is None or attempt == attempts - 1:
                raise
            time.sleep(wait)
    raise RuntimeError("unreachable")


def search(agent, repo, since):
    """Every issue and pull request of `repo` involving `agent` updated since."""
    found = []
    for kind in ("is:issue", "is:pr"):
        query = urllib.parse.quote(
            f"involves:{agent} updated:>={since} repo:{repo} {kind}")
        page = 1
        while True:
            body = request(f"https://api.github.com/search/issues?q={query}"
                           f"&per_page=100&page={page}")
            if body.get("incomplete_results") or body.get("total_count", 0) > 1000:
                raise ValueError("search results incomplete")
            found += body["items"]
            if len(body["items"]) < 100:
                break
            page += 1
    return found


def note_path(root, repo, number):
    """WORK/<repository name>/<number>.md under `root`."""
    return root / "WORK" / repo.split("/")[-1] / f"{number}.md"


def day_pr(repo, item, setup):
    """Whether `item` is MEMORY_REPO's day PR, titled with its day."""
    return (repo == setup["MEMORY_REPO"] and "pull_request" in item
            and bool(DAY_TITLE.match(item["title"].strip())))


def is_day(text):
    """Whether `text` is a calendar date YYYY-MM-DD."""
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def parse(text):
    """A note as its title, its fields [(label, text)] and its log [(day, text)]."""
    lines = text.splitlines()
    title = lines[0] if lines else ""
    fields, log, current = [], [], None
    for line in lines[1:]:
        match = ITEM.match(line)
        if match:
            label = match.group(1)
            current = [label, line]
            dated = DAY.match(label)
            (log if dated else fields).append(current)
            if dated:
                current[0] = dated.group(0)
        elif line.startswith((" ", "\t")) and line.strip() and current:
            current[1] += " " + line.strip()
        elif not line.strip() or line.startswith("- "):
            current = None
    return title, [tuple(f) for f in fields], [tuple(e) for e in log]


def fields_after_log(text):
    """The field labels that come below the note's first log line."""
    labels = [match.group(1) for match in map(ITEM.match, text.splitlines()[1:])
              if match]
    first = next((i for i, label in enumerate(labels) if DAY.match(label)),
                 len(labels))
    return [label for label in labels[first:] if not DAY.match(label)]


def template_fields(text):
    """The field labels of the template's first Markdown example, in order."""
    if "```markdown" not in text:
        raise ValueError("template has no ```markdown example")
    block = text.split("```markdown", 1)[1].split("```", 1)[0]
    return [label for label, _ in parse(block.strip())[1]
            if not label.startswith("<")]


def live_state(line, in_log):
    """The kinds of live state `line` copies: any in a field, and in a log
    line only a mergeable state it opens with."""
    if in_log:
        return ["mergeable state"] if LIVE_LOG.match(line) else []
    return [name for name, pattern in LIVE if pattern.search(line)]


def lint_note(repo, number, text, fields):
    """Every way one note departs from the template's shape."""
    title, got, log = parse(text)
    findings = []
    match = TITLE.match(title)
    if not match:
        findings.append(f"title is not '# {repo}#{number} — ...'")
    elif (match.group(1), match.group(2)) != (repo, str(number)):
        findings.append(f"title names {match.group(1)}#{match.group(2)}")
    labels = [label for label, _ in got]
    if labels != fields:
        findings.append(f"fields {', '.join(labels) or 'none'}, "
                        f"not {', '.join(fields)}")
    if got and got[0][0] == fields[0] and not READ.search(got[0][1]):
        findings.append(f"no 'read <date>' on {fields[0]}")
    if len(log) > LOG_LINES:
        findings.append(f"{len(log)} log lines, more than {LOG_LINES}")
    days = [day for day, _ in log]
    if days != sorted(days, reverse=True):
        findings.append("log not newest-first")
    findings += [f"{day} is not a date" for day in days if not is_day(day)]
    findings += [f"{label} after the log" for label in fields_after_log(text)]
    for where, line, in_log in ([(label, line, False) for label, line in got
                                 if label in fields]
                                + [(day, line, True) for day, line in log]):
        for kind in live_state(line, in_log):
            findings.append(f"{where}: copies {kind}")
    return findings


def lint(root, template):
    """Findings over every WORK/<repo>/<number>.md under `root`."""
    fields = template_fields(template.read_text())
    if not (root / "WORK").is_dir():
        raise FileNotFoundError(f"no WORK/ in {root}")
    out = []
    for path in sorted((root / "WORK").glob("*/*.md")):
        if not path.stem.isdigit():
            continue
        for finding in lint_note(path.parent.name, path.stem, path.read_text(), fields):
            out.append(f"WORK/{path.parent.name}/{path.name}: {finding}")
    return out


def touched_finding(item, text, since_day):
    """What is missing for one touched item: its note, or a log line since."""
    closed = item["state"] == "closed"
    if text is None:
        return None if closed else "no note"
    if closed:
        return "closed, note not deleted"
    if not any(is_day(day) and day >= since_day for day, _ in parse(text)[2]):
        return f"no log line dated {since_day} or later"
    return None


def skeleton(rows):
    """The day-PR comment's list, one line per touched item for the agent to finish."""
    return [f"- {repo}#{item['number']} ({item['title']}): " for repo, item in rows]


def touched(root, setup, since):
    """Print touched items missing a note or a line, then the comment skeleton."""
    repos = list(dict.fromkeys(
        setup["WORK_REPOS"] + [setup["MEMORY_REPO"], setup["DESIRE_REPO"]]))
    since_day, rows, findings, incomplete = since[:10], [], [], False
    for repo in repos:
        try:
            items = search(setup["AGENT"], repo, since)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as error:
            reason = getattr(error, "code", None) or type(error).__name__
            print(f"{repo}: n/a ({reason})")
            incomplete = True
            continue
        for item in sorted(items, key=lambda i: i["number"]):
            if day_pr(repo, item, setup):
                continue
            rows.append((repo, item))
            path = note_path(root, repo, item["number"])
            text = path.read_text() if path.exists() else None
            finding = touched_finding(item, text, since_day)
            if finding:
                findings.append(f"{repo}#{item['number']}: {finding} "
                                f"(WORK/{path.parent.name}/{path.name})")
    print("\n".join(findings) or ("incomplete" if incomplete else "clean"))
    print("\nDay-PR comment:")
    print("\n".join(skeleton(rows)) or "(nothing touched)")
    return 2 if incomplete else 1 if findings else 0


def main(argv):
    """Parse the command line and run one check."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["touched", "lint"])
    parser.add_argument("--since")
    parser.add_argument("--config")
    parser.add_argument("--template", default=str(TEMPLATE))
    args = parser.parse_args(argv)
    if args.command == "touched" and not (args.since and SINCE.fullmatch(args.since)):
        parser.error("touched needs --since <ISO8601>, e.g. 2026-09-01T08:00:00Z")
    path = config_path(args.config)
    try:
        if args.command == "lint":
            findings = lint(path.resolve().parent, pathlib.Path(args.template))
            print("\n".join(findings) or "clean")
            return 1 if findings else 0
        setup = config(path)
        missing = [k for k in ("AGENT", "WORK_REPOS", "MEMORY_REPO", "DESIRE_REPO")
                   if not setup.get(k)]
        if missing:
            raise ValueError(f"{path}: no {', '.join(missing)}")
        return touched(path.resolve().parent, setup, args.since)
    except (OSError, ValueError) as error:
        print(f"n/a ({error})")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
