#!/usr/bin/env python3
"""Merge a pull request's target branch into the branch checked out in a
worktree, locally, never pushing. Exit 0 merged or up to date, 1 stale names
or (dry run) conflicts, 2 stopped or unreadable, 3 a change lost or grown,
4 the check failed.
"""
import argparse
import collections
import os
import pathlib
import re
import subprocess
import sys

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")
TOP = re.compile(r"^(?:async\s+def|def|class)\s+(\w+)|^(\w+)\s*(?::[^=\n]*)?=(?!=)",
                 re.MULTILINE)
ENTRY = re.compile(r"^(?:[-*] |\[[^\]]+\]:|#)")
SEARCHED = ("*.py", "*.ipynb", "*.md", ":!CHANGELOG.md")
LOG = "CHANGELOG.md"


class Stop(Exception):
    """A step that cannot go on, with its exit code."""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def config(path):
    """config.env as a dict; blank lines and `#` comments skipped."""
    lines = [line for line in pathlib.Path(path).read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    pairs = [line.partition("=") for line in lines]
    if any(not separator or not key.strip() for key, separator, _ in pairs):
        raise ValueError("a line with no key")
    return {key.strip(): value.strip() for key, _, value in pairs}


def git(repo, *args, ok=(0,), feed=None):
    """git's stdout in repo, or (code, stdout) when ok allows other codes."""
    done = subprocess.run(["git", "-C", repo, "-c", "core.quotePath=false", *args],
                          capture_output=True, text=True, input=feed)
    if done.returncode not in ok:
        said = re.sub(r"://[^/@\s]+@", "://", done.stderr.strip())
        raise Stop(f"git {' '.join(args)}: n/a (exit {done.returncode}) {said}")
    return done.stdout if ok == (0,) else (done.returncode, done.stdout)


def show(repo, rev, path):
    """A file's text at a revision, empty when absent."""
    code, text = git(repo, "show", f"{rev}:{path}", ok=(0, 128))
    return text if code == 0 else ""


def ancestor(repo, older, newer="HEAD"):
    """Whether older is already in newer."""
    return git(repo, "merge-base", "--is-ancestor", older, newer, ok=(0, 1))[0] == 0


def fetch(repo, branch):
    """Fetch origin's branch into origin/<branch>."""
    git(repo, "fetch", "-q", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")


def hunks(diff_text):
    """A -U0 diff as (old start, old count, added lines) per hunk."""
    found = []
    for line in diff_text.splitlines():
        match = HUNK.match(line)
        if match:
            found.append((int(match[1]), int(match[2] or 1), []))
        elif found and line.startswith("+"):
            found[-1][2].append(line[1:])
    return found


def anchor(mb_lines, start, base_lines):
    """Where in base_lines a block inserted after mb line `start` goes."""
    if start == 0:
        return 0
    for n in (3, 2, 1):
        before, after = mb_lines[max(0, start - n):start], mb_lines[start:start + n]
        for context, shift in ((before, len(before)), (after, 0)):
            spots = [i + shift for i in range(len(base_lines) - len(context) + 1)
                     if base_lines[i:i + len(context)] == context]
            if any(line.strip() for line in context) and len(spots) == 1:
                return spots[0]
    raise Stop(f"{LOG}: no unique place in the base's file for the lines after"
               f" {mb_lines[start - 1]!r}")


def fresh(block, base_text):
    """A block without the entries the base's file already has."""
    entries = []
    for line in block:
        if not entries or not line.strip() or ENTRY.match(line) or not entries[-1][-1].strip():
            entries.append([line])
        else:
            entries[-1].append(line)
    kept = [entry for entry in entries if not entry[0].strip()
            or "\n" + "\n".join(entry) + "\n" not in "\n" + base_text + "\n"]
    lines = [line for entry in kept for line in entry]
    return lines if any(line.strip() for line in lines) else []


def under(block, base_lines, spot):
    """A block led by a heading the base has, moved under that heading."""
    lead = next((line for line in block if line.strip()), "")
    if not lead.startswith("#") or base_lines.count(lead) != 1:
        return spot, block
    rest, spot = block[block.index(lead) + 1:], base_lines.index(lead) + 1
    while rest and not rest[0].strip():
        rest = rest[1:]
    return spot + (spot < len(base_lines) and not base_lines[spot].strip()), rest


def resolve_changelog(mb_text, base_text, diff_text):
    """The base's file plus the branch's added blocks; (text, blocks kept)."""
    mb_lines, base_lines = mb_text.splitlines(), base_text.splitlines()
    inserts, count = collections.defaultdict(list), 0
    for start, removed, added in hunks(diff_text):
        if removed:
            raise Stop(f"{LOG}: the branch removes or edits lines of it; resolve it by hand")
        spot, block = under(added, base_lines, anchor(mb_lines, start, base_lines))
        block = fresh(block, base_text)
        count += bool(block)
        inserts[spot] += block
    out = []
    for i in range(len(base_lines) + 1):
        out += inserts.get(i, []) + base_lines[i:i + 1]
    return "\n".join(out) + ("\n" if base_text.endswith("\n") else ""), count


def dotted(path):
    """A Python file's module name."""
    name = path[:-3].replace("/", ".")
    return name[:-len(".__init__")] if name.endswith(".__init__") else name


def defined(text):
    """Top-level names a Python file defines or assigns."""
    return {a or b for a, b in TOP.findall(text)}


def patterns(module, name=None):
    """Regexes for an import or use of a module, or of one of its names."""
    parent, _, leaf = module.rpartition(".")
    m, lf, n = re.escape(module), re.escape(leaf), re.escape(name or "")
    if name:
        return [rf"(?<![\w.]){m}\.{n}\b", rf"(?<![\w./]){lf}\.{n}\b",
                rf"^\s*from\s+(?:{m}|\.+{lf})\s+import\s.*\b{n}\b"]
    return [rf"^\s*(?:import|from)\s+{m}\b"] + (
        [rf"(?<![\w./]){m}\.\w", rf"^\s*from\s+{re.escape(parent)}\s+import\s.*\b{lf}\b"]
        if parent else [])


def gone(repo, mb, base, tree):
    """(module, name or None, how) for each one the base removed since mb."""
    lost = []
    for line in git(repo, "diff", "--name-status", "-M", mb, base, "--", "*.py").splitlines():
        status, old, *new = line.split("\t")
        if status[0] in "DR" and not show(repo, tree, old):
            lost.append((dotted(old), None, f"now {dotted(new[0])}" if new else "deleted"))
        if status[0] in "MR":
            still = defined(show(repo, base, (new or [old])[0])) | defined(show(repo, tree, old))
            lost += [(dotted(old), name, "removed")
                     for name in sorted(defined(show(repo, mb, old)) - still)]
    return lost


def stale(repo, mb, base, tree):
    """file:line uses in tree of each module or name the base removed."""
    hits = []
    for module, name, how in gone(repo, mb, base, tree):
        regexes = [re.compile(p) for p in patterns(module, name)]
        _, out = git(repo, "grep", "-n", "-I", "-F", "-e", name or module.rpartition(".")[2],
                     tree, "--", *SEARCHED, ok=(0, 1))
        for line in out.splitlines():
            path, number, text = line[len(tree) + 1:].split(":", 2)
            if any(regex.search(text) for regex in regexes):
                what = f"{module}.{name}" if name else module
                hits.append(f"{path}:{number}: {text.strip()}  ({what} {how})")
    return hits


def changes(diff_text):
    """Per file, the hunks of a -U0 diff as tuples of +/- lines."""
    files, found = {}, None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            rest = line[len("diff --git "):]
            key = rest[3:rest.find('" "')] if rest[0] == '"' else rest[2:(len(rest) - 1) // 2]
            found = files.setdefault(key, [])
        elif found is not None and line.startswith(("@@", "Binary files")):
            found.append((line,) if line[0] == "B" else ())
        elif found and line[:1] in "+-":
            found[-1] += (line,)
    return files


def counted(hunks):
    """The multiset of lines in a list of hunks."""
    return collections.Counter(line for hunk in hunks for line in hunk)


def lost_changes(ours, merged, skip=(LOG,)):
    """Report lines for files whose own change the merge lost or grew."""
    report = []
    for path in sorted((set(ours) | set(merged)) - set(skip)):
        mine, now = counted(ours.get(path, [])), counted(merged.get(path, []))
        lost, grew = sum((mine - now).values()), sum((now - mine).values())
        if path not in ours:
            report.append(f"{path}: differs from the base though the branch never touched it")
        elif lost or grew:
            report.append(f"{path}: {lost} changed lines lost, {grew} gained")
    return report


def own(ours, theirs):
    """The branch's hunks per file, less those the base made too."""
    return {path: [h for h in hunks if h not in theirs.get(path, [])]
            for path, hunks in ours.items()}


def intent(repo, mb, head, base, tree, skip=(LOG,)):
    """lost_changes between the branch's own diff and the merged tree's."""
    diff = lambda old, new: changes(git(repo, "diff", "--no-renames", "-U0", old, new))
    return lost_changes(own(diff(mb, head), diff(mb, base)), diff(base, tree), skip)


def changelog_text(repo, mb, base):
    """The resolved CHANGELOG.md and a line saying how."""
    text, count = resolve_changelog(show(repo, mb, LOG), show(repo, base, LOG),
                                    git(repo, "diff", "-U0", mb, "HEAD", "--", LOG))
    return text, f"{LOG}: the base's file plus {count} block(s) the branch added"


def identity(repo, path):
    """Stop unless git commits as config.env's AGENT and AGENT_EMAIL."""
    try:
        setup = config(path)
        want = f"{setup['AGENT']} <{setup['AGENT_EMAIL']}>"
    except (OSError, ValueError, KeyError) as error:
        raise Stop(f"config.env: n/a ({error})") from error
    ident = git(repo, "var", "GIT_COMMITTER_IDENT").rsplit(" ", 2)[0]
    if ident != want:
        raise Stop(f"git commits as {ident}, config.env says {want}")


def prepare(repo, base):
    """Check the clone and worktree, fetch; (branch, merge base, head)."""
    if git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        git(repo, "fetch", "-q", "--unshallow", "origin", ok=(0, 1, 128))
        if git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
            raise Stop("shallow clone, and `git fetch --unshallow origin` failed")
    branch = git(repo, "symbolic-ref", "--short", "HEAD").strip()
    if git(repo, "status", "--porcelain", "--untracked-files=no").strip():
        raise Stop("the worktree has uncommitted changes")
    fetch(repo, base)
    fetch(repo, branch)
    if not ancestor(repo, f"origin/{branch}"):
        raise Stop(f"origin/{branch} has commits this branch lacks: merge them first")
    mb = git(repo, "merge-base", f"origin/{base}", "HEAD").strip()
    return branch, mb, git(repo, "rev-parse", "HEAD").strip()


def dry_run(repo, remote, mb, head):
    """Print what a real run would meet; the exit code."""
    code, out = git(repo, "merge-tree", "--write-tree", "--name-only", remote, "HEAD",
                    ok=(0, 1))
    tree, *conflicts = out.split("\n\n")[0].splitlines()
    findings = [f"conflict: {path}" for path in sorted(set(conflicts)) if path != LOG]
    if code == 1 and LOG in conflicts:
        try:
            print(changelog_text(repo, mb, remote)[1])
        except Stop as stop:
            findings.append(str(stop))
    hits = stale(repo, mb, remote, tree)
    lost = intent(repo, mb, head, remote, tree, [LOG, *conflicts])
    report = [*findings, *(f"stale: {h}" for h in hits), *(f"intent: {i}" for i in lost)]
    print("\n".join(report) or "clean: it would merge as it stands")
    return 3 if lost else 1 if findings or hits else 0


def merge(repo, branch, remote, mb, head, arguments):
    """Merge, resolve, check and commit; the exit code."""
    code, _ = git(repo, "merge", "--no-ff", "--no-commit", remote, ok=(0, 1))
    try:
        conflicts = git(repo, "diff", "--name-only", "--diff-filter=U").split()
        note = ""
        if code and conflicts != [LOG]:
            raise Stop("conflicts: " + " ".join(conflicts or ["(none listed)"]))
        if conflicts:
            text, note = changelog_text(repo, mb, remote)
            pathlib.Path(repo, LOG).write_text(text)
            git(repo, "add", LOG)
        tree = git(repo, "write-tree").strip()
        hits, lost = stale(repo, mb, remote, tree), intent(repo, mb, head, remote, tree)
        if lost:
            raise Stop("\n".join(f"intent: {line}" for line in lost), 3)
        if arguments.check and subprocess.run(arguments.check, shell=True, cwd=repo).returncode:
            raise Stop(f"check failed: {arguments.check}", 4)
        message = "\n\n".join([f"Merge {arguments.base} into {branch}", note,
                                 "\n".join(arguments.trailer)])
        git(repo, "commit", "-q", "--cleanup=strip", "-F", "-", feed=message)
    except Stop:
        git(repo, "merge", "--abort", ok=(0, 128))
        print("merge aborted, the branch is unchanged", file=sys.stderr)
        raise
    print(f"merged: {note or 'no conflict'}", *(f"stale: {hit}" for hit in hits), sep="\n")
    print(f"old {head}\nnew {git(repo, 'rev-parse', 'HEAD').strip()}")
    fetch(repo, arguments.base)
    if not ancestor(repo, remote):
        print(f"{remote} moved again: run this again before pushing")
    print("push with: git push origin HEAD\na push voids an approval given on the old"
          " SHA, and a review bot may not re-review a push that only merges the base")
    return 1 if hits else 0


def main(argv):
    """Parse the arguments and run; the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("repo", "base", "--check"):
        parser.add_argument(name)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--trailer", action="append", default=[])
    parser.add_argument("--config", default=os.environ.get("AGENTS_CONFIG") or "config.env")
    arguments = parser.parse_args(argv)
    repo, remote = arguments.repo, f"origin/{arguments.base}"
    try:
        if not arguments.dry_run:
            identity(repo, arguments.config)
        branch, mb, head = prepare(repo, arguments.base)
        print(f"{branch} {head[:8]}, {remote} {git(repo, 'rev-parse', remote)[:8]},"
              f" merge base {mb[:8]}")
        if ancestor(repo, remote):
            print("up to date")
            return 0
        if arguments.dry_run:
            return dry_run(repo, remote, mb, head)
        return merge(repo, branch, remote, mb, head, arguments)
    except Stop as stop:
        print(stop, file=sys.stderr)
        return stop.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
