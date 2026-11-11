#!/usr/bin/env python3
"""What `work_notes.py` claims about touched items and the shape of notes.

Run: python3 -m unittest discover -s .agents/skills/work-notes -p 'test_*.py'
"""
import contextlib
import io
import os
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

import work_notes

FIELDS = ["whose", "does", "needs", "touches", "blocks"]
GOOD = """# lib#12 — let statements in closed terms

- **whose** ours · read 2026-09-01
- **does** adds `let` to the internal language of closed categories,
  so a term can name an intermediate value
- **needs** USER's read
- **touches** `closed.py` — collides with #442 on `closed.py`
- **blocks** nothing

- **2026-09-01 🌙 Evening** resolved 19 review threads
- **2026-08-27 🌤️ Daylight** designed the `let` encoding with USER
"""
SETUP = {"USER": "someone", "AGENT": "someone-agents",
         "WORK_REPOS": ["org/lib", "org/docs"], "MEMORY_REPO": "someone/memory",
         "DESIRE_REPO": "someone/desire"}


def item(number, state="open", title="a title", pull=False):
    found = {"number": number, "state": state, "title": title}
    if pull:
        found["pull_request"] = {}
    return found


class Config(unittest.TestCase):
    """config.env is read like the sweep reads it."""

    def test_lists_split_and_comments_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "config.env"
            path.write_text("# seed\nAGENT=bot\nWORK_REPOS=a/b, c/d\n\nAGENT_FOOTERS=x,,y\n")
            setup = work_notes.config(path)
        self.assertEqual(setup["AGENT"], "bot")
        self.assertEqual(setup["WORK_REPOS"], ["a/b", "c/d"])
        self.assertEqual(setup["AGENT_FOOTERS"], ["x", "y"])

    def test_a_line_without_a_key_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "config.env"
            path.write_text("AGENT\n")
            with self.assertRaises(ValueError):
                work_notes.config(path)

    def test_flag_then_environment_then_cwd(self):
        with mock.patch.dict(os.environ, {"AGENTS_CONFIG": "/env/config.env"}):
            self.assertEqual(str(work_notes.config_path("/flag.env")), "/flag.env")
            self.assertEqual(str(work_notes.config_path(None)), "/env/config.env")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(str(work_notes.config_path(None)), "config.env")


class Parse(unittest.TestCase):
    """A note splits into title, fields and dated log lines."""

    def test_fields_log_and_continuations(self):
        title, fields, log = work_notes.parse(GOOD)
        self.assertTrue(title.startswith("# lib#12"))
        self.assertEqual([label for label, _ in fields], FIELDS)
        self.assertIn("intermediate value", fields[1][1])
        self.assertEqual([day for day, _ in log], ["2026-09-01", "2026-08-27"])

    def test_the_real_template_gives_the_five_fields(self):
        self.assertEqual(work_notes.template_fields(work_notes.TEMPLATE.read_text()),
                         FIELDS)


class Lint(unittest.TestCase):
    """Each departure from the template is one finding."""

    def lint(self, text, repo="lib", number="12"):
        return work_notes.lint_note(repo, number, text, FIELDS)

    def test_the_template_example_is_clean(self):
        self.assertEqual(self.lint(GOOD), [])

    def test_title_must_name_the_file(self):
        self.assertEqual(self.lint(GOOD, number="13"), ["title names lib#12"])
        self.assertEqual(self.lint(GOOD.replace(" — ", " - ", 1)),
                         ["title is not '# lib#12 — ...'"])

    def test_a_state_field_breaks_the_order(self):
        text = GOOD.replace("- **whose** ours · read 2026-09-01",
                            "- **state** open · read 2026-09-01\n- **whose** ours")
        self.assertEqual(self.lint(text), [
            "fields state, whose, does, needs, touches, blocks, "
            "not whose, does, needs, touches, blocks"])

    def test_read_date_belongs_on_whose(self):
        self.assertEqual(self.lint(GOOD.replace(" · read 2026-09-01", "")),
                         ["no 'read <date>' on whose"])

    def test_more_than_five_log_lines(self):
        extra = "".join(f"- **2026-08-{day:02d} 🐦 Birdsong** x\n"
                        for day in range(20, 10, -1))
        self.assertIn("12 log lines, more than 5", self.lint(GOOD + extra))

    def test_log_out_of_order(self):
        text = GOOD + "- **2026-09-02 🐦 Birdsong** later, below\n"
        self.assertEqual(self.lint(text), ["log not newest-first"])

    def test_a_field_after_the_log(self):
        text = GOOD.replace("- **blocks** nothing\n", "") + "- **blocks** nothing\n"
        self.assertEqual(self.lint(text), ["blocks after the log"])

    def test_a_log_date_that_is_no_date(self):
        text = GOOD.replace("2026-09-01 🌙", "2026-19-01 🌙")
        self.assertIn("2026-19-01 is not a date", self.lint(text))

    def test_live_state_in_a_field(self):
        for line, kinds in [("CI green on `869fdf1`", ["CI result"]),
                            ("checks green", ["CI result"]),
                            ("CI 7/7 green", ["CI result", "check count"]),
                            ("3/3 checks", ["check count"]),
                            ("a draft, `blocked`", ["mergeable state"]),
                            ("`hypergraph.py` (+197/−60)", ["line count"])]:
            with self.subTest(line=line):
                text = GOOD.replace("USER's read", f"USER's read; {line}")
                self.assertEqual(self.lint(text),
                                 [f"needs: copies {kind}" for kind in kinds])

    def test_prose_about_merging_is_not_state(self):
        for line in ["merges clean", "the branch is clean of TODOs",
                     "red-black trees", "1/2 of the work"]:
            with self.subTest(line=line):
                self.assertEqual(self.lint(GOOD.replace("USER's read", line)), [])

    def test_a_log_line_opening_with_mergeable_state_is_copied(self):
        text = GOOD.replace("resolved 19 review threads",
                            "`clean` against `main`, every check green")
        self.assertEqual(self.lint(text), ["2026-09-01: copies mergeable state"])

    def test_a_log_line_recording_a_change_may_name_state(self):
        for body in ["merged `main` (was `dirty` on `CHANGELOG.md`)",
                     "opened it, +52/−1, CI 7/7 green"]:
            with self.subTest(body=body):
                text = GOOD.replace("resolved 19 review threads", body)
                self.assertEqual(self.lint(text), [])

    def test_lint_walks_numbered_notes_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "WORK" / "lib").mkdir(parents=True)
            (root / "WORK" / "lib" / "12.md").write_text(GOOD)
            (root / "WORK" / "lib" / "13.md").write_text(GOOD)
            (root / "WORK" / "TEMPLATE.md").write_text("# not a note")
            self.assertEqual(work_notes.lint(root, work_notes.TEMPLATE),
                             ["WORK/lib/13.md: title names lib#12"])


class Touched(unittest.TestCase):
    """A touched item needs a note with a line from the turn."""

    def test_open_item_without_a_note(self):
        self.assertEqual(work_notes.touched_finding(item(1), None, "2026-09-01"),
                         "no note")

    def test_closed_item_without_a_note_is_fine(self):
        self.assertIsNone(work_notes.touched_finding(item(1, "closed"), None,
                                                     "2026-09-01"))

    def test_closed_item_with_a_note(self):
        self.assertEqual(work_notes.touched_finding(item(1, "closed"), GOOD,
                                                    "2026-09-01"),
                         "closed, note not deleted")

    def test_log_line_on_or_after_the_day(self):
        self.assertIsNone(work_notes.touched_finding(item(1), GOOD, "2026-09-01"))
        self.assertEqual(work_notes.touched_finding(item(1), GOOD, "2026-09-02"),
                         "no log line dated 2026-09-02 or later")

    def test_a_log_date_that_is_no_date_is_not_a_line_since(self):
        text = GOOD.replace("2026-09-01 🌙", "9999-99-99 🌙")
        self.assertEqual(work_notes.touched_finding(item(1), text, "2026-09-02"),
                         "no log line dated 2026-09-02 or later")

    def test_note_path_uses_the_repository_name(self):
        self.assertEqual(work_notes.note_path(pathlib.Path("/m"), "org/lib", 7),
                         pathlib.Path("/m/WORK/lib/7.md"))

    def test_the_day_pr_is_not_an_item(self):
        self.assertTrue(work_notes.day_pr(
            "someone/memory", item(5, title="2026-09-01", pull=True), SETUP))
        self.assertFalse(work_notes.day_pr(
            "someone/memory", item(5, title="2026-09-01"), SETUP))
        self.assertFalse(work_notes.day_pr(
            "org/lib", item(5, title="2026-09-01", pull=True), SETUP))

    def test_skeleton_lists_each_item(self):
        self.assertEqual(work_notes.skeleton([("org/lib", item(3, title="t"))]),
                         ["- org/lib#3 (t): "])

    def run_touched(self, search):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "WORK" / "lib").mkdir(parents=True)
            (root / "WORK" / "lib" / "3.md").write_text(
                GOOD.replace("lib#12", "lib#3"))
            out = io.StringIO()
            with mock.patch.object(work_notes, "search", search), \
                    contextlib.redirect_stdout(out):
                code = work_notes.touched(root, SETUP, "2026-09-01T00:00:00Z")
        return code, out.getvalue()

    def test_a_failed_read_is_incomplete_not_clean(self):
        def search(agent, repo, since):
            if repo == "org/docs":
                raise urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
            return []
        code, out = self.run_touched(search)
        self.assertEqual(code, 2)
        self.assertIn("org/docs: n/a (403)", out)
        self.assertNotIn("clean", out)
        self.assertIn("incomplete", out)

    def test_findings_and_skeleton(self):
        def search(agent, repo, since):
            self.assertEqual(agent, "someone-agents")
            return {"org/lib": [item(3), item(4)],
                    "someone/memory": [item(9, title="2026-09-01", pull=True)]
                    }.get(repo, [])
        code, out = self.run_touched(search)
        self.assertEqual(code, 1)
        self.assertIn("org/lib#4: no note (WORK/lib/4.md)", out)
        self.assertNotIn("org/lib#3:", out)
        self.assertIn("- org/lib#3 (a title): ", out)
        self.assertNotIn("someone/memory#9", out)

    def test_nothing_missing_is_clean(self):
        code, out = self.run_touched(lambda agent, repo, since: [])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("clean"))


class Main(unittest.TestCase):
    """What cannot be read is incomplete, never clean or a finding."""

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = work_notes.main(list(argv))
        return code, out.getvalue()

    def test_missing_or_partial_config_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "config.env"
            self.assertEqual(self.run_main("touched", "--since", "2026-09-01",
                                           "--config", str(path))[0], 2)
            path.write_text("AGENT=bot\n")
            code, out = self.run_main("touched", "--since", "2026-09-01",
                                      "--config", str(path))
        self.assertEqual(code, 2)
        self.assertIn("no WORK_REPOS, MEMORY_REPO, DESIRE_REPO", out)

    def test_lint_without_work_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self.run_main("lint", "--config",
                                      str(pathlib.Path(tmp) / "config.env"))
        self.assertEqual(code, 2)
        self.assertTrue(out.startswith("n/a (no WORK/"))

    def test_since_must_be_a_time(self):
        self.assertTrue(work_notes.SINCE.fullmatch("2026-09-01T08:00:00Z"))
        self.assertTrue(work_notes.SINCE.fullmatch("2026-09-01"))
        for since in ["2026-09-01 08:00", "yesterday", "2026-09-01Tnoon"]:
            with self.subTest(since=since), \
                    contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit):
                work_notes.main(["touched", "--since", since])


class Request(unittest.TestCase):
    """A GitHub read gives up on a stalled connection."""

    def test_a_timeout_is_passed(self):
        with mock.patch.object(work_notes.urllib.request, "urlopen",
                               side_effect=TimeoutError) as urlopen, \
                self.assertRaises(OSError):
            work_notes.request("https://example.invalid")
        self.assertEqual(urlopen.call_args.kwargs.get("timeout"), work_notes.TIMEOUT)


class RateLimit(unittest.TestCase):
    """A rate-limited answer is waited out, anything else is not."""

    def test_retry_after_wins(self):
        self.assertEqual(work_notes.rate_wait(
            403, {"Retry-After": "10"}, "secondary rate limit", 0), 11)

    def test_spent_primary_limit_waits_for_reset(self):
        self.assertEqual(work_notes.rate_wait(
            403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "30"},
            "API rate limit exceeded", 0), 30)

    def test_headers_alone_signal_a_rate_limit(self):
        self.assertEqual(work_notes.rate_wait(429, {"Retry-After": "5"}, "", 0), 6)
        self.assertEqual(work_notes.rate_wait(
            403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "30"}, "", 0), 30)

    def test_forbidden_is_not_a_rate_limit(self):
        self.assertIsNone(work_notes.rate_wait(403, {}, "Resource not accessible", 0))
        self.assertIsNone(work_notes.rate_wait(422, {}, "rate limit", 0))


if __name__ == "__main__":
    unittest.main()
