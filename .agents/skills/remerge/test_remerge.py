#!/usr/bin/env python3
"""What `remerge.py` claims, as tests: the CHANGELOG.md resolution, the
stale-name and intent checks, and whole runs on throwaway git repos.

Run: python3 -m unittest discover -s .agents/skills/remerge -p 'test_*.py'
"""
import contextlib
import io
import pathlib
import re
import subprocess
import tempfile
import unittest
import unittest.mock

import remerge

LOG = """# Changelog

## [Unreleased]

### Added

- `a`, the first ([#1]).
- `b`, the second, over
  two lines ([#2]).

### Fixed

- `c` ([#3]).

[#1]: https://example.test/1
[#2]: https://example.test/2
[#3]: https://example.test/3
"""


def diff(old, new):
    """git's -U0 diff of two texts, without a repository."""
    with tempfile.TemporaryDirectory() as tmp:
        a, b = pathlib.Path(tmp, "a"), pathlib.Path(tmp, "b")
        a.write_text(old)
        b.write_text(new)
        return subprocess.run(["git", "diff", "--no-index", "-U0", str(a), str(b)],
                              capture_output=True, text=True).stdout


def edit(text, after, lines):
    """text with lines inserted after the line `after`."""
    out = text.splitlines()
    i = out.index(after) + 1
    return "\n".join(out[:i] + lines + out[i:]) + "\n"


class Changelog(unittest.TestCase):
    """The base's file plus the branch's own added blocks, nothing else."""

    def setUp(self):
        self.branch = edit(edit(LOG, "  two lines ([#2]).", ["- `d`, ours ([#9])."]),
                           "[#3]: https://example.test/3", ["[#9]: https://example.test/9"])
        self.base = edit(edit(LOG, "### Added", ["", "- `e`, theirs ([#8])."]),
                         "[#3]: https://example.test/3", ["[#8]: https://example.test/8"])

    def test_both_sides_keep_their_lines_once(self):
        text, count = remerge.resolve_changelog(LOG, self.base, diff(LOG, self.branch))
        self.assertEqual(count, 2)
        for line in ["- `d`, ours ([#9]).", "- `e`, theirs ([#8]).",
                     "[#9]: https://example.test/9", "[#8]: https://example.test/8"]:
            self.assertEqual(text.splitlines().count(line), 1, line)
        self.assertLess(text.index("`d`, ours"), text.index("### Fixed"))
        self.assertGreater(text.index("[#9]:"), text.index("[#3]:"))

    def test_a_line_already_in_the_base_is_dropped(self):
        base = edit(LOG, "  two lines ([#2]).", ["- `d`, ours ([#9])."])
        text, count = remerge.resolve_changelog(LOG, base, diff(LOG, self.branch))
        self.assertEqual(text.count("`d`, ours"), 1)
        self.assertEqual(count, 1)

    def test_an_edited_line_stops(self):
        branch = LOG.replace("`c` ([#3]).", "`c`, fixed ([#3]).")
        with self.assertRaisesRegex(remerge.Stop, "removes or edits"):
            remerge.resolve_changelog(LOG, self.base, diff(LOG, branch))

    def test_a_lost_anchor_stops(self):
        base = LOG.replace("  two lines ([#2]).\n\n### Fixed", "  three ([#2]).\n### Gone")
        with self.assertRaisesRegex(remerge.Stop, "no unique place"):
            remerge.resolve_changelog(LOG, base, diff(LOG, self.branch))

    def test_a_heading_the_base_has_takes_the_block_under_it(self):
        mb = "# Log\n\n## 10-28\n\n- old\n"
        base = "# Log\n\n## 10-29\n\n- theirs\n\n## 10-28\n\n- old\n"
        branch = "# Log\n\n## 10-29\n\n- ours\n\n## 10-28\n\n- old\n"
        text, count = remerge.resolve_changelog(mb, base, diff(mb, branch))
        self.assertEqual(text, "# Log\n\n## 10-29\n\n- ours\n\n- theirs\n\n## 10-28\n\n- old\n")
        self.assertEqual(count, 1)

    def test_a_blank_line_is_no_anchor(self):
        self.assertEqual(remerge.anchor(["", "", "y"], 1, ["", "", "", "y"]), 2)


class Names(unittest.TestCase):
    """Modules and top-level names, and the lines that use them."""

    def test_dotted(self):
        self.assertEqual(remerge.dotted("pkg/sub/mod.py"), "pkg.sub.mod")
        self.assertEqual(remerge.dotted("pkg/sub/__init__.py"), "pkg.sub")

    def test_defined(self):
        text = "class A:\n    def inner(self): ...\ndef f(): ...\nB = A\nC: int = 1\nif B == 1: pass\n"
        self.assertEqual(remerge.defined(text), {"A", "f", "B", "C"})

    def matches(self, line, module, name=None):
        return any(re.search(p, line) for p in remerge.patterns(module, name))

    def test_a_module(self):
        for line in ["from pkg.old import x", "import pkg.old as o", "y = pkg.old.x",
                     "from pkg import old"]:
            self.assertTrue(self.matches(line, "pkg.old"), line)
        for line in ["from pkg.older import x", "path = 'docs/pkg.old.svg'",
                     "from pkg import oldest"]:
            self.assertFalse(self.matches(line, "pkg.old"), line)

    def test_a_top_level_module_needs_an_import(self):
        self.assertTrue(self.matches("import readme", "readme"))
        self.assertFalse(self.matches("text = readme.read_text()", "readme"))

    def test_a_name(self):
        for line in ["from pkg.group import Group", "g = group.Group()",
                     "from .group import Group, x", "pkg.group.Group"]:
            self.assertTrue(self.matches(line, "pkg.group", "Group"), line)
        for line in ["abc.Group", "group.GroupAlgebra", "from pkg.abc import Group"]:
            self.assertFalse(self.matches(line, "pkg.group", "Group"), line)


class Intent(unittest.TestCase):
    """A merged tree differs from the base by the branch's own change."""

    def test_a_diff_by_file(self):
        text = ("diff --git a/my f.py b/my f.py\n--- a/my f.py\n+++ b/my f.py\n"
                "@@ -1 +1,2 @@\n-old\n+new\n+--- x\n@@ -9,0 +10 @@\n+end\n"
                "diff --git a/img.png b/img.png\nBinary files a/img.png and b/img.png differ\n"
                'diff --git "a/q\\"t" "b/q\\"t"\n@@ -1 +1 @@\n-a\n+b\n')
        self.assertEqual(remerge.changes(text), {
            "my f.py": [("-old", "+new", "+--- x"), ("+end",)],
            "img.png": [("Binary files a/img.png and b/img.png differ",)],
            'q\\"t': [("-a", "+b")]})

    def test_a_hunk_the_base_made_too_is_not_the_branch_s_own(self):
        ours = {"f": [("+x",), ("+",)], "g": [("-y", "+z")]}
        theirs = {"f": [("+x",)], "g": [("-y", "+w")]}
        self.assertEqual(remerge.own(ours, theirs), {"f": [("+",)], "g": [("-y", "+z")]})

    def test_lost_grew_and_untouched(self):
        ours = {"f": [("+x", "-y")], "g": [("+z",)]}
        merged = {"f": [("+x",)], "g": [("+z",)], "h": [("+w",)], "CHANGELOG.md": []}
        self.assertEqual(remerge.lost_changes(ours, merged), [
            "f: 1 changed lines lost, 0 gained",
            "h: differs from the base though the branch never touched it"])


def run(cwd, *args):
    """A git command in cwd, its stdout."""
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


class Runs(unittest.TestCase):
    """Whole runs against an origin on disk."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.origin, self.clone, self.config = root / "origin", root / "clone", root / "config.env"
        self.config.write_text("# test\nAGENT=bot\nAGENT_EMAIL=bot@example.test\n")
        self.origin.mkdir()
        run(self.origin, "init", "-q", "-b", "main")
        self.identity(self.origin)
        self.write(self.origin, {"CHANGELOG.md": LOG, "pkg/__init__.py": "",
                                 "pkg/old.py": "def f():\n    return 1\n\n\ndef g():\n    return 2\n",
                                 "pkg/use.py": "from pkg.old import f\n"})
        run(self.origin, "commit", "-q", "-am", "start")
        run(root, "clone", "-q", str(self.origin), str(self.clone))
        self.identity(self.clone)
        run(self.clone, "checkout", "-q", "-b", "feature")
        run(self.clone, "push", "-q", "origin", "feature")

    def tearDown(self):
        self.tmp.cleanup()

    def identity(self, repo):
        run(repo, "config", "user.name", "bot")
        run(repo, "config", "user.email", "bot@example.test")
        run(repo, "config", "commit.gpgsign", "false")

    def write(self, repo, files, message=None):
        for path, text in files.items():
            pathlib.Path(repo, path).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(repo, path).write_text(text)
        run(repo, "add", "-A")
        if message:
            run(repo, "commit", "-q", "-m", message)

    def remerge(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = remerge.main([str(self.clone), "main", "--config", str(self.config), *args])
        return code, out.getvalue() + err.getvalue()

    def both_add_to_the_changelog(self):
        self.write(self.clone, {"CHANGELOG.md": edit(LOG, "- `a`, the first ([#1]).",
                                                     ["- `d`, ours ([#9])."]),
                                "pkg/new.py": "x = 1\n"}, "ours")
        self.write(self.origin, {"CHANGELOG.md": edit(LOG, "- `a`, the first ([#1]).",
                                                      ["- `e`, theirs ([#8])."])}, "theirs")

    def test_a_branch_origin_lacks_stops(self):
        run(self.clone, "checkout", "-q", "-b", "local")
        code, out = self.remerge("--dry-run")
        self.assertEqual(code, 2)
        self.assertIn("couldn't find remote ref refs/heads/local", out)

    def test_a_clean_merge_says_so(self):
        self.write(self.clone, {"pkg/new.py": "x = 1\n"}, "ours")
        self.write(self.origin, {"pkg/other.py": "y = 2\n"}, "theirs")
        self.assertIn("clean: it would merge", self.remerge("--dry-run")[1])
        self.assertEqual(self.remerge()[0], 0)
        self.assertEqual(run(self.clone, "log", "-1", "--format=%B").strip(),
                         "Merge main into feature")

    def test_a_change_the_base_already_has_is_not_lost(self):
        self.write(self.clone, {"pkg/use.py": "from pkg.old import f, g\n"}, "ours")
        self.write(self.origin, {"pkg/use.py": "from pkg.old import f, g\n",
                                 "pkg/other.py": "y = 2\n"}, "squashed")
        code, out = self.remerge("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.remerge()[0], 0)

    def test_up_to_date(self):
        code, out = self.remerge()
        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("up to date\n"), out)

    def test_a_changelog_conflict_resolves_and_commits(self):
        self.both_add_to_the_changelog()
        old = run(self.clone, "rev-parse", "HEAD").strip()
        code, out = self.remerge("--trailer", "Co-Authored-By: Bot <bot@example.test>")
        self.assertEqual(code, 0, out)
        text = (self.clone / "CHANGELOG.md").read_text()
        self.assertIn("`d`, ours", text)
        self.assertIn("`e`, theirs", text)
        self.assertNotIn("<<<<<<<", text)
        message = run(self.clone, "log", "-1", "--format=%B")
        self.assertTrue(message.startswith("Merge main into feature\n\nCHANGELOG.md: the base's"))
        self.assertTrue(message.strip().endswith("Co-Authored-By: Bot <bot@example.test>"))
        self.assertEqual(run(self.clone, "log", "-1", "--format=%P").split()[0], old)
        self.assertIn("git push origin HEAD", out)

    def test_dry_run_writes_nothing(self):
        self.both_add_to_the_changelog()
        old = run(self.clone, "rev-parse", "HEAD")
        code, out = self.remerge("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("CHANGELOG.md: the base's file plus 1 block(s)", out)
        self.assertEqual(run(self.clone, "rev-parse", "HEAD"), old)

    def test_another_conflict_aborts(self):
        self.write(self.clone, {"pkg/old.py": "def f():\n    return 3\n"}, "ours")
        self.write(self.origin, {"pkg/old.py": "def f():\n    return 4\n"}, "theirs")
        old = run(self.clone, "rev-parse", "HEAD")
        self.assertEqual(self.remerge("--dry-run")[0], 1)
        code, out = self.remerge()
        self.assertEqual(code, 2)
        self.assertIn("conflicts: pkg/old.py", out)
        self.assertEqual(run(self.clone, "rev-parse", "HEAD"), old)
        self.assertEqual(run(self.clone, "status", "--porcelain", "--untracked-files=no"), "")

    def test_a_renamed_module_and_a_removed_name_are_stale(self):
        self.write(self.clone, {"pkg/mine.py": "from pkg.old import g\nimport pkg.old\n"}, "ours")
        run(self.origin, "mv", "pkg/old.py", "pkg/fresh.py")
        self.write(self.origin, {"pkg/use.py": "from pkg.fresh import f\n"}, "rename")
        code, out = self.remerge()
        self.assertEqual(code, 1, out)
        self.assertIn("stale: pkg/mine.py:1: from pkg.old import g  (pkg.old now pkg.fresh)", out)
        self.assertIn("stale: pkg/mine.py:2:", out)
        self.assertNotIn("pkg/use.py", out)

    def test_a_removed_name(self):
        self.write(self.clone, {"pkg/mine.py": "from pkg.old import g\n"}, "ours")
        self.write(self.origin, {"pkg/old.py": "def f():\n    return 1\n"}, "drop g")
        code, out = self.remerge("--dry-run")
        self.assertEqual(code, 1, out)
        self.assertIn("stale: pkg/mine.py:1: from pkg.old import g  (pkg.old.g removed)", out)

    def test_a_failing_check_aborts(self):
        self.both_add_to_the_changelog()
        old = run(self.clone, "rev-parse", "HEAD")
        code, out = self.remerge("--check", "exit 3")
        self.assertEqual(code, 4)
        self.assertEqual(run(self.clone, "rev-parse", "HEAD"), old)

    def test_a_lost_change_aborts(self):
        self.write(self.clone, {"pkg/use.py": "from pkg.old import f, g\n"}, "ours")
        self.write(self.origin, {"pkg/use.py": "from pkg.old import f  # base\n"}, "theirs")
        (self.clone / ".git" / "info" / "attributes").write_text("pkg/use.py merge=theirs\n")
        run(self.clone, "config", "merge.theirs.driver", "cp %B %A")
        code, out = self.remerge()
        self.assertEqual(code, 3, out)
        self.assertIn("intent: pkg/use.py: 2 changed lines lost", out)

    def test_a_wrong_identity_stops(self):
        self.config.write_text("AGENT=someone\nAGENT_EMAIL=else@example.test\n")
        self.both_add_to_the_changelog()
        code, out = self.remerge()
        self.assertEqual(code, 2)
        self.assertIn("config.env says someone <else@example.test>", out)

    def test_a_wrong_author_stops(self):
        self.both_add_to_the_changelog()
        with unittest.mock.patch.dict("os.environ", {"GIT_AUTHOR_NAME": "someone"}):
            code, out = self.remerge()
        self.assertEqual(code, 2)
        self.assertIn("git authors as someone <bot@example.test>", out)

    def test_a_failed_refetch_after_the_commit_still_reports_the_merge(self):
        self.both_add_to_the_changelog()
        old = run(self.clone, "rev-parse", "HEAD")
        real = remerge.fetch
        calls = []

        def fetch(repo, branch):
            calls.append(branch)
            if len(calls) > 2:
                raise remerge.Stop("git fetch: n/a (exit 128) offline")
            real(repo, branch)

        with unittest.mock.patch.object(remerge, "fetch", fetch):
            code, out = self.remerge()
        self.assertEqual(code, 0, out)
        self.assertNotEqual(run(self.clone, "rev-parse", "HEAD"), old)
        self.assertIn("could not check whether origin/main moved again", out)

    def test_a_shallow_clone_is_completed(self):
        self.write(self.origin, {"pkg/other.py": "y = 2\n"}, "theirs")
        shallow = pathlib.Path(self.tmp.name, "shallow")
        run(self.tmp.name, "clone", "-q", "--depth", "1", f"file://{self.origin}", str(shallow))
        self.clone = shallow
        self.assertEqual(self.remerge("--dry-run")[0], 0)
        self.assertEqual(run(shallow, "rev-parse", "--is-shallow-repository").strip(), "false")


if __name__ == "__main__":
    unittest.main()
