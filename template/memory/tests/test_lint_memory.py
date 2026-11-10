import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

SPEC = importlib.util.spec_from_file_location("lint_memory", Path(__file__).resolve().parents[1] / "scripts/lint_memory.py")
lint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lint)

NOTE = """# project#1 — an example

- **whose** ours · read 2026-01-01
- **does** documents the example
- **needs** nothing
- **touches** no other items
- **blocks** nothing

- **2026-01-01 Daylight** wrote the example
"""
SETUP = {"WORK_REPOS": ["owner/project", "owner/other"], "AGENT": "bot", "ADOPTED_PRS": {"owner/other": [4]}}


def item(number, *, author="human", updated="2026-01-01T12:00:00Z", pr=True):
    result = {"number": number, "user": {"login": author}, "updated_at": updated,
              "html_url": f"https://github.com/owner/project/issues/{number}"}
    if pr:
        result["pull_request"] = {}
    return result


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("WORK/project/1.md", NOTE)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def audit(self):
        audit = lint.Audit(self.root, SETUP)
        audit.local()
        return audit

    def test_template_is_clean(self):
        self.assertEqual(self.audit().findings, [])

    def test_work_template_is_not_a_numbered_item(self):
        self.write("WORK/TEMPLATE.md", "# The shape\n\n```markdown\n" + NOTE + "```\n")
        self.assertEqual(self.audit().findings, [])

    def test_configured_seed_passes_offline(self):
        seed = Path(__file__).resolve().parents[1]
        if not (seed / "WORK/TEMPLATE.md").exists():
            self.skipTest("live memory clone does not carry the template")
        audit = lint.Audit(seed, SETUP)
        audit.local()
        self.assertEqual(audit.findings, [])

    def test_board_limit_is_strict(self):
        self.write("README.md", "line\n" * 200)
        self.assertTrue(any("board-length" in f for f in self.audit().findings))

    def test_fields_empty_duplicate_and_live_state(self):
        self.write("WORK/project/1.md", NOTE.replace("- **needs** nothing", "- **needs**\n- **needs** nothing\n- **state** open"))
        findings = self.audit().findings
        self.assertTrue(any("empty-field" in f for f in findings))
        self.assertTrue(any("note-fields" in f for f in findings))

    def test_invalid_dates_log_order_and_limit(self):
        self.write("WORK/project/1.md", NOTE.replace("read 2026-01-01", "read 2026-02-30") + "- **2026-02-01 Evening** updated\n" * 6)
        findings = self.audit().findings
        for rule in ("read-date", "log-order", "note-log"):
            self.assertTrue(any(rule in f for f in findings), findings)

    def test_paths_and_unknown_repositories(self):
        self.write("WORK/unknown/02.md", NOTE)
        self.write("WORK/unknown/2.md", NOTE)
        findings = self.audit().findings
        for rule in ("note-path", "note-repo", "note-title"):
            self.assertTrue(any(rule in f for f in findings))

    def test_commonmark_links_anchors_images_and_code(self):
        self.write("docs/target.md", "# Hello, world!\n# Hello, world!\n")
        self.write("docs/source.md", """[one](target.md#hello-world)
[two][ref]

[ref]: target.md#hello-world-1
![image](missing.svg)
[bad](target.md#absent)
[encoded](hello%20world.md)
[escape](../../outside.md)
`[inline](ignored.md)`

```
[fenced](ignored.md)
```
""")
        self.write("docs/hello world.md", "hello")
        findings = self.audit().findings
        self.assertEqual(len(findings), 3, findings)
        self.assertFalse(any("ignored" in f for f in findings))

    def test_balanced_parentheses_in_bare_and_markdown_urls(self):
        url = "https://example.test/Foo_(bar)"
        for text in (url, "(" + url + ").", "[label](" + url + ")", "[label][ref]\n\n[ref]: " + url):
            self.assertEqual({target for _, target in lint.links(text)}, {url}, text)
        ipv6 = "http://[::1]/page"
        self.assertEqual({target for _, target in lint.links(ipv6)}, {ipv6})

    def test_bad_url_does_not_abort_other_checks(self):
        self.write("README.md", "http://[x\n[broken](missing.md)\n")
        findings = self.audit().findings
        self.assertTrue(any("invalid-link" in f for f in findings))
        self.assertTrue(any("missing.md" in f for f in findings))

    def test_diagnostics_preserve_source_order(self):
        self.write("README.md", "[second](b.md)\n\n[first](a.md)\n\n[second again](b.md)\n")
        findings = self.audit().findings
        self.assertEqual([f.split(":")[1] for f in findings], ["1", "3", "5"])
        self.assertIn("b.md", findings[0])

    def test_spaced_explicit_anchors_and_utf8_target_reads(self):
        self.write("docs/target.md", '# Café\n<a id = "intro"></a>\n<a name = "legacy"></a>\n')
        self.write("README.md", "[one](docs/target.md#intro)\n[two](docs/target.md#legacy)\n[three](docs/target.md#café)\n")
        read_text = Path.read_text
        def read(path, *args, **kwargs):
            self.assertEqual(kwargs.get("encoding"), "utf-8")
            return read_text(path, *args, **kwargs)
        with patch.object(Path, "read_text", read):
            self.assertEqual(self.audit().findings, [])

    def test_unreadable_note_keeps_findings_and_continues(self):
        self.write("config.env", "WORK_REPOS=owner/project\nAGENT=bot\n")
        self.write("docs/a.md", "[broken](missing-a.md)")
        self.write("docs/b.md", "placeholder")
        (self.root / "docs/b.md").write_bytes(b"\xff")
        self.write("docs/c.md", "[broken](missing-c.md)")
        with patch("sys.stdout", new_callable=io.StringIO) as output, patch("sys.stderr", new_callable=io.StringIO) as errors:
            self.assertEqual(lint.main(["--root", str(self.root)]), 2)
        self.assertIn("missing-a.md", output.getvalue())
        self.assertIn("missing-c.md", output.getvalue())
        self.assertIn("docs/b.md", errors.getvalue())

    def test_sync_missing_closed_stale_authored_adopted_and_cross_cites(self):
        self.write("WORK/project/1.md", NOTE + "\nother#3 https://github.com/owner/other/issues/5\n")
        self.write("WORK/project/2.md", NOTE.replace("project#1", "project#2"))
        self.write("WORK/project/6.md", NOTE.replace("project#1", "project#6"))
        audit = self.audit()
        audit.github(lambda repo, path: [item(1, updated="2026-01-02T00:00:00Z"), item(2), item(7, author="bot"), item(8, pr=False)]
                     if repo.endswith("project") else [item(3), item(4), item(5), item(99)])
        findings = "\n".join(audit.findings)
        for expected in ("stale-note", "closed-note", "project/7.md", "other/3.md", "other/4.md", "other/5.md"):
            self.assertIn(expected, findings)
        self.assertNotIn("project/8.md", findings)
        self.assertNotIn("other/99.md", findings)
        self.assertEqual(audit.incomplete, [])

    def test_legacy_read_date_still_checks_freshness(self):
        self.write("WORK/project/1.md", NOTE.replace("- **whose**", "- **state**"))
        audit = self.audit()
        audit.github(lambda repo, path: [item(1, updated="2026-01-02T00:00:00Z")])
        self.assertTrue(any("stale-note" in f for f in audit.findings))

    def test_ambiguous_repo_names_fail(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            lint.Audit(self.root, {**SETUP, "WORK_REPOS": ["first/project", "second/project"]})

    def test_unreadable_repo_is_not_closed_notes(self):
        audit = self.audit()
        audit.github(lambda *_: (_ for _ in ()).throw(URLError("denied")))
        self.assertEqual(len(audit.incomplete), 2)
        self.assertFalse(any("closed-note" in f for f in audit.findings))

    def test_unreadable_note_is_not_missing(self):
        self.write("WORK/project/1.md", "placeholder")
        (self.root / "WORK/project/1.md").write_bytes(b"\xff")
        audit = self.audit()
        audit.local()
        audit.github(lambda repo, path: [item(1, author="bot")] if repo == "owner/project" else [])
        self.assertFalse(any("missing-note" in f for f in audit.findings))

    def test_read_date_on_a_wrapped_line(self):
        for indent in ("  ", "\t", " "):
            self.write("WORK/project/1.md", NOTE.replace(" · read ", f"\n{indent}wrapped · read "))
            audit = self.audit()
            self.assertFalse(any("read-date" in f for f in audit.findings), (indent, audit.findings))

    def test_memory_repo_notes_are_allowed(self):
        self.write("WORK/memory/1.md", NOTE.replace("project#1", "memory#1"))
        audit = lint.Audit(self.root, {**SETUP, "MEMORY_REPO": "owner/memory"})
        audit.local()
        self.assertFalse(any("note-repo" in f for f in audit.findings), audit.findings)

    def test_external_broken_vs_unverifiable(self):
        for status, broken in ((404, True), (410, True), (403, False), (429, False), (503, False)):
            audit = self.audit()
            audit.urls = {"https://example.test": (Path("README.md"), 1)}
            def check(url):
                raise HTTPError(url, status, "test", {}, None)
            audit.external(check)
            self.assertEqual(bool(audit.findings), broken)
            self.assertEqual(bool(audit.incomplete), not broken)

    def test_offline_cli_never_uses_network_and_exit_codes(self):
        self.write("config.env", "WORK_REPOS=owner/project\nAGENT=bot\n")
        with patch.object(lint, "urlopen", side_effect=AssertionError("offline network")), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(lint.main(["--root", str(self.root)]), 0)
            self.write("README.md", "[broken](absent.md)")
            self.assertEqual(lint.main(["--root", str(self.root)]), 1)
            with patch.object(lint.GitHub, "get", side_effect=URLError("denied")), patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(lint.main(["--root", str(self.root), "--github"]), 2)


class NetworkTest(unittest.TestCase):
    def test_pagination_and_timeout(self):
        calls = []
        def response(request, timeout):
            calls.append((request.full_url, timeout))
            return io.StringIO(json.dumps([item(i) for i in range(100)] if len(calls) == 1 else [item(100)]))
        with patch.object(lint, "urlopen", side_effect=response):
            self.assertEqual(len(lint.GitHub(3).get("owner/project", "issues?state=open")), 101)
        self.assertIn("page=2", calls[-1][0])
        self.assertEqual(calls[0][1], 3)

    def test_api_token_is_not_forwarded_on_redirects(self):
        requests = []
        def response(request, timeout):
            requests.append(request)
            return io.StringIO("[]")
        with patch.dict("os.environ", {"GITHUB_TOKEN": "secret"}), patch.object(lint, "urlopen", side_effect=response):
            lint.GitHub(3).get("owner/project", "issues?state=open")
        self.assertEqual(requests[0].get_header("Authorization"), "Bearer secret")
        self.assertNotIn("Authorization", requests[0].headers)
        self.assertIn("Authorization", requests[0].unredirected_hdrs)

    def test_head_fallback_does_not_send_tokens(self):
        calls = []
        def response(request, timeout):
            calls.append(request)
            if request.get_method() == "HEAD":
                raise HTTPError(request.full_url, 405, "method", {}, None)
            return io.StringIO("")
        with patch.dict("os.environ", {"GITHUB_TOKEN": "secret"}), patch.object(lint, "urlopen", side_effect=response):
            lint.GitHub(3).check("https://example.test")
        self.assertEqual([r.get_method() for r in calls], ["HEAD", "GET"])
        self.assertTrue(all(not r.has_header("Authorization") for r in calls))


if __name__ == "__main__":
    unittest.main()
