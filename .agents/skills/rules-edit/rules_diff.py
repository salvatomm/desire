#!/usr/bin/env python3
"""Check a DESIRE_REPO branch's diff against its base before it is pushed:
installation values from config.env in added lines are findings; causal words
in the changelog, new comments, dropped clauses and names that outlive their
removal are advisories.

Usage: rules_diff.py <base-ref> [--head REF] [--repo DIR] [--config FILE]
                     [--allow WORD ...]
Exit 0 clean, 1 findings, 2 a read failed (that part prints n/a).
"""
import argparse
import functools
import os
import pathlib
import re
import subprocess
import sys

CHANGELOG = "CHANGELOG.md"
CAUSAL = re.compile(r"\b(because|so that|to avoid|which is why|in order to)\b"
                    r"|(?:^|[,;(—–]\s*)(since)\b", re.I)
QUOTE = re.compile(r"\*\"[^\"]*\"\*|\*\"[^\"]*$|^[^\"]*\"\*")
CLAUSE = re.compile(r"\b(only|every|never|unless|once)\b", re.I)
TICKED = re.compile(r"`([A-Za-z_][\w./-]{2,})`")
DEF = re.compile(r"^\s*(?:def\s+(\w+)|class\s+(\w+))")
COMMENTED = (".py", ".sh", ".yml", ".yaml")
NEW = re.compile(r"\b(never|rather than|instead of|no longer)\b", re.I)
HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
STOP = {"a", "an", "the", "of", "to", "in", "on", "and", "or", "is", "it", "its", "be",
        "by", "for", "as", "at", "that", "this", "with", "from", "when", "what"}


class Unread(Exception):
    """A git read that failed."""


def config(path):
    """config.env as a dict; WORK_REPOS a list. Blank and `#` lines skipped."""
    setup = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"config.env: no key in {line!r}")
        setup[key.strip()] = value.strip()
    if not setup.get("USER") or not setup.get("AGENT"):
        raise ValueError(f"{path}: no USER or AGENT")
    setup["WORK_REPOS"] = [r.strip() for r in setup.get("WORK_REPOS", "").split(",") if r.strip()]
    return setup


def find_config(given):
    """--config, else AGENTS_CONFIG, else ./config.env."""
    return pathlib.Path(given or os.environ.get("AGENTS_CONFIG") or "config.env")


@functools.cache
def word(value):
    """A regex matching `value` as a whole word, a trailing full stop allowed."""
    return re.compile(rf"(?<![\w.@-]){re.escape(value)}(?![\w@-]|\.\w)", re.I)


def values(setup):
    """The always-flagged values, and the bare repo names, from config.env."""
    repos = [*setup["WORK_REPOS"], setup.get("MEMORY_REPO", "")]
    always = {setup.get(k, "") for k in ("USER", "AGENT", "AGENT_EMAIL")}
    always |= {repo.partition("/")[0] for repo in repos}
    names = {repo.partition("/")[2] for repo in repos} - always
    return sorted(v for v in always if v), sorted(n for n in names if n)


def hits(line, always, names):
    """The values a line names: `always` anywhere, `names` as words or `name#N`."""
    lower = line.lower()
    found = [v for v in always if v.lower() in lower and word(v).search(line)]
    return found + [n for n in names if n.lower() in lower and (
        word(n).search(line) or re.search(rf"(?<![\w-]){re.escape(n)}#\d", line, re.I))]


def git(repo, *args, ok=(0,)):
    """A git command's stdout, raising Unread on an exit code not in `ok`."""
    run = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if run.returncode not in ok:
        raise Unread(f"git {' '.join(args[:2])}: {run.stderr.strip()[:120]}")
    return run.stdout


def parse(diff):
    """A unified -U0 diff as (path, sign, line number, text) tuples."""
    path, number, header = None, 0, False
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            path, header = None, True
        elif header and line.startswith("--- "):
            path = line[6:] if line.startswith("--- a/") else None
        elif header and line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else path
        elif line.startswith("@@"):
            header = False
            number = int(re.search(r"\+(\d+)", line).group(1))
        elif path and not header and line[:1] in "+-":
            yield path, line[0], number, line[1:]
            number += line[0] == "+"


def generic(lines, always, names):
    """Repo names the base already uses on lines naming no other value."""
    seen = set()
    for line in lines:
        if (found := hits(line, [], names)) and not hits(line, always, []):
            seen |= set(found)
    return seen


def leaks(changes, always, names):
    """Added lines outside the changelog that name an installation value."""
    for path, sign, number, text in changes:
        if sign == "+" and path != CHANGELOG and (found := hits(text, always, names)):
            yield f"{path}:{number}: names {', '.join(found)}: {text.strip()[:90]}"


def causal(changes):
    """Added changelog lines giving a reason, quotes left out."""
    for path, sign, number, text in changes:
        if sign == "+" and path == CHANGELOG and (m := CAUSAL.search(QUOTE.sub("", text))):
            yield f"{path}:{number}: \"{m.group(1) or m.group(2)}\" gives a reason: {text.strip()[:80]}"


def comments(changes):
    """Added comment lines in code and workflow files."""
    for path, sign, number, text in changes:
        stripped = text.strip()
        if sign == "+" and path and path.endswith(COMMENTED) \
                and re.match(r"#(?:\s|$)", stripped):
            yield f"{path}:{number}: comment: {stripped[:80]}"


def asserted(changes):
    """Added rule lines with a never, rather than, instead of or no longer."""
    for path, sign, number, text in changes:
        if sign == "+" and path.endswith(".md") and path != CHANGELOG \
                and (m := NEW.search(text)):
            yield f"{path}:{number}: \"{text[m.start():].strip()[:80]}\""


def words(text):
    """The lowercase words of a text."""
    return re.findall(r"[\w'-]+", text.lower())


def sentences(text):
    """The sentences of a Markdown text, as word lists."""
    return [words(part) for part in re.split(r"[.;:!?]\s|\n\s*\n", text)]


def blocks(changes, sign, skip=()):
    """Each run of consecutive `sign` lines of one file, joined, with its path."""
    run, last = [], None
    for path, s, _, text in [*changes, (None, None, 0, "")]:
        if (path, s) != last and run:
            yield last[0], " ".join(run)
            run = []
        if s == sign and path not in skip:
            run.append(text.strip())
        last = (path, s)


def dropped(changes, said, deleted):
    """Removed only/every/never/unless/once clauses no sentence at the head says:
    the keyword and the two words after it that matter, together."""
    for path, text in blocks(changes, "-", deleted):
        if not path.endswith(".md") or path == CHANGELOG:
            continue
        for sentence in re.split(r"[.;:!?](?:\s|$)", text):
            for match in CLAUSE.finditer(sentence):
                key = match.group(1).lower()
                clause = [w for w in words(sentence[match.end():]) if w not in STOP][:2]
                if clause and not any(key in s and all(w in s for w in clause)
                                      for s in said):
                    yield f"{path}: \"{sentence[match.start():].strip()[:80]}\""
                    break


def identifier(name):
    """Whether a backticked word reads as a name rather than a plain word."""
    return bool(re.search(r"[_./()A-Z-]", name))


def named(text):
    """The backticked names and the def or class a line carries."""
    names = {n for n in TICKED.findall(text) if identifier(n)}
    return names | {m.group(2) or m.group(1) + "(" for m in [DEF.match(text)] if m}


def removed_names(changes):
    """Per file, the names its removed lines carry that no added line does."""
    added = set().union(*[named(t) for p, s, _, t in changes if s == "+" and p != CHANGELOG])
    found = {}
    for path, sign, _, text in changes:
        if sign == "-":
            found.setdefault(path, set()).update(named(text) - added)
    return found


def survivors(repo, head, removed, texts):
    """Each name a file no longer carries at the head that other files still do."""
    gone = sorted({n for path, names in removed.items()
                   for n in names if not word(n).search(texts.get(path, ""))})
    for name in gone:
        found = git(repo, "grep", "-cF", name, head, "--", ".", f":!{CHANGELOG}", ok=(0, 1))
        places = [line.partition(":")[2] for line in found.splitlines()]
        if places:
            yield f"`{name.rstrip('(')}` left a file and is still in {', '.join(places)}"


def entry(changes, text, day):
    """Whether the changelog gained a bold entry under its top heading, dated `day`."""
    added = [(n, t) for p, s, n, t in changes if p == CHANGELOG and s == "+"]
    rules = [p for p, s, _, _ in changes if p and p.endswith(".md") and p != CHANGELOG]
    if not added:
        return ["rule files changed and CHANGELOG.md gained no entry"] if rules else []
    lines = text.splitlines()
    tops = [i + 1 for i, line in enumerate(lines) if HEADING.match(line)]
    notes = []
    if not tops or HEADING.match(lines[tops[0] - 1]).group(1) != day:
        notes.append(f"CHANGELOG.md's top heading is not ## {day}")
    end = tops[1] if len(tops) > 1 else len(lines) + 1
    if tops and any(not tops[0] <= n < end for n, _ in added):
        notes.append("CHANGELOG.md gained lines outside its top dated section")
    if not any(t.startswith("**") for _, t in added):
        notes.append("CHANGELOG.md gained no line starting with a bold rule")
    return notes


def report(title, lines):
    """A titled block of lines, or nothing."""
    return [f"{title}:", *(f"  {line}" for line in lines)] if lines else []


def show(repo, head, path):
    """A file's text at `head`, empty when it is not there."""
    run = subprocess.run(["git", "-C", str(repo), "show", f"{head}:{path}"],
                         capture_output=True, text=True)
    return run.stdout if not run.returncode else ""


def check(repo, base, head, setup, allow):
    """The findings and advisories of base...head, and whether a read failed."""
    always, names = values(setup)
    span = f"{base}...{head}"
    changes = list(parse(git(repo, "diff", "--no-color", "-U0", "--no-ext-diff", span)))
    tree = git(repo, "grep", "-hI", "-e", ".", base, "--", ".", f":!{CHANGELOG}", ok=(0, 1))
    names = [n for n in names if n not in generic(tree.splitlines(), always, names)
             and n.lower() not in allow]
    findings = list(leaks(changes, always, names))
    deleted = set(git(repo, "diff", "--name-only", "--diff-filter=D", span).split())
    rules = git(repo, "grep", "-h", "-e", "^", head, "--", "*.md", f":!{CHANGELOG}", ok=(0, 1))
    texts = {path: show(repo, head, path) for path in {c[0] for c in changes}}
    advice = report("reason in the changelog", list(causal(changes)))
    advice += report("new comments", list(comments(changes)))
    advice += report("new never/instead clause: did USER say it?", list(asserted(changes)))
    advice += report("clause the head no longer says",
                     list(dropped(changes, sentences(rules), deleted)))
    failed = False
    try:
        advice += report("old names", list(survivors(repo, head, removed_names(changes), texts)))
        day = git(repo, "log", "-1", "--format=%cs", head).strip()
        advice += report("changelog entry", entry(changes, texts.get(CHANGELOG, ""), day))
    except Unread as error:
        advice += [f"n/a: {error}"]
        failed = True
    return findings, advice, failed


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repo", default=".", type=pathlib.Path)
    parser.add_argument("--config")
    parser.add_argument("--allow", action="append", default=[])
    options = parser.parse_args(arguments)
    try:
        setup = config(find_config(options.config))
        findings, advice, failed = check(options.repo, options.base, options.head, setup,
                                         {a.lower() for a in options.allow})
    except (OSError, ValueError, Unread) as error:
        print(f"n/a: {error}")
        return 2
    print("\n".join([*report("installation values (findings)", findings), *advice])
          or "clean")
    return 2 if failed else 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
