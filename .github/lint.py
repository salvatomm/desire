#!/usr/bin/env python3
"""What the prompts promise about themselves, checked rather than trusted: the
links resolve, the deny lists name real tools, no rule is stated twice, the
loaded prompts fit their budget, and with `--memory` a MEMORY_REPO clone matches the seed it came from
and its board fits under 200 lines.

Run: python3 .github/lint.py [--memory <path to MEMORY_REPO clone>]
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = ROOT / "template" / "memory"

# The prompts a session loads, and the bytes all of them may take together.
PROMPTS = ["AGENTS.md", "BIRDSONG.md", "EVENING.md"]
BUDGET = 30_000

# The MCP servers a deny list may name: a wrong server name denies nothing.
SERVERS = {"claude-code-remote"}

# Files a MEMORY_REPO clone carries verbatim from the seed.
COPIES = [".claude/settings.json", ".claude/hooks/session-start.sh",
          ".agents/skills/sweep/sweep.py", ".agents/skills/sweep/test_sweep.py"]

# The files that state rules, and the run of words two of them may not share.
RULES = ["AGENTS.md", "BIRDSONG.md", "EVENING.md", "OPERATIONS.md",
         "template/memory/AGENTS.md", "template/memory/README.md",
         "template/memory/WORK/TEMPLATE.md", "template/memory/OTHERS/TEMPLATE.md",
         "template/memory/.github/PULL_REQUEST_TEMPLATE.md"]
PHRASE = 8

LINK = re.compile(r"\]\(([^)\s]+)(?:\s+[^)]*)?\)")
IMPORT = re.compile(r"^@(\S+)$", re.MULTILINE)
ITEM = re.compile(r"(?:[\w.-]+/)?[\w.-]*#\d+")


def slug(heading):
    """GitHub's anchor for a heading: lowercase, punctuation dropped, spaces
    to hyphens."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading.strip().lower())
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(path):
    """Every heading's anchor, a repeated one suffixed `-1`, `-2` in order."""
    seen, found = {}, set()
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            base = slug(line.lstrip("#"))
            found.add(f"{base}-{seen[base]}" if base in seen else base)
            seen[base] = seen.get(base, 0) + 1
    return found


def links(root, skip=("CHANGELOG.md",)):
    """Every relative link in a Markdown file that points nowhere. The
    changelog is history and may name files that are gone."""
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts or path.name in skip:
            continue
        for target in LINK.findall(path.read_text()):
            if re.match(r"[a-z]+:", target):
                continue
            name, _, anchor = target.partition("#")
            where = (path.parent / name).resolve() if name else path
            if not where.exists():
                yield f"{path.relative_to(root)}: no such file {target}"
            elif anchor and where.suffix == ".md" and anchor not in anchors(
                    where):
                yield f"{path.relative_to(root)}: no such heading {target}"


def loaded(path, missing):
    """The bytes a file puts in context with every `@` import it pulls in,
    collecting the imports that point nowhere into `missing`."""
    size = len(path.read_bytes())
    for name in IMPORT.findall(path.read_text()):
        if (path.parent / name).exists():
            size += loaded(path.parent / name, missing)
        else:
            missing.append(f"{path.name}: imports {name}, which does not exist")
    return size


def budget():
    missing = []
    if (size := sum(loaded(ROOT / name, missing) for name in PROMPTS)) > BUDGET:
        yield f"the prompts load {size} bytes, over the budget of {BUDGET}"
    yield from missing


def phrases(path):
    """Every run of `PHRASE` words in a file, its link targets dropped."""
    text = re.sub(r"\]\([^)]*\)", "]", path.read_text().lower())
    words = re.findall(r"[\w']+", text)
    return {" ".join(words[i:i + PHRASE])
            for i in range(len(words) - PHRASE + 1)}


def repeated():
    """A rule stated in two files, which drift apart: say it in one, link
    it from the other."""
    seen, pairs = {}, {}
    for name in RULES:
        for phrase in sorted(phrases(ROOT / name)):
            if seen.setdefault(phrase, name) != name:
                pairs.setdefault((name, seen[phrase]), phrase)
    for (name, first), phrase in pairs.items():
        yield f"{name} repeats {first}: \"{phrase}\""


def denied():
    """The tools the seed denies, from the settings file and from the hook
    that writes the same list into the workspace settings."""
    settings = json.loads((SEED / ".claude/settings.json").read_text())
    hook = (SEED / ".claude/hooks/session-start.sh").read_text()
    written = json.loads(re.search(r"^deny='(.*)'$", hook, re.M).group(1))
    return set(settings["permissions"]["deny"]), set(written)


def deny():
    settings, written = denied()
    if settings != written:
        yield f"the hook denies {sorted(written ^ settings)} and the" \
              " settings do not, or the other way round"
    for tool in settings | written:
        server = re.fullmatch(r"mcp__(.+?)__\w+", tool)
        if tool.startswith("mcp") and (
                not server or server.group(1) not in SERVERS):
            yield f"deny names {tool}, on no server in {sorted(SERVERS)}"


def bullets(text):
    """Each list item of a Markdown file, its continuation lines joined."""
    item = None
    for line in text.splitlines():
        if line.startswith("- "):
            if item:
                yield item
            item = line
        elif item and line.startswith("  "):
            item += " " + line.strip()
        else:
            if item:
                yield item
            item = None
    if item:
        yield item


def single(board):
    """Board lines about exactly one item, which belong in its `WORK/` note."""
    for line in bullets(board):
        if len(set(ITEM.findall(line))) == 1:
            yield f"the board has a line about one item: {line[:70]}"


def memory(clone):
    for name in COPIES:
        if not (clone / name).exists():
            yield f"{clone.name}/{name} is missing, the seed carries it"
        elif (clone / name).read_bytes() != (SEED / name).read_bytes():
            yield f"{clone.name}/{name} differs from template/memory/{name}"
    board = (clone / "README.md").read_text()
    if (lines := len(board.splitlines())) > 200:
        yield f"the board is {lines} lines, over 200"
    yield from single(board)
    yield from (f"{clone.name}/{finding}" for finding in links(clone))


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--memory", type=pathlib.Path)
    options = parser.parse_args(arguments)
    findings = [*links(ROOT), *budget(), *deny(), *repeated()]
    if options.memory:
        findings += memory(options.memory.resolve())
    print("\n".join(findings) or "clean")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
