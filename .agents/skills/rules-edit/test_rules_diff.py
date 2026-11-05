#!/usr/bin/env python3
"""What `rules_diff.py` reports on a diff, as tests.

Run: python3 -m unittest discover -s .agents/skills/rules-edit -p 'test_*.py'
"""
import contextlib
import io
import pathlib
import subprocess
import tempfile
import unittest

import rules_diff

SETUP = {"USER": "alice", "AGENT": "alice-bots", "AGENT_EMAIL": "bots@example.test",
         "WORK_REPOS": ["acme/widgets", "alice/memory", "acme/notes"],
         "MEMORY_REPO": "alice/memory"}
DIFF = """diff --git a/AGENTS.md b/AGENTS.md
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -3,2 +3,2 @@
-Merge only once the item in progress is done.
-Run `old_name` first.
+Merge it.
+Never ask twice.
diff --git a/tool.py b/tool.py
--- a/tool.py
+++ b/tool.py
@@ -1,0 +2,2 @@
+# explains why
+#!/not/a/shebang
diff --git a/gone.md b/gone.md
--- a/gone.md
+++ /dev/null
@@ -1 +0,0 @@
-Every rule here is gone.
"""


class Values(unittest.TestCase):
    """Owners, USER, AGENT and email always; repo names as words or `name#N`."""

    def test_split(self):
        always, names = rules_diff.values(SETUP)
        self.assertEqual(always, ["acme", "alice", "alice-bots", "bots@example.test"])
        self.assertEqual(names, ["memory", "notes", "widgets"])

    def test_whole_words_only(self):
        always, names = rules_diff.values(SETUP)
        self.assertEqual(rules_diff.hits("see acme/widgets#4", always, names),
                         ["acme", "widgets"])
        self.assertEqual(rules_diff.hits("acmeish widgetsmith", always, names), [])
        self.assertEqual(rules_diff.hits("alice-bots pushed", always, []), ["alice-bots"])
        self.assertEqual(rules_diff.hits("filed as notes#12.", [], names), ["notes"])

    def test_a_name_the_base_uses_plainly_is_generic(self):
        lines = ["long-term memory lives here", "acme/notes is private"]
        self.assertEqual(rules_diff.generic(lines, ["acme"], ["memory", "notes"]),
                         {"memory"})


class Parse(unittest.TestCase):
    """A -U0 diff becomes (path, sign, line, text), deleted files keeping their path."""

    def setUp(self):
        self.changes = list(rules_diff.parse(DIFF))

    def test_lines(self):
        self.assertIn(("AGENTS.md", "+", 4, "Never ask twice."), self.changes)
        self.assertIn(("gone.md", "-", 0, "Every rule here is gone."), self.changes)

    def test_body_lines_that_look_like_headers(self):
        diff = ("diff --git a/A.md b/A.md\n--- a/A.md\n+++ b/A.md\n@@ -2 +2 @@\n"
                "--- only once\n+++ acme/x#3\n")
        self.assertEqual(list(rules_diff.parse(diff)),
                         [("A.md", "-", 2, "-- only once"), ("A.md", "+", 2, "++ acme/x#3")])

    def test_leaks_skip_the_changelog(self):
        changes = [("CHANGELOG.md", "+", 1, "acme"), ("README.md", "+", 2, "acme/x")]
        found = list(rules_diff.leaks(changes, ["acme"], []))
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("README.md:2"))

    def test_comments_not_shebangs(self):
        found = list(rules_diff.comments(self.changes))
        self.assertEqual(len(found), 1)
        self.assertIn("explains why", found[0])

    def test_new_never_clause(self):
        found = list(rules_diff.asserted(self.changes))
        self.assertEqual(found, ['AGENTS.md:4: "Never ask twice."'])

    def test_dropped_clause_unless_said_elsewhere(self):
        said = rules_diff.sentences("Merge it. Never ask twice.")
        found = list(rules_diff.dropped(self.changes, said, {"gone.md"}))
        self.assertEqual(found, ['AGENTS.md: "only once the item in progress is done"'])
        said = rules_diff.sentences("Merge only once the item is in progress.")
        self.assertEqual(list(rules_diff.dropped(self.changes, said, {"gone.md"})), [])

    def test_removed_names(self):
        self.assertEqual(rules_diff.removed_names(self.changes)["AGENTS.md"], {"old_name"})
        changes = [("a.py", "-", 0, "def cited(x):"), ("a.py", "+", 1, "def owned(x):")]
        self.assertEqual(rules_diff.removed_names(changes), {"a.py": {"cited("}})
        self.assertFalse(rules_diff.identifier("blocked"))


class Changelog(unittest.TestCase):
    """Reasons outside quotes, and an entry under today's top heading."""

    def test_causal_outside_quotes(self):
        changes = [("CHANGELOG.md", "+", 1, "**Rule** — x, so that y."),
                   ("CHANGELOG.md", "+", 2, 'USER: *"do it because"*. Ruling: #3.'),
                   ("CHANGELOG.md", "+", 3, "reads every PR since its last turn"),
                   ("CHANGELOG.md", "+", 4, "a gate, since it failed")]
        found = list(rules_diff.causal(changes))
        self.assertEqual([f.split(":")[1] for f in found], ["1", "4"])

    def test_entry(self):
        text = "# Changelog\n\n## 2026-11-05\n\n**Rule** (`AGENTS.md`) — x.\n\n## 2026-10-01\n"
        good = [("CHANGELOG.md", "+", 5, "**Rule** (`AGENTS.md`) — x.")]
        self.assertEqual(rules_diff.entry(good, text, "2026-11-05"), [])
        self.assertEqual(len(rules_diff.entry(good, text, "2026-11-06")), 1)
        late = [("CHANGELOG.md", "+", 8, "plain line")]
        self.assertEqual(len(rules_diff.entry(late, text, "2026-11-05")), 2)
        self.assertEqual(rules_diff.entry([("AGENTS.md", "+", 1, "x")], "", "d"),
                         ["rule files changed and CHANGELOG.md gained no entry"])


class Config(unittest.TestCase):
    """config.env read like the sweep reads it."""

    def test_parse(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "config.env"
            path.write_text("# seed\nUSER=alice\nAGENT=bots\nWORK_REPOS=a/b, c/d\n")
            self.assertEqual(rules_diff.config(path),
                             {"USER": "alice", "AGENT": "bots", "WORK_REPOS": ["a/b", "c/d"]})
            for text in ("no separator\n", "WORK_REPOS=a/b\n", ""):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    rules_diff.config(path)


class Run(unittest.TestCase):
    """End to end on a throwaway git repo: exit 1 on a leak, 2 on a bad ref."""

    def git(self, *args):
        subprocess.run(["git", "-C", self.folder, *args], check=True, capture_output=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = self.temp.name
        root = pathlib.Path(self.folder)
        (root / "config.env").write_text("USER=alice\nAGENT=alice-bots\n"
                                         "WORK_REPOS=acme/widgets\nMEMORY_REPO=alice/memory\n")
        (root / "AGENTS.md").write_text("Long-term memory.\n")
        self.git("init", "-q", "-b", "main")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
        (root / "AGENTS.md").write_text("Long-term memory.\nSee acme/widgets#2.\n")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "leak")

    def tearDown(self):
        self.temp.cleanup()

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rules_diff.main([*args, "--repo", self.folder,
                                    "--config", f"{self.folder}/config.env"])
        return code, out.getvalue()

    def test_leak(self):
        code, out = self.run_main("main~1")
        self.assertEqual(code, 1)
        self.assertIn("AGENTS.md:2: names acme, widgets", out)

    def test_bad_ref(self):
        code, out = self.run_main("nosuch")
        self.assertEqual(code, 2)
        self.assertTrue(out.startswith("n/a"))

    def test_allow(self):
        code, out = self.run_main("main~1", "--allow", "widgets")
        self.assertEqual((code, out.splitlines()[1].split(":")[2]), (1, " names acme"))


if __name__ == "__main__":
    unittest.main()
