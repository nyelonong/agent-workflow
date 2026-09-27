from __future__ import annotations

import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import html_review  # noqa: E402  (the reviewer lives in scripts/ and is not a package)
import task_review  # noqa: E402

CLIENT = ROOT / "scripts/task_review.py"
REVIEWER = ROOT / "scripts/html_review.py"
REVIEW_ID = "0123456789abcdef0123456789abcdef"


def review_request(root: str, **overrides) -> task_review.ReviewRequest:
    payload = {
        "version": "1",
        "review_id": REVIEW_ID,
        "criterion": "ship it",
        "repositories": [{"root": root}],
    }
    payload.update(overrides)
    return task_review.parse_request_json(json.dumps(payload))


def get(url: str, timeout: float = 5.0) -> tuple[int, bytes, dict[str, str]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def post(url: str, payload: object, timeout: float = 5.0) -> tuple[int, bytes]:
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


class ReviewCase(unittest.TestCase):
    """A temporary Git repository with one committed file and two changes."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        # macOS /tmp is a symlink and the client canonicalises roots.
        self.base = Path(os.path.realpath(self._tmp.name))
        self.root = self.base / "repo"
        (self.root / "other").mkdir(parents=True)
        (self.root / "a.py").write_text("print('one')\n", encoding="utf-8")
        (self.root / "other" / "b.txt").write_text("unchanged\n", encoding="utf-8")
        self.git("init", "-q", "-b", "main", ".")
        self.git("add", "-A")
        self.git(
            "-c", "user.name=Task Review Test",
            "-c", "user.email=test@example.com",
            "-c", "commit.gpgsign=false",
            "commit", "-q", "-m", "initial",
        )
        (self.root / "a.py").write_text("print('one')\nprint('two')\n", encoding="utf-8")
        (self.root / "untracked.txt").write_text("new file\n", encoding="utf-8")

    def git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull},
        )
        return completed.stdout

    @property
    def request(self) -> task_review.ReviewRequest:
        return review_request(str(self.root))

    def session(self, request: "task_review.ReviewRequest | None" = None, **kwargs) -> html_review.ReviewSession:
        """A served review the test can talk to directly; no browser, no network."""
        kwargs.setdefault("open_browser", False)
        session = html_review.start_review_server(
            self.request if request is None else request, **kwargs
        )
        self.addCleanup(session.close)
        return session

    def file(self, payload: dict, path: str) -> dict:
        for repository in payload["repositories"]:
            for item in repository["files"]:
                if item["path"] == path:
                    return item
        self.fail(f"{path} is not in the payload")


# ---------------------------------------------------------------------------
# the patch reader
# ---------------------------------------------------------------------------


class PatchParsingTests(unittest.TestCase):
    PATCH = (
        b"diff --git a/a.py b/a.py\n"
        b"index 1111111..2222222 100644\n"
        b"--- a/a.py\n"
        b"+++ b/a.py\n"
        b"@@ -1,4 +1,4 @@ def handler():\n"
        b" keep\n"
        b"-gone\n"
        b"+fresh\n"
        b" \n"
        b"\\ No newline at end of file\n"
    )

    def setUp(self) -> None:
        self.lines, self.added, self.removed, self.binary = html_review.parse_patch(self.PATCH)

    def test_splits_a_patch_into_typed_lines(self) -> None:
        self.assertEqual(
            ["meta", "meta", "meta", "meta", "meta", "context", "remove", "add", "context", "meta"],
            [line.type for line in self.lines],
        )

    def test_numbers_both_sides_of_the_diff(self) -> None:
        context, remove, add, blank = self.lines[5], self.lines[6], self.lines[7], self.lines[8]
        self.assertEqual((1, 1), (context.old_line, context.new_line))
        self.assertEqual((2, None), (remove.old_line, remove.new_line))
        self.assertEqual((None, 2), (add.old_line, add.new_line))
        self.assertEqual((3, 3), (blank.old_line, blank.new_line))
        self.assertEqual("", blank.text, "a blank context line carries no text of its own")

    def test_keeps_the_text_without_its_prefix(self) -> None:
        self.assertEqual("keep", self.lines[5].text)
        self.assertEqual("gone", self.lines[6].text)
        self.assertEqual("fresh", self.lines[7].text)

    def test_counts_additions_and_removals(self) -> None:
        self.assertEqual((1, 1), (self.added, self.removed))
        self.assertFalse(self.binary)

    def test_headers_have_no_position_to_comment_on(self) -> None:
        for line in self.lines:
            if line.type == "meta":
                self.assertIsNone(line.old_line)
                self.assertIsNone(line.new_line)
                self.assertFalse(line.selectable)
            else:
                self.assertTrue(line.selectable)

    def test_a_pure_addition_hunk_has_no_old_side(self) -> None:
        lines, added, removed, _ = html_review.parse_patch(
            b"diff --git a/n.txt b/n.txt\n--- /dev/null\n+++ b/n.txt\n@@ -0,0 +1,2 @@\n+one\n+two\n"
        )
        self.assertEqual((2, 0), (added, removed))
        self.assertEqual([(None, 1), (None, 2)], [(line.old_line, line.new_line) for line in lines[4:]])

    def test_a_deleted_file_still_numbers_its_old_lines(self) -> None:
        lines, added, removed, _ = html_review.parse_patch(
            b"diff --git a/gone.txt b/gone.txt\ndeleted file mode 100644\n"
            b"--- a/gone.txt\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-one\n-two\n"
        )
        self.assertEqual((0, 2), (added, removed))
        self.assertEqual([(1, None), (2, None)], [(line.old_line, line.new_line) for line in lines[5:]])

    def test_marks_a_binary_patch(self) -> None:
        lines, _, _, binary = html_review.parse_patch(
            b"diff --git a/logo.png b/logo.png\nindex 1111111..2222222 100644\n"
            b"Binary files a/logo.png and b/logo.png differ\n"
        )
        self.assertTrue(binary)
        self.assertEqual([], [line for line in lines if line.selectable])

    def test_counts_are_survived_by_a_rename_with_no_content_change(self) -> None:
        lines, added, removed, binary = html_review.parse_patch(
            b"diff --git a/old.txt b/new.txt\nsimilarity index 100%\nrename from old.txt\nrename to new.txt\n"
        )
        self.assertEqual((0, 0, False), (added, removed, binary))
        self.assertEqual([], [line for line in lines if line.selectable])


# ---------------------------------------------------------------------------
# the request, exactly as RDG validates it
# ---------------------------------------------------------------------------


class RequestValidationTests(ReviewCase):
    def run_reviewer(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REVIEWER), *args],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_rejects_what_rdg_rejects(self) -> None:
        root = str(self.root)
        cases = {
            "relative root": {"repositories": [{"root": "repo"}]},
            "parent traversal in root": {"repositories": [{"root": "/tmp/../etc"}]},
            "unknown protocol version": {"version": "2"},
            "whitespace review id": {"review_id": "   "},
            "whitespace criterion": {"criterion": "\t\n "},
            "no repositories": {"repositories": []},
            "duplicate roots": {"repositories": [{"root": root}, {"root": root}]},
            "empty scope list": {"repositories": [{"root": root, "paths": []}]},
            "scope with parent traversal": {"repositories": [{"root": root, "paths": ["src/../a.py"]}]},
            "absolute scope": {"repositories": [{"root": root, "paths": ["/a.py"]}]},
        }
        base = {"version": "1", "review_id": REVIEW_ID, "criterion": "ship it"}
        for label, override in cases.items():
            with self.subTest(case=label):
                payload = dict(base)
                payload.update(override)
                result = self.run_reviewer("--review", json.dumps(payload))
                self.assertEqual(html_review.EXIT_ERROR, result.returncode, result.stderr)
                self.assertEqual("", result.stdout, "a rejected request must print no result line")
                self.assertIn(html_review.PRODUCER, result.stderr)

    def test_rejects_a_request_that_is_not_json(self) -> None:
        result = self.run_reviewer("--review", "not json")
        self.assertEqual(html_review.EXIT_ERROR, result.returncode)
        self.assertIn(html_review.PRODUCER, result.stderr)

    def test_requires_a_request(self) -> None:
        result = self.run_reviewer()
        self.assertEqual(html_review.EXIT_ERROR, result.returncode)
        self.assertIn("--review", result.stderr)

    def test_reads_the_request_from_stdin_when_the_value_is_absent(self) -> None:
        payload = json.dumps({
            "version": "1", "review_id": REVIEW_ID, "criterion": " ",
            "repositories": [{"root": str(self.root)}],
        })
        result = self.run_reviewer("--review", stdin=payload)
        self.assertEqual(html_review.EXIT_ERROR, result.returncode)
        self.assertIn("criterion must not be empty", result.stderr)

    def test_fails_closed_when_a_repository_is_not_a_worktree(self) -> None:
        request = review_request(str(self.base / "nowhere"))
        with self.assertRaises(task_review.GitError):
            html_review.build_payload(request)


# ---------------------------------------------------------------------------
# the server
# ---------------------------------------------------------------------------


class ServerRouteTests(ReviewCase):
    def test_serves_the_page_with_a_locked_down_policy(self) -> None:
        session = self.session()
        status, body, headers = get(session.url)
        self.assertEqual(200, status)
        page = body.decode("utf-8")
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertIn("style-src 'unsafe-inline'", headers["Content-Security-Policy"])
        policy = headers["Content-Security-Policy"]
        # Same-origin vendored scripts are allowed now; nothing else is, and no
        # directive may be declared twice (the last one silently wins, which is
        # how an earlier policy ended up blocking the page's own script).
        self.assertIn("script-src 'self' 'unsafe-inline'", policy)
        for directive in ("default-src", "style-src", "script-src", "connect-src", "font-src"):
            self.assertEqual(1, policy.count(directive + " "), f"{directive} must be declared once")
        self.assertNotIn("http://", policy)
        self.assertNotIn("https://", policy)
        self.assertEqual("nosniff", headers["X-Content-Type-Options"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertIn(session.token, page, "the page needs its own token to reach its routes")
        self.assertNotRegex(page, r'<(script|link|img|iframe)[^>]+(src|href)="(https?:)?//')
        self.assertIn("font-src 'self'", headers["Content-Security-Policy"])
        self.assertNotIn("prefers-color-scheme: light", page, "the page is dark only")

    def test_every_route_is_behind_the_token(self) -> None:
        session = self.session()
        for path in ("/", f"/{session.token}x/", "/api/review", f"/wrong-token{self.base.name}/api/review"):
            with self.subTest(path=path):
                status, _, _ = get(f"{session.base_url}{path}")
                self.assertEqual(404, status)
        status, _ = post(f"{session.base_url}/api/decision", {"decision": "approve", "annotations": []})
        self.assertEqual(404, status, "a decision without the token must not be recorded")
        self.assertIsNone(session.result(timeout=0.5))

    def test_serves_the_bundled_code_font(self) -> None:
        # The code font ships with the reviewer and is served from the review's
        # own origin: no network, and no third party named in the CSP.
        session = self.session()
        for name, path in html_review.FONT_FILES.items():
            self.assertTrue(path.is_file(), f"{name} must ship with the reviewer")
        status, body, headers = get(f"{session.base_url}/{session.token}/font/jetbrains-mono-400.woff2")
        self.assertEqual(200, status)
        self.assertEqual("font/woff2", headers["Content-Type"])
        self.assertEqual(html_review.FONT_FILES["jetbrains-mono-400.woff2"].read_bytes()[:4], body[:4])
        for path in ("/font/jetbrains-mono-400.woff2", f"/wrong{session.token}/font/jetbrains-mono-400.woff2"):
            with self.subTest(path=path):
                status, _, _ = get(f"{session.base_url}{path}")
                self.assertEqual(404, status, "a font must not be served without the review token")
        status, _, _ = get(f"{session.base_url}/{session.token}/font/jetbrains-mono-400.woff2.map")
        self.assertEqual(404, status, "the font route serves bundled files only")

    def test_the_page_uses_the_bundled_font_and_nerd_glyphs(self) -> None:
        session = self.session()
        status, body, _ = get(session.url)
        page = body.decode("utf-8")
        self.assertIn('font-family:"JetBrains Mono"', page)
        self.assertIn('src:url("font/jetbrains-mono-400.woff2")', page)
        self.assertIn("--nerd:", page)
        self.assertIn("FILE_GLYPHS", page, "file icons come from the nerd glyph map")

    def test_serves_no_filesystem_and_no_directory_listing(self) -> None:
        session = self.session()
        for path in (f"/{session.token}/..", f"/{session.token}/../../etc/passwd", f"/{session.token}/scripts/"):
            with self.subTest(path=path):
                status, _, _ = get(f"{session.base_url}{path}")
                self.assertEqual(404, status)

    def test_answers_the_wrong_method(self) -> None:
        session = self.session()
        status, _ = post(f"{session.base_url}/{session.token}/api/review", {})
        self.assertEqual(405, status)

    def test_publishes_the_criterion_the_repositories_and_the_diff(self) -> None:
        session = self.session()
        status, body, headers = get(f"{session.url}api/review")
        self.assertEqual(200, status)
        self.assertIn("application/json", headers["Content-Type"])
        payload = json.loads(body)
        self.assertEqual("ship it", payload["criterion"])
        self.assertEqual(REVIEW_ID, payload["review_id"])
        self.assertEqual([str(self.root)], [item["root"] for item in payload["repositories"]])

        changed = self.file(payload, "a.py")
        self.assertEqual("modified", changed["status"])
        self.assertEqual((1, 0), (changed["added"], changed["removed"]))
        self.assertEqual(
            [("print('one')", 1, 1), ("print('two')", None, 2)],
            [(line["text"], line["old_line"], line["new_line"]) for line in changed["lines"] if line["type"] != "meta"],
        )

        added = self.file(payload, "untracked.txt")
        self.assertEqual("added", added["status"])
        self.assertEqual([("new file", None, 1)], [(line["text"], line["old_line"], line["new_line"]) for line in added["lines"] if line["type"] != "meta"])

    def test_reports_a_scope_and_a_deletion(self) -> None:
        self.git("rm", "-q", "other/b.txt")
        scoped = review_request(str(self.root), repositories=[{"root": str(self.root), "paths": ["other"]}])
        payload = html_review.build_payload(scoped)
        self.assertEqual([["other"]], [item["paths"] for item in payload["repositories"]])
        deleted = self.file(payload, "other/b.txt")
        self.assertEqual("deleted", deleted["status"])
        self.assertEqual((0, 1), (deleted["added"], deleted["removed"]))
        self.assertEqual([("unchanged", 1, None)], [(line["text"], line["old_line"], line["new_line"]) for line in deleted["lines"] if line["type"] != "meta"])

    def test_keeps_a_binary_file_uncommentable(self) -> None:
        (self.root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01\x02")
        payload = html_review.build_payload(self.request)
        binary = self.file(payload, "logo.png")
        self.assertTrue(binary["binary"])
        self.assertEqual([], [line for line in binary["lines"] if line["type"] != "meta"])

    def test_refuses_a_decision_the_client_would_reject(self) -> None:
        cases = {
            "unknown decision": {"decision": "merge", "annotations": []},
            "changes without feedback": {"decision": "request-changes", "annotations": []},
            "changes with only blank text": {"decision": "request-changes", "annotations": [{"text": " ", "target": {"scope": "review"}}]},
            "cancelled with a comment": {"decision": "cancelled", "annotations": [{"text": "nope", "target": {"scope": "review"}}]},
            "malformed target": {"decision": "approve", "annotations": [{"text": "x", "target": {"scope": "line"}}]},
            "a line that is not in the diff": {
                "decision": "approve",
                "annotations": [{"text": "x", "target": {"scope": "line", "repository": str(self.root), "path": "a.py", "side": "new", "start_line": 900, "end_line": 900}}],
            },
            "a file that is not in the review": {
                "decision": "approve",
                "annotations": [{"text": "x", "target": {"scope": "line", "repository": str(self.root), "path": "ghost.py", "side": "new", "start_line": 1, "end_line": 1}}],
            },
        }
        for label, payload in cases.items():
            with self.subTest(case=label):
                session = self.session()
                status, body = post(f"{session.url}api/decision", payload)
                self.assertEqual(400, status, body)
                self.assertIn("error", json.loads(body))
                self.assertIsNone(session.result(timeout=0.2), "a refused decision must leave the review open")

    def test_refuses_a_decision_that_is_not_json(self) -> None:
        session = self.session()
        status, _ = post(f"{session.url}api/decision", b"{not json")
        self.assertEqual(400, status)
        self.assertIsNone(session.result(timeout=0.2))

    def test_records_a_decision_once_and_stops(self) -> None:
        session = self.session()
        status, _ = post(f"{session.url}api/decision", {"decision": "cancelled", "annotations": []})
        self.assertEqual(204, status)
        result = session.result(timeout=5)
        self.assertEqual(
            {"version": "1", "review_id": REVIEW_ID, "decision": "cancelled", "annotations": []},
            result,
        )
        later = html_review.build_result(self.request, "approve", [])
        session.submit(later)
        self.assertEqual("cancelled", session.result(timeout=0)["decision"], "a decision is final")

    def test_carries_a_line_comment_with_both_of_its_ends(self) -> None:
        session = self.session()
        status, _ = post(
            f"{session.url}api/decision",
            {
                "decision": "request-changes",
                "annotations": [
                    {
                        "text": "guard this call",
                        "target": {
                            "scope": "line", "repository": str(self.root), "path": "a.py",
                            "side": "new", "start_line": 1, "end_line": 2,
                        },
                    }
                ],
            },
        )
        self.assertEqual(204, status)
        annotation = session.result(timeout=5)["annotations"][0]
        self.assertEqual(
            {
                "scope": "line", "repository": str(self.root), "path": "a.py",
                "side": "new", "start_line": 1, "end_line": 2,
            },
            annotation["target"],
        )
        task_review.validate_decision_semantics(session.result(timeout=0))


# ---------------------------------------------------------------------------
# decisions, without a browser in the way
# ---------------------------------------------------------------------------


class DecisionTests(ReviewCase):
    def approve_with(self, annotations: list) -> dict:
        session = self.session()
        status, body = post(f"{session.url}api/decision", {"decision": "approve", "annotations": annotations})
        self.assertEqual(204, status, body)
        result = session.result(timeout=5)
        self.assertIsNotNone(result)
        return result

    def test_approve_carries_every_comment_as_a_line_target(self) -> None:
        result = self.approve_with([
            {
                "text": "add a regression test",
                "target": {
                    "scope": "line", "repository": str(self.root), "path": "a.py",
                    "side": "new", "start_line": 2, "end_line": 2,
                },
            }
        ])
        self.assertEqual("approve", result["decision"])
        # The client must accept this result without complaint.
        task_review.validate_decision_semantics(result)
        self.assertTrue(task_review.is_annotation(result["annotations"][0]))

    def test_a_review_comment_is_a_scope_and_nothing_else(self) -> None:
        result = self.approve_with([{"text": "overall", "target": {"scope": "review", "path": "a.py"}}])
        self.assertEqual({"scope": "review"}, result["annotations"][0]["target"])

    def test_a_stale_page_cannot_point_at_a_line_it_never_saw(self) -> None:
        with self.assertRaises(html_review.DecisionError) as caught:
            html_review.parse_decision(
                {
                    "decision": "approve",
                    "annotations": [
                        {
                            "text": "x",
                            "target": {
                                "scope": "line", "repository": str(self.root), "path": "a.py",
                                "side": "old", "start_line": 2, "end_line": 2,
                            },
                        }
                    ],
                },
                self.request,
                html_review.line_index(html_review.build_payload(self.request)),
            )
        self.assertIn("a.py", str(caught.exception))

    def test_a_closed_window_is_a_cancelled_review(self) -> None:
        session = self.session()
        session.stop()
        result = session.result(timeout=5)
        self.assertEqual("cancelled", result["decision"])
        self.assertEqual([], result["annotations"])

    def test_the_page_reports_a_closed_window_with_the_beacon_the_page_sends(self) -> None:
        # What navigator.sendBeacon posts on pagehide, verbatim in shape.
        session = self.session()
        status, _ = post(f"{session.url}api/decision", json.dumps({"decision": "cancelled", "annotations": []}).encode())
        self.assertEqual(204, status)
        self.assertEqual("cancelled", session.result(timeout=5)["decision"])

    def test_browser_disabled_by_environment(self) -> None:
        for value, expected in [("", True), ("0", True), ("false", True), ("1", False), ("yes", False)]:
            with self.subTest(value=value):
                self.assertEqual(expected, html_review.browser_enabled({html_review.NO_BROWSER_ENV: value}))
        self.assertTrue(html_review.browser_enabled({}))


class Collector:
    """Captures the diagnostics a reviewer run writes for a human."""

    def __init__(self) -> None:
        self.text = ""

    def write(self, text: str) -> None:
        self.text += text

    def flush(self) -> None:
        pass


class ServeAndWaitTests(ReviewCase):
    def test_opens_the_page_when_a_browser_is_allowed(self) -> None:
        session = self.session(open_browser=True)
        session.stop()  # the decision is already in, so serve_and_wait returns at once
        with mock.patch.object(html_review.webbrowser, "open", return_value=True) as opened:
            result = session.serve_and_wait(stream=Collector())
        opened.assert_called_once()
        self.assertEqual(session.url, opened.call_args.args[0])
        self.assertEqual("cancelled", result["decision"])

    def test_does_not_open_a_page_when_a_browser_is_disabled(self) -> None:
        session = self.session()
        session.stop()
        with mock.patch.object(html_review.webbrowser, "open", return_value=True) as opened:
            session.serve_and_wait(stream=Collector())
        opened.assert_not_called()

    def test_prints_the_url_so_a_human_can_open_the_page_by_hand(self) -> None:
        session = self.session()
        session.stop()
        messages = Collector()
        session.serve_and_wait(stream=messages)
        self.assertIn(session.url, messages.text)

    def test_publishes_and_then_withdraws_the_url(self) -> None:
        published = self.base / "page-url"
        session = self.session()
        session.stop()
        session.serve_and_wait(stream=Collector(), url_file=str(published))
        self.assertFalse(published.exists(), "a token that no longer routes must not be left on disk")

    def test_a_browser_that_cannot_open_keeps_the_review_alive(self) -> None:
        session = self.session(open_browser=True)
        session.stop()
        messages = Collector()
        with mock.patch.object(html_review.webbrowser, "open", side_effect=OSError("no browser here")):
            result = session.serve_and_wait(stream=messages)
        self.assertEqual("cancelled", result["decision"])
        self.assertIn("no browser here", messages.text)


# ---------------------------------------------------------------------------
# the real client against the real reviewer
# ---------------------------------------------------------------------------


class GateIntegrationTests(ReviewCase):
    """The real gate runs the real reviewer; this test plays the human."""

    def env(self) -> dict[str, str]:
        dropped = (
            task_review.LAUNCHER_ENV,
            task_review.TIMEOUT_ENV,
            html_review.NO_BROWSER_ENV,
            html_review.URL_FILE_ENV,
        )
        base = {key: value for key, value in os.environ.items() if key not in dropped}
        base.update(
            {
                task_review.LAUNCHER_ENV: str(REVIEWER),
                task_review.TIMEOUT_ENV: "60",
                html_review.NO_BROWSER_ENV: "1",
                html_review.URL_FILE_ENV: str(self.base / "review-url"),
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        return base

    def start_review(self) -> subprocess.Popen:
        process = subprocess.Popen(
            [sys.executable, str(CLIENT), "review", "--criterion", "ship it", "--repo", str(self.root)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.env(),
        )
        self.addCleanup(self.kill, process)
        return process

    @staticmethod
    def kill(process: subprocess.Popen) -> None:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=30)

    def review_page(self, process: subprocess.Popen, timeout: float = 30.0) -> str:
        """The URL of the page the reviewer is actually serving."""
        published = self.base / "review-url"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail(f"the review ended before it served a page: exit {process.returncode}")
            try:
                url = published.read_text(encoding="utf-8").strip()
            except OSError:
                time.sleep(0.05)
                continue
            if url:
                return url
        self.fail("the reviewer never published a review page")

    def finish(self, process: subprocess.Popen) -> tuple[int, str]:
        stdout, _ = process.communicate(timeout=60)
        return process.returncode, stdout

    def review(self, decision: dict) -> tuple[int, dict]:
        """Runs the gate to completion with one decision, the way a human would."""
        process = self.start_review()
        status, body = post(f"{self.review_page(process)}api/decision", decision, timeout=30)
        self.assertEqual(204, status, body)
        code, stdout = self.finish(process)
        self.assertEqual(1, len(stdout.splitlines()), f"one result line, got {stdout!r}")
        return code, json.loads(stdout)

    def verify(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLIENT), "verify", "--repo", str(self.root)],
            capture_output=True,
            text=True,
            env=self.env(),
            timeout=60,
        )

    def test_an_approval_makes_the_gate_pass(self) -> None:
        code, result = self.review(
            {
                "decision": "approve",
                "annotations": [
                    {
                        "text": "the nit I am knowingly keeping",
                        "target": {
                            "scope": "line", "repository": str(self.root), "path": "a.py",
                            "side": "new", "start_line": 2, "end_line": 2,
                        },
                    }
                ],
            }
        )
        self.assertEqual(task_review.EXIT_OK, code)
        self.assertEqual("approve", result["decision"])
        self.assertEqual(1, len(result["annotations"]))
        verified = self.verify()
        self.assertEqual(task_review.EXIT_OK, verified.returncode, verified.stdout + verified.stderr)
        self.assertTrue(json.loads(verified.stdout)["approved"])

    def test_an_approval_without_comments_makes_the_gate_pass(self) -> None:
        code, result = self.review({"decision": "approve", "annotations": []})
        self.assertEqual(task_review.EXIT_OK, code)
        self.assertEqual([], result["annotations"])
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)

    def test_requested_changes_leaves_the_gate_failing(self) -> None:
        code, result = self.review(
            {
                "decision": "request-changes",
                "annotations": [{"text": "this needs a test", "target": {"scope": "review"}}],
            }
        )
        self.assertEqual(task_review.EXIT_NOT_APPROVED, code)
        self.assertEqual("request-changes", result["decision"])
        verified = self.verify()
        self.assertEqual(task_review.EXIT_NOT_APPROVED, verified.returncode, verified.stdout)
        self.assertFalse(json.loads(verified.stdout)["approved"])

    def test_open_line_comments_come_back_as_feedback(self) -> None:
        # An unresolved comment is the work the author still owes, so sending it
        # back must never be blocked and must never be dropped.
        code, result = self.review(
            {
                "decision": "request-changes",
                "annotations": [
                    {
                        "text": "rename this, it shadows the module name",
                        "target": {
                            "scope": "line",
                            "repository": str(self.root),
                            "path": "a.py",
                            "side": "new",
                            "start_line": 2,
                            "end_line": 2,
                        },
                    }
                ],
            }
        )
        self.assertEqual(task_review.EXIT_NOT_APPROVED, code)
        self.assertEqual("request-changes", result["decision"])
        self.assertEqual(1, len(result["annotations"]), "the open comment must reach the agent")
        self.assertEqual(2, result["annotations"][0]["target"]["start_line"])
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)

    def test_feedback_needs_at_least_one_comment(self) -> None:
        process = self.start_review()
        page = self.review_page(process)
        status, body = post(f"{page}api/decision", {"decision": "request-changes", "annotations": []}, timeout=30)
        self.assertEqual(400, status, body)
        self.assertIsNone(process.poll(), "a refused decision must leave the review open")
        status, _ = post(f"{page}api/decision", {"decision": "cancelled", "annotations": []}, timeout=30)
        self.assertEqual(204, status)
        self.finish(process)

    def test_a_closed_window_leaves_the_gate_failing(self) -> None:
        code, result = self.review({"decision": "cancelled", "annotations": []})
        self.assertEqual(task_review.EXIT_NOT_APPROVED, code)
        self.assertEqual("cancelled", result["decision"])
        self.assertEqual([], result["annotations"])
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)

    def test_a_change_under_the_reviewer_fails_the_gate_closed(self) -> None:
        # The gate re-fingerprints after an approval: a reviewer that approved a
        # tree that then moved must not leave an approval behind.
        process = self.start_review()
        page = self.review_page(process)
        (self.root / "a.py").write_text("print('one')\nprint('two')\nprint('three')\n", encoding="utf-8")
        status, body = post(
            f"{page}api/decision",
            {"decision": "approve", "annotations": []},
            timeout=30,
        )
        self.assertEqual(204, status, body)
        code, stdout = self.finish(process)
        self.assertEqual(task_review.EXIT_ERROR, code, stdout)
        self.assertEqual("", stdout, "a state that moved under the reviewer must print no result")
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)

    def test_a_refused_decision_leaves_the_review_open(self) -> None:
        process = self.start_review()
        page = self.review_page(process)
        status, _ = post(f"{page}api/decision", {"decision": "nope", "annotations": []}, timeout=30)
        self.assertEqual(400, status)
        self.assertIsNone(process.poll(), "a refused decision is not a decision")
        # The same page is still up, and a real decision still ends the review.
        status, _ = post(f"{page}api/decision", {"decision": "cancelled", "annotations": []}, timeout=30)
        self.assertEqual(204, status)
        code, stdout = self.finish(process)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, code)
        self.assertEqual("cancelled", json.loads(stdout)["decision"])

    def test_the_published_url_is_gone_when_the_review_ends(self) -> None:
        self.review({"decision": "cancelled", "annotations": []})
        self.assertFalse((self.base / "review-url").exists(), "a dead token must not be left on disk")

    @staticmethod
    def reviewer_children(client: subprocess.Popen) -> list[int]:
        """The reviewers this test's own client started.

        Scoped to the client's children on purpose: matching the binary name
        would also match a review running elsewhere on the machine, and the
        test would fail for a process it never started.
        """
        found = subprocess.run(
            ["pgrep", "-P", str(client.pid)], capture_output=True, text=True
        ).stdout.split()
        return [int(pid) for pid in found if pid.isdigit()]

    def wait_for_exit(self, pids: list[int], timeout: float = 20.0) -> list[int]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            alive = [pid for pid in pids if self.pid_alive(pid)]
            if not alive:
                return []
            time.sleep(0.2)
        return [pid for pid in pids if self.pid_alive(pid)]

    @staticmethod
    def pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError):
            return False
        return True

    def test_a_killed_client_does_not_leave_a_stale_reviewer(self) -> None:
        # SIGKILL cannot be handled, so the reviewer has to notice on its own.
        # Before the watchdog it survived, holding its port for good.
        process = self.start_review()
        self.review_page(process)
        children = self.reviewer_children(process)
        self.assertTrue(children, "the reviewer should be running while the page is up")
        process.kill()
        process.wait(timeout=30)
        self.assertEqual([], self.wait_for_exit(children), "an orphaned reviewer must not outlive its client")

    def test_the_reviewer_expires_on_its_own_lifetime(self) -> None:
        environment = self.env()
        environment[html_review.LIFETIME_ENV] = "1"
        environment[html_review.IDLE_ENV] = "1"
        completed = subprocess.run(
            [sys.executable, str(REVIEWER), "--review", self.request.to_json()],
            capture_output=True,
            text=True,
            env=environment,
            timeout=60,
        )
        self.assertEqual(html_review.EXIT_OK, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual("cancelled", result["decision"], "an expired review is never an approval")
        self.assertEqual([], result["annotations"])

    def test_junk_lifetime_values_fall_back_to_the_defaults(self) -> None:
        environment = self.env()
        environment[html_review.LIFETIME_ENV] = "not a number"
        environment[html_review.IDLE_ENV] = "-5"
        self.assertEqual(
            html_review.LIFETIME_SECONDS,
            html_review.positive_seconds(environment, html_review.LIFETIME_ENV, html_review.LIFETIME_SECONDS),
        )
        self.assertEqual(
            html_review.IDLE_SECONDS,
            html_review.positive_seconds(environment, html_review.IDLE_ENV, html_review.IDLE_SECONDS),
        )


class DocumentCase(ReviewCase):
    """A repository with a specification that a human reviews in the browser."""

    def setUp(self) -> None:
        super().setUp()
        self.doc = self.root / "docs/specs/2026-09-27-topic.md"
        self.doc.parent.mkdir(parents=True)
        self.doc.write_text(
            "# Topic\n\n## Problem\n\nSomething is **wrong** with `parse`.\n\n"
            "- one goal\n- [ ] an unchecked task\n- [x] a checked task\n",
            encoding="utf-8",
        )

    def document_request(self) -> task_review.DocumentRequest:
        return task_review.DocumentRequest(
            version=task_review.PROTOCOL_VERSION,
            review_id="doc-1",
            criterion="Fix the parser",
            path=str(self.doc),
        )

    def document_session(self, request: "task_review.DocumentRequest | None" = None, **kwargs):
        """A served document review the test can talk to directly."""
        kwargs.setdefault("open_browser", False)
        wanted = self.document_request() if request is None else request
        # start() matters: close() calls shutdown(), which blocks forever on a
        # server that never entered serve_forever.
        session = html_review.ReviewSession(
            wanted, html_review.build_document_payload(wanted), mode="document", **kwargs
        ).start()
        self.addCleanup(session.close)
        return session


class DocumentReviewTests(DocumentCase):
    def test_renders_one_row_per_line_of_the_document(self) -> None:
        session = self.document_session()
        source = self.doc.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(source), len(session.payload["rows"]))
        for index, row in enumerate(session.payload["rows"]):
            self.assertEqual(index + 1, row["n"], "row n must be source line n")
        status, body, _ = get(f"{session.url}api/doc")
        self.assertEqual(200, status)
        self.assertEqual(session.payload["review_id"], json.loads(body)["review_id"])

    def test_inline_markup_is_rendered_and_source_html_is_escaped(self) -> None:
        self.doc.write_text("# T\n\n**bold** and <script>x</script>\n", encoding="utf-8")
        session = self.document_session()
        rendered = " ".join(row["html"] for row in session.payload["rows"])
        self.assertIn("<b>bold</b>", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_a_line_comment_comes_back_anchored_to_the_document(self) -> None:
        session = self.document_session()
        status, body = post(
            f"{session.url}api/doc-decision",
            {
                "decision": "request-changes",
                "annotations": [
                    {
                        "text": "name the failure mode",
                        "target": {"scope": "line", "path": str(self.doc), "start_line": 5, "end_line": 5},
                    }
                ],
            },
        )
        self.assertEqual(204, status, body)
        result = session.result(timeout=5)
        self.assertIsNotNone(result)
        target = result["annotations"][0]["target"]
        self.assertEqual(5, target["start_line"])
        self.assertNotIn("repository", target, "a document has no repository")
        self.assertNotIn("side", target, "a document has no old side")

    def test_a_comment_cannot_name_a_line_the_document_does_not_have(self) -> None:
        session = self.document_session()
        status, body = post(
            f"{session.url}api/doc-decision",
            {
                "decision": "request-changes",
                "annotations": [
                    {
                        "text": "invented",
                        "target": {"scope": "line", "path": str(self.doc), "start_line": 999, "end_line": 999},
                    }
                ],
            },
        )
        self.assertEqual(400, status)
        self.assertIn("999", json.loads(body)["error"])
        self.assertIsNone(session.result(timeout=0.3), "a refused decision must leave the review open")

    def test_a_diff_shaped_comment_is_refused(self) -> None:
        session = self.document_session()
        status, _ = post(
            f"{session.url}api/doc-decision",
            {
                "decision": "request-changes",
                "annotations": [
                    {
                        "text": "wrong shape",
                        "target": {
                            "scope": "line",
                            "repository": str(self.root),
                            "path": "a.py",
                            "side": "new",
                            "start_line": 1,
                            "end_line": 1,
                        },
                    }
                ],
            },
        )
        self.assertEqual(400, status, "a document review must not accept a diff annotation")

    def test_feedback_without_a_comment_is_refused(self) -> None:
        session = self.document_session()
        status, _ = post(f"{session.url}api/doc-decision", {"decision": "request-changes", "annotations": []})
        self.assertEqual(400, status)
        self.assertIsNone(session.result(timeout=0.2))

    def test_the_document_routes_are_behind_the_token(self) -> None:
        session = self.document_session()
        for path in ("/api/doc", "/api/doc-decision"):
            with self.subTest(path=path):
                status, _, _ = get(f"{session.base_url}{path}")
                self.assertEqual(404, status)
                self.assertEqual(
                    404,
                    post(f"{session.base_url}{path}", {"decision": "cancelled", "annotations": []})[0],
                )

    def test_the_document_page_carries_no_external_resource(self) -> None:
        session = self.document_session()
        status, body, headers = get(session.url)
        self.assertEqual(200, status)
        page = body.decode("utf-8")
        self.assertIn('"mode":"document"', page, "the page must know it is reviewing a document")
        self.assertNotRegex(page, r'<(script|link|img|iframe)[^>]+(src|href)="(https?:)?//')
        self.assertIn("font-src 'self'", headers["Content-Security-Policy"])


class DocumentRequestValidationTests(DocumentCase):
    def run_reviewer(self, *args: str, env: "dict[str, str] | None" = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REVIEWER), *args],
            capture_output=True,
            text=True,
            env={**os.environ, html_review.NO_BROWSER_ENV: "1", "GIT_CONFIG_GLOBAL": os.devnull, **(env or {})},
            timeout=60,
        )

    def test_accepts_a_well_formed_document_request(self) -> None:
        # A bounded lifetime, so an unattended run withdraws instead of waiting
        # for a decision nobody is there to make.
        completed = self.run_reviewer(
            "--review-doc", self.document_request().to_json(), env={html_review.LIFETIME_ENV: "1"}
        )
        self.assertEqual(html_review.EXIT_OK, completed.returncode, completed.stderr)
        self.assertEqual("cancelled", json.loads(completed.stdout)["decision"])

    def test_rejects_malformed_document_requests(self) -> None:
        version = task_review.PROTOCOL_VERSION
        path = str(self.doc)
        bad_requests = [
            "not json",
            json.dumps({"review_id": "d", "criterion": "c", "path": path}),
            json.dumps({"version": "2", "review_id": "d", "criterion": "c", "path": path}),
            json.dumps({"version": version, "review_id": " ", "criterion": "c", "path": path}),
            json.dumps({"version": version, "review_id": "d", "criterion": "  ", "path": path}),
            json.dumps({"version": version, "review_id": "d", "criterion": "c"}),
            json.dumps({"version": version, "review_id": "d", "criterion": "c", "path": str(self.root / "missing.md")}),
        ]
        for request in bad_requests:
            with self.subTest(request=request[:48]):
                completed = self.run_reviewer("--review-doc", request)
                self.assertEqual(html_review.EXIT_ERROR, completed.returncode)
                self.assertEqual("", completed.stdout)
                self.assertTrue(completed.stderr.strip(), "a refusal must say why")

    def test_neither_flag_is_a_usage_error(self) -> None:
        completed = self.run_reviewer()
        self.assertEqual(html_review.EXIT_ERROR, completed.returncode)
        self.assertIn("required", completed.stderr)


if __name__ == "__main__":
    unittest.main()


class DocumentBlockRangeTests(DocumentCase):
    """A block renders once but spans several lines, so every line of it counts."""

    PARAGRAPH = (
        "# Title\n"
        "\n"
        "first line of the paragraph\n"
        "second line of the paragraph\n"
        "third line of the paragraph\n"
        "\n"
        "## Design\n"
        "\n"
        "a second paragraph\n"
    )

    def setUp(self) -> None:
        super().setUp()
        self.doc.write_text(self.PARAGRAPH, encoding="utf-8")

    def paragraph_range(self) -> tuple[int, int]:
        session = self.document_session()
        block = next(b for b in session.payload["blocks"] if b["kind"] == "text")
        return block["start"], block["end"]

    def test_the_payload_carries_blocks_that_tile_the_document(self) -> None:
        session = self.document_session()
        covered: list[int] = []
        for block in session.payload["blocks"]:
            covered.extend(range(block["start"], block["end"] + 1))
        self.assertEqual(list(range(1, len(self.PARAGRAPH.splitlines()) + 1)), covered)

    def test_a_comment_on_any_line_of_a_paragraph_is_accepted(self) -> None:
        start, end = self.paragraph_range()
        self.assertEqual(3, start)
        self.assertEqual(5, end)
        for line in (start, (start + end) // 2, end):
            with self.subTest(line=line):
                session = self.document_session()
                status, body = post(
                    f"{session.url}api/doc-decision",
                    {
                        "decision": "request-changes",
                        "annotations": [
                            {
                                "text": f"comment on line {line}",
                                "target": {
                                    "scope": "line",
                                    "path": str(self.doc),
                                    "start_line": line,
                                    "end_line": line,
                                },
                            }
                        ],
                    },
                )
                self.assertEqual(204, status, body)
                target = session.result(timeout=5)["annotations"][0]["target"]
                self.assertEqual(line, target["start_line"], "the range must survive the round trip")

    def test_a_line_no_block_covers_is_still_refused(self) -> None:
        session = self.document_session()
        status, body = post(
            f"{session.url}api/doc-decision",
            {
                "decision": "request-changes",
                "annotations": [
                    {
                        "text": "invented",
                        "target": {
                            "scope": "line",
                            "path": str(self.doc),
                            "start_line": 999,
                            "end_line": 999,
                        },
                    }
                ],
            },
        )
        self.assertEqual(400, status)
        self.assertIn("999", json.loads(body)["error"])
        self.assertIsNone(session.result(timeout=0.3))


class CodeBlockLanguageTests(DocumentCase):
    """The page tokenizes; the server only records which language a fence claims."""

    def fenced(self, body: str, language: str = "python") -> str:
        self.doc.write_text(f"# T\n\n```{language}\n{body}\n```\n\nAfter.\n", encoding="utf-8")
        return self.document_session()

    def test_the_fence_language_reaches_the_block(self) -> None:
        session = self.fenced("x = 1  # a count")
        block = next(b for b in session.payload["blocks"] if b["kind"] == "code")
        self.assertEqual("python", block["language"])
        self.assertIn("x = 1  # a count", block["source"])

    def test_an_unknown_language_is_passed_through_not_guessed(self) -> None:
        session = self.fenced("value = 2", language="brainfuck")
        block = next(b for b in session.payload["blocks"] if b["kind"] == "code")
        self.assertEqual("brainfuck", block["language"], "the engine decides what it knows, not the server")

    def test_a_bare_fence_claims_no_language(self) -> None:
        self.doc.write_text("# T\n\n```\nplain\n```\n", encoding="utf-8")
        session = self.document_session()
        block = next(b for b in session.payload["blocks"] if b["kind"] == "code")
        self.assertEqual("", block["language"])

    def test_source_html_in_a_code_block_is_still_escaped(self) -> None:
        session = self.fenced("x = '<script>alert(1)</script>'")
        block = next(b for b in session.payload["blocks"] if b["kind"] == "code")
        self.assertNotIn("<script>", block["html"])
        self.assertIn("&lt;script&gt;", block["html"])

    def test_prose_around_a_code_block_is_untouched(self) -> None:
        session = self.fenced("value = 2")
        kinds = [b["kind"] for b in session.payload["blocks"]]
        self.assertEqual(["heading", "blank", "code", "blank", "text"], kinds)
        self.assertNotIn("language", next(b for b in session.payload["blocks"] if b["kind"] == "text"))


class PageSurfaceTests(ReviewCase):
    """The page is one inline script, and nothing in CI was reading it.

    An edit once removed `say` and the render path, and every test still passed
    because they all assert on markup and HTTP, never on the script. These
    tests read the script the page actually serves.
    """

    def page_script(self) -> str:
        session = self.session()
        status, body, _ = get(session.url)
        self.assertEqual(200, status)
        page = body.decode("utf-8")
        start = page.index('<script>\n"use strict";')
        end = page.index("</script>", start)
        return page[start:end]

    def test_every_helper_the_page_needs_is_defined(self) -> None:
        script = self.page_script()
        for name in (
            "say", "unresolvedThreads", "resolvedThreads", "reviewText", "sideNumber",
            "sendDecision", "render", "renderFiles", "renderDiff", "makeRow",
            "visibleFiles", "renderDocument", "renderBlock", "renderOutline",
            "trackOutline", "jumpToRange", "onDocumentPress", "onRowPress",
            "paintSelection", "markThreadedRows", "markDocumentThreadedRows",
            "selectionTarget", "showComposer", "hideComposer", "refreshThreads",
            "saveComment", "openDialog", "closeDialog", "approve", "confirmApprove",
            "requestChanges", "returnToPlanning", "cancelReview", "jumpToThread",
            "threadLocation", "renderThreads", "renderFooter", "cycleThread",
            "stepFile", "loadReview",
        ):
            with self.subTest(name=name):
                self.assertRegex(script, r"(?:function|async function) %s\(" % re.escape(name))

    def test_no_helper_is_defined_twice(self) -> None:
        # A shadowed definition silently wins and is how the document-aware
        # selection path was lost once.
        script = self.page_script()
        names = re.findall(r"(?:function|async function)\s+([A-Za-z_$][\w$]*)\s*\(", script)
        duplicates = {name for name in names if names.count(name) > 1}
        self.assertEqual(set(), duplicates, "these page functions are defined more than once")

    def test_the_page_reaches_the_areas_the_markup_declares(self) -> None:
        session = self.session()
        status, body, _ = get(session.url)
        page = body.decode("utf-8")
        script = self.page_script()
        referenced = set(re.findall(r'\bel\("([\w-]+)"\)', script))
        declared = set(re.findall(r'id="([\w-]+)"', page))
        self.assertEqual(set(), referenced - declared, "the script reaches ids the page does not declare")

    def test_the_boot_config_names_the_endpoints_the_routes_serve(self) -> None:
        session = self.session()
        status, body, _ = get(session.url)
        page = body.decode("utf-8")
        for key in ('"reviewUrl":"api/review"', '"decisionUrl":"api/decision"'):
            self.assertIn(key, page)
        self.assertNotIn("api/doc", page, "a diff page must not point at the document routes")

    def test_the_page_never_shadows_a_vendored_global(self) -> None:
        # highlight.js declares `hljs` and markdown-it declares `markdownit` at
        # global scope. A `const` of the same name in the inline script is a
        # SyntaxError that stops the whole page from rendering.
        script = self.page_script()
        for name in ("hljs", "markdownit"):
            with self.subTest(name=name):
                self.assertNotRegex(script, r"(?:const|let|var)\s+%s\b" % name)

    def test_the_page_carries_no_stray_control_characters(self) -> None:
        # The page is a non-raw Python string, so a backslash written for the
        # browser (\b, \s, \n inside a regex) is eaten by Python and arrives as a
        # control character. Four separate bugs came from this; catch them all.
        session = self.session()
        status, body, _ = get(session.url)
        self.assertEqual(200, status)
        text = body.decode("utf-8")
        strays = {
            f"U+{ord(character):04X}"
            for character in text
            if ord(character) < 32 and character not in "\n\t"
        }
        self.assertEqual(set(), strays, "the page contains control characters from a mangled escape")

    def test_the_page_declares_no_top_level_binding_twice(self) -> None:
        # A repeated `const` is a SyntaxError that stops the whole page, and it
        # has already happened twice here. Function names are checked above;
        # this covers the same rule for top-level bindings.
        script = self.page_script()
        import re as _re

        names = _re.findall(r"(?m)^(?:const|let)\s+([A-Za-z_$][\w$]*)", script)
        duplicates = {name for name in names if names.count(name) > 1}
        self.assertEqual(set(), duplicates, "a top-level binding is declared twice")
