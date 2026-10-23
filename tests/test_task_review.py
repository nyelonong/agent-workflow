from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import selectors
import signal
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import task_review  # noqa: E402  (the client lives in scripts/ and is not a package)

CLIENT = ROOT / "scripts/task_review.py"

APPROVE = '{"version":"1","review_id":"__REVIEW_ID__","decision":"approve","annotations":[]}'
REJECT = (
    '{"version":"1","review_id":"__REVIEW_ID__","decision":"request-changes",'
    '"annotations":[{"text":"needs work","target":{"scope":"review"}}]}'
)

# Stub launcher: echoes a caller-chosen result document. It never touches RDG and
# never reaches the network, so the whole suite is hermetic.
STUB_LAUNCHER = r'''#!/usr/bin/env python3
import json
import os
import sys

assert sys.argv[1] == "--review", "the client must pass --review"
request = json.loads(sys.argv[2])
template = os.environ["STUB_RESULT"]
if os.environ.get("STUB_SUBSTITUTE", "1") == "1":
    template = template.replace("__REVIEW_ID__", request["review_id"])
mode = os.environ.get("STUB_MODE", "result")
if mode == "mutate":
    with open(os.environ["STUB_MUTATE"], "a", encoding="utf-8") as handle:
        handle.write("\nappended while the human was deciding\n")
if mode == "garbage":
    sys.stdout.write("rdg: this is not json\n")
    sys.exit(0)
if mode == "fail":
    sys.stderr.write("rdg: repository is not open or is not a Git worktree\n")
    sys.exit(1)
sys.stdout.write(template + "\n")
'''


class ReviewCase(unittest.TestCase):
    """A temporary Git repository plus a stub launcher standing in for RDG."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        # macOS /tmp is a symlink; the client canonicalises roots, so canonicalise
        # here too and keep expected paths comparable.
        self.base = Path(os.path.realpath(self._tmp.name))
        self.launcher = self.base / "fake-rdg"
        self.launcher.write_text(STUB_LAUNCHER, encoding="utf-8")
        self.launcher.chmod(0o755)
        self.root = self.make_repo("repo")
        self.write("a.py", "print('two')\n")
        self.write("other/b.txt", "changed\n")
        self.write("untracked.txt", "new file\n")

    # -- helpers ---------------------------------------------------------

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def make_repo(self, name: str) -> Path:
        """Creates a sibling repository with one commit and one uncommitted change."""
        root = self.base / name
        (root / "other").mkdir(parents=True)
        (root / "a.py").write_text("print('one')\n", encoding="utf-8")
        (root / "other" / "b.txt").write_text("unchanged\n", encoding="utf-8")
        self.git_at(root, "init", "-q", "-b", "main", ".")
        self.git_at(root, "add", "-A")
        self.git_at(
            root,
            "-c", "user.name=Task Review Test",
            "-c", "user.email=test@example.com",
            "-c", "commit.gpgsign=false",
            "commit", "-q", "-m", "initial",
        )
        return root

    def git_at(self, root: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout

    def git(self, *args: str) -> str:
        return self.git_at(self.root, *args)

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git(
            "-c", "user.name=Task Review Test",
            "-c", "user.email=test@example.com",
            "-c", "commit.gpgsign=false",
            "commit", "-q", "-m", message,
        )


    def env(self, **extra: str) -> dict[str, str]:
        base = {
            key: value
            for key, value in os.environ.items()
            if key not in (task_review.LAUNCHER_ENV, task_review.TIMEOUT_ENV)
        }
        base.update(
            {
                task_review.LAUNCHER_ENV: str(self.launcher),
                task_review.TIMEOUT_ENV: "60",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
                "STUB_RESULT": APPROVE,
            }
        )
        base.update(extra)
        return base

    def run_client(self, *args: str, cwd: "Path | None" = None, **env_extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLIENT), *args],
            capture_output=True,
            text=True,
            env=self.env(**env_extra),
            cwd=None if cwd is None else str(cwd),
        )

    def review(self, *args: str, **env_extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_client("review", "--criterion", "ship it", "--repo", str(self.root), *args, **env_extra)

    def verify(self, *args: str, **env_extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_client("verify", "--repo", str(self.root), *args, **env_extra)

    def entries(self) -> list[dict]:
        return task_review.read_entries(str(self.root / ".git" / task_review.LEDGER_NAME))

    def states(self) -> list[str]:
        return [entry.get("state") for entry in self.entries()]

    def assertSingleJsonLine(self, result: subprocess.CompletedProcess[str]) -> dict:
        """stdout must be exactly one JSON object on one line, and parse cleanly."""
        self.assertTrue(result.stdout.endswith("\n"), f"stdout must end with a newline: {result.stdout!r}")
        lines = result.stdout.splitlines()
        self.assertEqual(1, len(lines), f"stdout must be a single line: {result.stdout!r}")
        payload = json.loads(lines[0])
        self.assertIsInstance(payload, dict)
        return payload
    @contextlib.contextmanager
    def captured(self):
        """Captures the in-process client's stdout and stderr."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            yield out, err

    def assertNoApproval(self, result: subprocess.CompletedProcess[str]) -> None:
        """Every failure path must leave the newest entry unapproved and empty stdout."""
        self.assertEqual(task_review.EXIT_ERROR, result.returncode, result.stderr)
        self.assertEqual("", result.stdout, "a failing review must not print an approval")
        self.assertNotIn("approved", self.states()[-1:], f"an approval was recorded: {self.entries()}")
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)


class RequestValidationTests(ReviewCase):
    def test_rejects_invalid_requests(self) -> None:
        root = str(self.root)
        cases = {
            "relative root": {"repositories": [{"root": "repo"}]},
            "parent traversal in root": {"repositories": [{"root": "/tmp/../etc"}]},
            "unknown protocol version": {"version": "2"},
            "empty review id": {"review_id": ""},
            "empty criterion": {"criterion": ""},
            "no repositories": {"repositories": []},
            "repositories not a list": {"repositories": {}},
            "duplicate roots": {"repositories": [{"root": root}, {"root": root}]},
            "empty scope list": {"repositories": [{"root": root, "paths": []}]},
            "scope with parent traversal": {"repositories": [{"root": root, "paths": ["src/../a.py"]}]},
            "scope with current dir": {"repositories": [{"root": root, "paths": ["./a.py"]}]},
            "absolute scope": {"repositories": [{"root": root, "paths": ["/a.py"]}]},
            "unnormalised scope": {"repositories": [{"root": root, "paths": ["src//a.py"]}]},
            "scope with trailing slash": {"repositories": [{"root": root, "paths": ["src/"]}]},
            "repository not an object": {"repositories": [root]},
            "unknown repository key": {"repositories": [{"root": root, "depth": 2}]},
        }
        base = {"version": "1", "review_id": "r1", "criterion": "ship it"}
        for label, override in cases.items():
            with self.subTest(case=label):
                payload = dict(base)
                payload.update(override)
                result = self.run_client("review", "--json", json.dumps(payload))
                self.assertNoApproval(result)
                self.assertIn("task_review:", result.stderr)

    def test_rejects_non_json_request(self) -> None:
        self.assertNoApproval(self.run_client("review", "--json", "{not json"))

    def test_rejects_non_worktree_root(self) -> None:
        plain = Path(self.root).parent / "plain"
        plain.mkdir()
        result = self.run_client("review", "--criterion", "x", "--repo", str(plain))
        self.assertNoApproval(result)
        self.assertIn("worktree", result.stderr)

    def test_usage_errors(self) -> None:
        both = ["--repo", str(self.root), "--repo", str(self.root)]
        cases = {
            "paths with two repos": ("review", "--criterion", "x", *both, "--paths", "a.py"),
            "json with criterion": ("review", "--criterion", "x", "--json", "{}"),
            "json with repo": ("review", "--json", "{}", "--repo", str(self.root)),
            "no subcommand": (),
        }
        for label, argv in cases.items():
            with self.subTest(case=label):
                result = self.run_client(*argv)
                self.assertEqual(task_review.EXIT_ERROR, result.returncode, result.stderr)
                self.assertEqual("", result.stdout)
        self.assertNoApproval(self.run_client("consume"))

    def test_canonicalises_symlinked_root(self) -> None:
        # RDG matches repositories by canonical path, so a symlinked root must be
        # resolved before it is sent; otherwise the launcher rejects the request.
        link = Path(self.root).parent / "link"
        link.symlink_to(self.root)
        result = self.run_client("status", "--repo", str(link))
        self.assertEqual(task_review.EXIT_NOT_APPROVED, result.returncode, result.stderr)
        self.assertEqual(str(self.root), self.assertSingleJsonLine(result)["repositories"][0]["root"])


class FingerprintTests(ReviewCase):
    def repositories(self, paths=None):
        return [task_review.Repository(root=str(self.root), paths=paths)]

    def test_fingerprint_is_stable_for_an_unchanged_tree(self) -> None:
        first = task_review.collect_snapshot(self.repositories())
        second = task_review.collect_snapshot(self.repositories())
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(64, len(first.fingerprint))

    def test_fingerprint_changes_with_content(self) -> None:
        before = task_review.collect_snapshot(self.repositories()).fingerprint
        self.write("a.py", "print('three')\n")
        self.assertNotEqual(before, task_review.collect_snapshot(self.repositories()).fingerprint)

    def test_fingerprint_changes_with_an_untracked_file(self) -> None:
        before = task_review.collect_snapshot(self.repositories()).fingerprint
        self.write("untracked.txt", "different content\n")
        self.assertNotEqual(before, task_review.collect_snapshot(self.repositories()).fingerprint)

    def test_fingerprint_changes_with_a_binary_untracked_file(self) -> None:
        before = task_review.collect_snapshot(self.repositories()).fingerprint
        (self.root / "blob.bin").write_bytes(b"\x00\x01\x02binary\x00")
        after_first = task_review.collect_snapshot(self.repositories()).fingerprint
        self.assertNotEqual(before, after_first)
        (self.root / "blob.bin").write_bytes(b"\x00\x01\x02different\x00")
        self.assertNotEqual(after_first, task_review.collect_snapshot(self.repositories()).fingerprint)

    def test_fingerprint_changes_with_a_symlink_target(self) -> None:
        link = self.root / "link"
        link.symlink_to("a.py")
        before = task_review.collect_snapshot(self.repositories()).fingerprint
        link.unlink()
        link.symlink_to("other/b.txt")
        self.assertNotEqual(before, task_review.collect_snapshot(self.repositories()).fingerprint)

    def test_fingerprint_changes_with_a_rename(self) -> None:
        before = task_review.collect_snapshot(self.repositories()).fingerprint
        (self.root / "a.py").rename(self.root / "renamed.py")
        self.assertNotEqual(before, task_review.collect_snapshot(self.repositories()).fingerprint)

    def test_fingerprint_changes_with_a_new_baseline(self) -> None:
        before = task_review.collect_snapshot(self.repositories()).fingerprint
        self.commit("second")
        after = task_review.collect_snapshot(self.repositories())
        self.assertNotEqual(before, after.fingerprint, "the baseline is part of the fingerprint")
        self.assertEqual([], list(after.repositories[0].files))

    def test_fingerprint_uses_the_empty_tree_for_an_unborn_repository(self) -> None:
        empty = Path(os.path.realpath(self._tmp.name)) / "unborn"
        (empty / "src").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(empty)], check=True, capture_output=True)
        self.assertEqual(
            task_review.EMPTY_TREE,
            task_review.collect_repository(task_review.Repository(root=str(empty))).baseline,
        )
        (empty / "src" / "a.py").write_text("x\n", encoding="utf-8")
        self.assertNotEqual("", task_review.collect_snapshot([task_review.Repository(root=str(empty))]).fingerprint)

    def test_scope_limits_the_snapshot(self) -> None:
        scoped = self.repositories(["a.py"])
        paths = [file.path for file in task_review.collect_snapshot(scoped).repositories[0].files]
        self.assertEqual(["a.py"], paths)
        every = [file.path for file in task_review.collect_snapshot(self.repositories()).repositories[0].files]
        self.assertEqual(["a.py", "other/b.txt", "untracked.txt"], every)

    def test_scope_matches_a_directory_prefix_only(self) -> None:
        files = task_review.collect_snapshot(self.repositories(["other"])).repositories[0].files
        self.assertEqual(["other/b.txt"], [file.path for file in files])


class ApprovalFlowTests(ReviewCase):
    def test_approve_records_a_verifiable_approval(self) -> None:
        result = self.review()
        payload = self.assertSingleJsonLine(result)
        self.assertEqual(task_review.EXIT_OK, result.returncode, result.stderr)
        self.assertEqual("approve", payload["decision"])
        self.assertEqual(task_review.PROTOCOL_VERSION, payload["version"])

        entries = self.entries()
        self.assertEqual(["superseded", "approved"], [entry["state"] for entry in entries])
        for entry in entries:
            self.assertEqual(task_review.PRODUCER, entry["producer"])
            self.assertEqual("ship it", entry["criterion"])
            self.assertEqual([{"root": str(self.root)}], entry["repositories"])
            self.assertRegex(entry["ts"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        approved = entries[-1]
        self.assertEqual("approve", approved["decision"])
        self.assertEqual([], approved["annotations"])
        self.assertNotIn("error", approved)

        verified = self.verify()
        self.assertEqual(task_review.EXIT_OK, verified.returncode, verified.stderr)
        self.assertEqual(
            {"approved": True, "fingerprint": approved["fingerprint"], "state": "approved",
             "reason": "the approval matches the current state"},
            self.assertSingleJsonLine(verified),
        )

    def test_ledger_is_private(self) -> None:
        self.review()
        mode = stat.S_IMODE(os.stat(self.root / ".git" / task_review.LEDGER_NAME).st_mode)
        self.assertEqual(0o600, mode)

    def test_request_changes_and_cancellation_do_not_approve(self) -> None:
        for decision, state, annotations in (
            ("request-changes", "rejected", '[{"text":"needs work","target":{"scope":"review"}}]'),
            ("return-to-planning", "rejected", "[]"),
            ("cancelled", "cancelled", "[]"),
        ):
            with self.subTest(decision=decision):
                template = (
                    '{"version":"1","review_id":"__REVIEW_ID__","decision":"%s","annotations":%s}'
                    % (decision, annotations)
                )
                result = self.review(STUB_RESULT=template)
                self.assertEqual(task_review.EXIT_NOT_APPROVED, result.returncode, result.stderr)
                payload = self.assertSingleJsonLine(result)
                self.assertEqual(decision, payload["decision"])
                self.assertEqual(["superseded", state], self.states()[-2:])
                self.assertEqual(decision, self.entries()[-1]["decision"])
                self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)
                self.assertNotIn("approved", self.states())

    def test_mid_review_change_is_rejected_after_approval(self) -> None:
        result = self.review(STUB_MODE="mutate", STUB_MUTATE=str(self.root / "a.py"))
        self.assertNoApproval(result)
        self.assertIn("changed while the human was deciding", result.stderr)
        self.assertEqual("error", self.states()[-1])
        self.assertIn("error", self.entries()[-1])

    def test_status_reports_the_newest_entry(self) -> None:
        self.review()
        status = self.run_client("status", "--repo", str(self.root))
        self.assertEqual(task_review.EXIT_OK, status.returncode, status.stderr)
        payload = self.assertSingleJsonLine(status)
        self.assertTrue(payload["approved"])
        self.assertEqual("approved", payload["state"])
        self.assertEqual(self.entries()[-1], payload["entry"])
        self.assertTrue(payload["repositories"][0]["matches"])

    def test_status_before_any_review(self) -> None:
        status = self.run_client("status", "--repo", str(self.root))
        self.assertEqual(task_review.EXIT_NOT_APPROVED, status.returncode, status.stderr)
        payload = self.assertSingleJsonLine(status)
        self.assertIsNone(payload["entry"])
        self.assertIn("no task review approval", payload["reason"])

    def test_review_from_a_json_request(self) -> None:
        payload = {
            "version": "1",
            "review_id": "fixed-review-id",
            "criterion": "ship it",
            "repositories": [{"root": str(self.root), "paths": ["a.py"]}],
        }
        result = self.run_client("review", "--json", json.dumps(payload))
        self.assertEqual(task_review.EXIT_OK, result.returncode, result.stderr)
        self.assertEqual("fixed-review-id", self.assertSingleJsonLine(result)["review_id"])
        self.assertEqual([{"root": str(self.root), "paths": ["a.py"]}], self.entries()[-1]["repositories"])
        self.assertEqual(task_review.EXIT_OK, self.verify("--paths", "a.py").returncode)

    def test_verify_from_a_json_request(self) -> None:
        payload = {
            "version": "1",
            "repositories": [{"root": str(self.root), "paths": ["a.py"]}],
        }
        result = self.run_client("verify", "--json", json.dumps(payload))
        self.assertEqual(task_review.EXIT_NOT_APPROVED, result.returncode, result.stderr)
        self.assertFalse(self.assertSingleJsonLine(result)["approved"])


class FailClosedResultTests(ReviewCase):
    def assertRejected(self, **env_extra: str) -> None:
        """A rejected launch must leave the ledger without a single approval."""
        self.assertNoApproval(self.review(**env_extra))
        self.assertNotIn("approved", self.states(), f"an approval was recorded: {self.entries()}")

    def test_non_json_launcher_output(self) -> None:
        self.assertRejected(STUB_MODE="garbage")

    def test_launcher_failure(self) -> None:
        result = self.review(STUB_MODE="fail")
        self.assertNoApproval(result)
        self.assertIn("not open or is not a Git worktree", result.stderr)
        self.assertIn("error", self.states()[-1])

    def test_two_json_documents(self) -> None:
        self.assertRejected(STUB_RESULT=APPROVE + "\n" + APPROVE)

    def test_json_array_result(self) -> None:
        self.assertRejected(STUB_RESULT="[]")

    def test_review_id_mismatch(self) -> None:
        self.assertRejected(STUB_RESULT=APPROVE.replace("__REVIEW_ID__", "some-other-review"))

    def test_wrong_protocol_version(self) -> None:
        self.assertRejected(STUB_RESULT=APPROVE.replace('"version":"1"', '"version":"2"'))

    def test_missing_protocol_version(self) -> None:
        self.assertRejected(STUB_RESULT=APPROVE.replace('"version":"1",', ""))

    def test_unknown_decision(self) -> None:
        self.assertRejected(STUB_RESULT=APPROVE.replace("approve", "ship-it"))

    def test_missing_decision(self) -> None:
        self.assertRejected(STUB_RESULT='{"version":"1","review_id":"__REVIEW_ID__","annotations":[]}')

    def test_missing_annotations(self) -> None:
        self.assertRejected(STUB_RESULT='{"version":"1","review_id":"__REVIEW_ID__","decision":"approve"}')

    def test_request_changes_without_text(self) -> None:
        self.assertRejected(STUB_RESULT=REJECT.replace("needs work", "   "))

    def test_request_changes_without_annotations(self) -> None:
        self.assertRejected(
            STUB_RESULT='{"version":"1","review_id":"__REVIEW_ID__","decision":"request-changes","annotations":[]}'
        )

    def test_cancelled_with_annotations(self) -> None:
        self.assertRejected(
            STUB_RESULT='{"version":"1","review_id":"__REVIEW_ID__","decision":"cancelled",'
            '"annotations":[{"text":"why not","target":{"scope":"review"}}]}'
        )

    def test_malformed_annotation_target(self) -> None:
        malformed = (
            '{"version":"1","review_id":"__REVIEW_ID__","decision":"approve","annotations":'
            '[{"text":"look here","target":{"scope":"line","repository":"/r","path":"a.py",'
            '"side":"new","start_line":5,"end_line":2}}]}'
        )
        self.assertRejected(STUB_RESULT=malformed)

    def test_annotation_without_a_target(self) -> None:
        self.assertRejected(
            STUB_RESULT='{"version":"1","review_id":"__REVIEW_ID__","decision":"approve",'
            '"annotations":[{"text":"look here"}]}'
        )


class LedgerTests(ReviewCase):
    def append_raw(self, line: str) -> None:
        path = self.root / ".git" / task_review.LEDGER_NAME
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def test_newest_entry_wins(self) -> None:
        self.review()
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)
        self.review(STUB_RESULT=REJECT)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)
        self.review()
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)
        self.assertEqual(
            ["superseded", "approved", "superseded", "rejected", "superseded", "approved"],
            self.states(),
        )

    def test_malformed_ledger_lines_are_skipped(self) -> None:
        self.review()
        self.append_raw("{not json at all")
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)
        self.append_raw("[]")
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)
        self.assertEqual(2, len(self.entries()), "malformed lines are skipped, not counted")

    def test_producer_mismatch_never_validates(self) -> None:
        self.review()
        approved = self.entries()[-1]
        self.append_raw(json.dumps({**approved, "producer": "pi-rdg-task-review"}))
        result = self.verify()
        self.assertEqual(task_review.EXIT_NOT_APPROVED, result.returncode, result.stderr)
        self.assertIn(task_review.PRODUCER, self.assertSingleJsonLine(result)["reason"])

    def test_fingerprint_mismatch_never_validates(self) -> None:
        self.review()
        self.append_raw(json.dumps({**self.entries()[-1], "fingerprint": "0" * 64}))
        result = self.verify()
        self.assertEqual(task_review.EXIT_NOT_APPROVED, result.returncode, result.stderr)
        self.assertIn("changed since", self.assertSingleJsonLine(result)["reason"])

    def test_verify_fails_after_any_worktree_change(self) -> None:
        self.review()
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)
        self.write("a.py", "print('changed after approval')\n")
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)
        self.write("extra.txt", "a new file\n")
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)
        (self.root / "extra.txt").unlink()
        self.write("a.py", "print('two')\n")
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode, "restoring the state restores the approval")

    def test_consume_after_approve_makes_verify_fail(self) -> None:
        self.review()
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)
        consumed = self.run_client("consume", "--repo", str(self.root))
        self.assertEqual(task_review.EXIT_OK, consumed.returncode, consumed.stderr)
        self.assertEqual("consumed", self.assertSingleJsonLine(consumed)["state"])
        result = self.verify()
        self.assertEqual(task_review.EXIT_NOT_APPROVED, result.returncode, result.stderr)
        self.assertIn("consumed", self.assertSingleJsonLine(result)["reason"])
        # The approval was spent, not erased: the record survives for the audit.
        self.assertEqual(["superseded", "approved", "consumed"], self.states())
        self.assertEqual("approve", self.entries()[-1]["decision"])

    def test_revoke_after_approve_makes_verify_fail(self) -> None:
        self.review()
        revoked = self.run_client("revoke", "--repo", str(self.root))
        self.assertEqual(task_review.EXIT_OK, revoked.returncode, revoked.stderr)
        self.assertEqual("superseded", self.assertSingleJsonLine(revoked)["state"])
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)

    def test_a_failing_review_revokes_a_previous_approval(self) -> None:
        self.review()
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)
        self.assertNoApproval(self.review(STUB_MODE="garbage"))
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)

    def test_scope_narrows_what_invalidates_an_approval(self) -> None:
        self.review("--paths", "a.py")
        self.assertEqual(task_review.EXIT_OK, self.verify("--paths", "a.py").returncode)
        self.write("other/b.txt", "out of scope change\n")
        scoped = self.verify("--paths", "a.py")
        self.assertEqual(task_review.EXIT_OK, scoped.returncode, scoped.stderr)
        unscoped = self.verify()
        self.assertEqual(task_review.EXIT_NOT_APPROVED, unscoped.returncode, unscoped.stderr)
        self.write("a.py", "print('in scope')\n")
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify("--paths", "a.py").returncode)

    def test_every_repository_needs_an_approval(self) -> None:
        other = self.make_repo("second")
        (other / "a.py").write_text("print('changed')\n", encoding="utf-8")
        both = ["--repo", str(self.root), "--repo", str(other)]
        result = self.run_client("review", "--criterion", "ship both", *both)
        self.assertEqual(task_review.EXIT_OK, result.returncode, result.stderr)
        for root in (self.root, other):
            entries = task_review.read_entries(str(root / ".git" / task_review.LEDGER_NAME))
            self.assertEqual(["superseded", "approved"], [entry["state"] for entry in entries])
        self.assertEqual(task_review.EXIT_OK, self.run_client("verify", *both).returncode)

        # One spent approval is enough to fail the whole set.
        self.run_client("consume", "--repo", str(other))
        both_roots = self.run_client("verify", *both)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, both_roots.returncode, both_roots.stderr)
        self.assertIn("consumed", self.assertSingleJsonLine(both_roots)["reason"])
        # The fingerprint covers the whole reviewed set, so one repository on
        # its own never validates an approval recorded for two.
        single = self.verify()
        self.assertEqual(task_review.EXIT_NOT_APPROVED, single.returncode, single.stderr)
        self.assertIn("changed since", self.assertSingleJsonLine(single)["reason"])

    def test_consume_and_revoke_accept_every_reviewed_repository(self) -> None:
        other = self.make_repo("second")
        (other / "a.py").write_text("print('changed')\n", encoding="utf-8")
        both = ["--repo", str(self.root), "--repo", str(other)]
        for command, state in (("consume", "consumed"), ("revoke", "superseded")):
            self.assertEqual(task_review.EXIT_OK, self.run_client("review", "--criterion", "ship both", *both).returncode)
            closed = self.run_client(command, *both)
            self.assertEqual(task_review.EXIT_OK, closed.returncode, closed.stderr)
            self.assertEqual(state, self.assertSingleJsonLine(closed)["state"])
            self.assertEqual(task_review.EXIT_NOT_APPROVED, self.run_client("verify", *both).returncode)

    def test_status_falls_back_to_the_working_directory(self) -> None:
        self.review()
        status = self.run_client("status", cwd=self.root)
        self.assertEqual(task_review.EXIT_OK, status.returncode, status.stderr)
        self.assertEqual(str(self.root), self.assertSingleJsonLine(status)["repositories"][0]["root"])


class InjectionTests(ReviewCase):
    """The git and launcher seams are replaceable, so a test never needs RDG."""

    def test_injected_launcher_and_git_runners_drive_the_review(self) -> None:
        seen: dict[str, object] = {}

        def fake_launch(launcher: str, request_json: str, timeout: "int | None") -> bytes:
            seen["launcher"] = launcher
            seen["request"] = json.loads(request_json)
            seen["timeout"] = timeout
            return (
                json.dumps(
                    {
                        "version": "1",
                        "review_id": seen["request"]["review_id"],
                        "decision": "approve",
                        "annotations": [],
                    }
                )
                + "\n"
            ).encode()

        git = task_review.run_git
        calls: list[str] = []

        def counting_git(root: str, args, *, allowed_codes=(0,)):
            calls.append(args[0])
            return git(root, args, allowed_codes=allowed_codes)

        with self.captured() as (out, _):
            code = task_review.main(
                ["review", "--criterion", "ship it", "--repo", str(self.root)],
                {task_review.LAUNCHER_ENV: "/nonexistent/rdg", task_review.TIMEOUT_ENV: "0"},
                git=counting_git,
                launch=fake_launch,
            )
        self.assertEqual(task_review.EXIT_OK, code)
        self.assertEqual("approve", json.loads(out.getvalue())["decision"])
        self.assertEqual("/nonexistent/rdg", seen["launcher"])
        self.assertIsNone(seen["timeout"])
        self.assertEqual(str(self.root), seen["request"]["repositories"][0]["root"])
        self.assertIn("rev-parse", calls)
        self.assertIn("status", calls)
        self.assertIn("diff", calls)
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)

    def test_injected_launcher_failure_is_an_error(self) -> None:
        def failing_launch(launcher: str, request_json: str, timeout: "int | None") -> bytes:
            raise task_review.LauncherError("no review window")

        with self.captured() as (_, err):
            code = task_review.main(
                ["review", "--criterion", "ship it", "--repo", str(self.root)],
                {},
                launch=failing_launch,
            )
        self.assertIn("no review window", err.getvalue())
        self.assertEqual(task_review.EXIT_ERROR, code)
        self.assertEqual("error", self.states()[-1])
        self.assertIn("no review window", self.entries()[-1]["error"])


class TimeoutTests(ReviewCase):
    def test_timeout_environment(self) -> None:
        self.assertEqual(1800, task_review.resolve_timeout({}))
        self.assertEqual(5, task_review.resolve_timeout({task_review.TIMEOUT_ENV: "5"}))
        self.assertIsNone(task_review.resolve_timeout({task_review.TIMEOUT_ENV: "0"}))
        for value in ("-1", "soon"):
            with self.subTest(value=value):
                with self.assertRaises(task_review.TaskReviewError):
                    task_review.resolve_timeout({task_review.TIMEOUT_ENV: value})

    def test_launcher_failure_on_a_missing_binary(self) -> None:
        result = self.run_client(
            "review", "--criterion", "x", "--repo", str(self.root),
            **{task_review.LAUNCHER_ENV: "/nonexistent/rdg"},
        )
        self.assertNoApproval(result)
        self.assertIn("unable to run the reviewer", result.stderr)


class PackagingTests(unittest.TestCase):
    def test_client_is_executable_and_uses_the_standard_library_only(self) -> None:
        self.assertTrue(os.access(CLIENT, os.X_OK), "scripts/task_review.py must be executable")
        third_party = {
            name.split(".")[0]
            for name in sys.modules
            if getattr(sys.modules.get(name), "__file__", "") and "site-packages" in sys.modules[name].__file__
        }
        self.assertEqual(set(), {name for name in third_party if name == task_review.__name__})
        source = CLIENT.read_text(encoding="utf-8")
        for banned in ("import requests", "import yaml", "pip install", "urllib.request"):
            self.assertNotIn(banned, source, f"the client must stay dependency-free: {banned}")

    def test_client_reports_usage_without_a_subcommand(self) -> None:
        completed = subprocess.run([sys.executable, str(CLIENT)], capture_output=True, text=True)
        self.assertEqual(task_review.EXIT_ERROR, completed.returncode)
        self.assertEqual("", completed.stdout)
        self.assertIn("usage:", completed.stderr)

class ReviewerResolutionTests(unittest.TestCase):
    """The reviewer is pluggable; the bundled HTML reviewer is the default."""

    def test_html_is_the_default_reviewer(self) -> None:
        self.assertEqual(task_review.HTML_REVIEWER, task_review.DEFAULT_REVIEWER)
        self.assertEqual(task_review.HTML_REVIEWER, task_review.resolve_reviewer({}))

    def test_html_reviewer_resolves_to_the_bundled_script(self) -> None:
        command = task_review.resolve_launcher_command(task_review.HTML_REVIEWER)
        self.assertEqual(2, len(command))
        self.assertEqual(sys.executable, command[0])
        self.assertEqual(ROOT / "scripts/html_review.py", Path(command[1]))
        self.assertTrue(Path(command[1]).is_file(), "the default reviewer must ship with the client")

    def test_rdg_reviewer_resolves_to_the_binary(self) -> None:
        self.assertEqual(["rdg"], task_review.resolve_launcher_command(task_review.RDG_REVIEWER))

    def test_reviewer_environment_wins_over_the_legacy_variable(self) -> None:
        environ = {task_review.REVIEWER_ENV: "rdg", task_review.LAUNCHER_ENV: "/legacy/reviewer"}
        self.assertEqual("rdg", task_review.resolve_reviewer(environ))

    def test_legacy_reviewer_variable_is_still_honored(self) -> None:
        self.assertEqual(
            "/legacy/reviewer",
            task_review.resolve_reviewer({task_review.LAUNCHER_ENV: "/legacy/reviewer"}),
        )

    def test_blank_reviewer_values_fall_through(self) -> None:
        self.assertEqual(
            task_review.HTML_REVIEWER,
            task_review.resolve_reviewer({task_review.REVIEWER_ENV: "   ", task_review.LAUNCHER_ENV: ""}),
        )

    def test_an_explicit_launcher_path_still_wins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            launcher = Path(directory) / "reviewer"
            launcher.write_text("#!/bin/sh\n", encoding="utf-8")
            self.assertEqual([str(launcher)], task_review.resolve_launcher_command(str(launcher)))




class DocumentCommandTests(unittest.TestCase):
    """A specification reviewed in the browser, approved, then spent."""

    APPROVE = '{"version":"1","review_id":"__REVIEW_ID__","decision":"approve","annotations":[]}'
    COMMENT = (
        '{"version":"1","review_id":"__REVIEW_ID__","decision":"request-changes",'
        '"annotations":[{"text":"name the failure mode","target":'
        '{"scope":"line","path":"__DOC__","start_line":5,"end_line":5}}]}'
    )

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(os.path.realpath(self._tmp.name)) / "repo"
        (self.root / "docs/specs").mkdir(parents=True)
        self.doc = self.root / "docs/specs/2026-09-27-topic.md"
        self.doc.write_text("# Topic\n\n## Problem\n\nSomething is wrong.\n\n- a goal\n", encoding="utf-8")
        for command in (
            ["init", "-q", "-b", "main", "."],
            ["add", "-A"],
            ["-c", "user.name=Test", "-c", "user.email=t@local", "commit", "-qm", "init"],
        ):
            subprocess.run(["git", "-C", str(self.root), *command], check=True, capture_output=True)
        self.launcher = Path(os.path.realpath(self._tmp.name)) / "stub-reviewer"
        self.launcher.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "assert sys.argv[1] == '--review-doc', sys.argv\n"
            "request = json.loads(sys.argv[2])\n"
            "template = os.environ['STUB_RESULT'].replace('__REVIEW_ID__', request['review_id'])\n"
            "sys.stdout.write(template.replace('__DOC__', request['path']) + '\\n')\n",
            encoding="utf-8",
        )
        self.launcher.chmod(0o755)

    def run_client(self, *args: str, template: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLIENT), *args],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "STUB_RESULT": template,
                task_review.REVIEWER_ENV: str(self.launcher),
                task_review.TIMEOUT_ENV: "60",
            },
            timeout=90,
        )

    def criterion_args(self) -> tuple:
        return ("--criterion", "Fix the parser", "--doc", str(self.doc))

    def test_an_approved_spec_verifies_and_then_stops_counting(self) -> None:
        reviewed = self.run_client("review-doc", *self.criterion_args(), template=self.APPROVE)
        self.assertEqual(task_review.EXIT_OK, reviewed.returncode, reviewed.stderr)
        self.assertEqual("approve", json.loads(reviewed.stdout)["decision"])
        verified = self.run_client("verify-doc", *self.criterion_args(), template=self.APPROVE)
        self.assertEqual(task_review.EXIT_OK, verified.returncode, verified.stdout + verified.stderr)
        self.assertTrue(json.loads(verified.stdout)["approved"])
        consumed = self.run_client("consume-doc", *self.criterion_args(), template=self.APPROVE)
        self.assertEqual(task_review.EXIT_OK, consumed.returncode, consumed.stderr)
        after = self.run_client("verify-doc", *self.criterion_args(), template=self.APPROVE)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, after.returncode)
        self.assertEqual("consumed", json.loads(after.stdout)["state"])

    def test_document_recovery_preserves_the_document_request_and_verified_decision(self):
        recovery = self.root.parent / "document recovery"
        result = self.run_client(
            "review-doc", *self.criterion_args(), "--recovery-dir", str(recovery), template=self.APPROVE,
        )
        self.assertEqual(task_review.EXIT_OK, result.returncode, result.stderr)
        request = json.loads((recovery / "request.json").read_text())
        self.assertEqual(str(self.doc), request["path"])
        self.assertNotIn("repositories", request)
        self.assertEqual(json.loads(result.stdout), json.loads((recovery / "result.json").read_text()))
        verified = self.run_client("verify-doc", *self.criterion_args(), template=self.APPROVE)
        self.assertEqual(task_review.EXIT_OK, verified.returncode, verified.stderr)

    def test_editing_the_spec_after_approval_invalidates_it(self) -> None:
        reviewed = self.run_client("review-doc", *self.criterion_args(), template=self.APPROVE)
        self.assertEqual(task_review.EXIT_OK, reviewed.returncode, reviewed.stderr)
        self.doc.write_text(self.doc.read_text(encoding="utf-8") + "\nOne more line.\n", encoding="utf-8")
        verified = self.run_client("verify-doc", *self.criterion_args(), template=self.APPROVE)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, verified.returncode)
        self.assertIn("changed since the approval", json.loads(verified.stdout)["reason"])

    def test_a_different_criterion_does_not_match_the_approval(self) -> None:
        self.run_client("review-doc", *self.criterion_args(), template=self.APPROVE)
        other = self.run_client(
            "verify-doc", "--criterion", "Something else entirely", "--doc", str(self.doc), template=self.APPROVE
        )
        self.assertEqual(task_review.EXIT_NOT_APPROVED, other.returncode)

    def test_verify_takes_the_criterion_from_the_ledger_when_it_is_not_repeated(self) -> None:
        self.run_client("review-doc", *self.criterion_args(), template=self.APPROVE)
        verified = self.run_client("verify-doc", "--doc", str(self.doc), template=self.APPROVE)
        self.assertEqual(task_review.EXIT_OK, verified.returncode, verified.stdout + verified.stderr)

    def test_requested_changes_leaves_no_approval(self) -> None:
        reviewed = self.run_client("review-doc", *self.criterion_args(), template=self.COMMENT)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, reviewed.returncode)
        result = json.loads(reviewed.stdout)
        self.assertEqual("request-changes", result["decision"])
        self.assertEqual(5, result["annotations"][0]["target"]["start_line"])
        verified = self.run_client("verify-doc", *self.criterion_args(), template=self.COMMENT)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, verified.returncode)

    def test_a_diff_shaped_result_is_rejected_for_a_document_review(self) -> None:
        template = (
            '{"version":"1","review_id":"__REVIEW_ID__","decision":"approve","annotations":'
            '[{"text":"wrong","target":{"scope":"line","repository":"/tmp","path":"a.py",'
            '"side":"new","start_line":1,"end_line":1}}]}'
        )
        reviewed = self.run_client("review-doc", *self.criterion_args(), template=template)
        self.assertEqual(task_review.EXIT_ERROR, reviewed.returncode, "a diff annotation is not a document comment")
        self.assertIn("malformed annotations", reviewed.stderr)

    def test_the_ledger_names_the_document(self) -> None:
        self.run_client("review-doc", *self.criterion_args(), template=self.APPROVE)
        common = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        entries = [
            json.loads(line)
            for line in (Path(common) / task_review.LEDGER_NAME).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(str(self.doc), entries[-1]["document"])

    def test_a_document_outside_a_repository_keeps_its_own_ledger(self) -> None:
        outside = Path(os.path.realpath(self._tmp.name)) / "loose"
        outside.mkdir()
        loose = outside / "notes.md"
        loose.write_text("# Notes\n", encoding="utf-8")
        reviewed = self.run_client(
            "review-doc", "--criterion", "Read the notes", "--doc", str(loose), template=self.APPROVE
        )
        self.assertEqual(task_review.EXIT_OK, reviewed.returncode, reviewed.stderr)
        self.assertTrue((outside / task_review.LEDGER_NAME).is_file())
        verified = self.run_client(
            "verify-doc", "--criterion", "Read the notes", "--doc", str(loose), template=self.APPROVE
        )
        self.assertEqual(task_review.EXIT_OK, verified.returncode, verified.stdout + verified.stderr)


class GuidedReviewTests(ReviewCase):
    def guide(self) -> dict:
        request = task_review.build_request("ship it", [task_review.Repository(str(self.root), ["a.py"])])
        return {
            "version": 1, "fingerprint": task_review.collect_snapshot(request.repositories).fingerprint,
            "summary": "Print a different value", "before": "Print one", "after": "Print two",
            "chapters": [{"title": "Output", "summary": "Change the printed value",
                          "files": [{"repository": str(self.root), "path": "a.py"}]}],
        }

    def invoke(self, *arguments: str, launch=None) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = task_review.main(list(arguments), {task_review.REVIEWER_ENV: "html"}, launch=launch or self.approve)
        return code, stdout.getvalue(), stderr.getvalue()

    @staticmethod
    def approve(launcher, request_json, timeout):
        request = json.loads(request_json)
        return json.dumps({"version": "1", "review_id": request["review_id"], "decision": "approve", "annotations": []}).encode()

    def test_status_accepts_paths_and_returns_the_scoped_guide_fingerprint(self):
        expected = self.guide()["fingerprint"]
        result = self.run_client("status", "--repo", str(self.root), "--paths", "a.py")
        self.assertEqual(task_review.EXIT_NOT_APPROVED, result.returncode, result.stderr)
        self.assertEqual(expected, json.loads(result.stdout)["fingerprint"])

    def test_cli_captures_guide_once_and_existing_verification_still_checks_code(self):
        value = self.guide()
        path = self.base / "guide.json"
        path.write_text(json.dumps(value))

        def launch(launcher, request_json, timeout):
            captured = json.loads(request_json)
            path.write_text("changed after capture")
            self.assertEqual(value, captured["guide"])
            return self.approve(launcher, request_json, timeout)

        code, out, error = self.invoke("review", "--criterion", "ship it", "--repo", str(self.root), "--paths", "a.py", "--guide", str(path), launch=launch)
        self.assertEqual(task_review.EXIT_OK, code, out + error)
        self.assertEqual(task_review.EXIT_OK, self.verify("--paths", "a.py").returncode)
        self.write("a.py", "changed after approval\n")
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify("--paths", "a.py").returncode)

    def test_inline_guide_round_trip_and_mid_review_mutation_fails_closed(self):
        request = task_review.build_request("ship it", [task_review.Repository(str(self.root), ["a.py"])])
        payload = {**request.payload(), "guide": self.guide()}

        def launch(launcher, request_json, timeout):
            self.assertEqual(payload["guide"], json.loads(request_json)["guide"])
            self.write("a.py", "mutated during review\n")
            return self.approve(launcher, request_json, timeout)

        code, out, error = self.invoke("review", "--json", json.dumps(payload), launch=launch)
        self.assertEqual(task_review.EXIT_ERROR, code)
        self.assertIn("changed while the human", error)
        self.assertEqual("", out)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify("--paths", "a.py").returncode)

    def test_stale_unknown_and_non_html_guides_never_reach_a_launcher(self):
        request = task_review.build_request("ship it", [task_review.Repository(str(self.root), ["a.py"])])
        for problem in ("stale", "unknown", "backend"):
            with self.subTest(problem=problem):
                value = self.guide()
                launcher = "html"
                if problem == "stale":
                    value["fingerprint"] = "b" * 64
                elif problem == "unknown":
                    value["chapters"][0]["files"][0]["path"] = "untracked.txt"
                else:
                    launcher = "rdg"
                guided = task_review.normalize_request({**request.payload(), "guide": value})
                with self.assertRaises(task_review.TaskReviewError):
                    task_review.command_review(guided, git=task_review.run_git, launch=lambda *args: self.fail("invalid guide reached launcher"), launcher=launcher, timeout=1)
                self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify("--paths", "a.py").returncode)

    def test_bad_files_and_conflicting_flags_report_local_errors(self):
        path = self.base / "guide.json"
        for content in (b"not JSON", b"\xff", b"x" * (task_review.MAX_GUIDE_BYTES + 1)):
            path.write_bytes(content)
            code, out, error = self.invoke("review", "--criterion", "ship it", "--repo", str(self.root), "--guide", str(path))
            self.assertEqual(task_review.EXIT_ERROR, code, out)
            self.assertIn("guide", error)
        path.unlink()
        with self.assertRaisesRegex(task_review.UsageError, "unable to read guide"):
            task_review.read_guide(str(path))
        request = task_review.build_request("ship it", [task_review.Repository(str(self.root))])
        code, out, error = self.invoke("review", "--json", request.to_json(), "--guide", str(path))
        self.assertEqual(task_review.EXIT_ERROR, code, out)
        self.assertIn("--guide", error)


class RecoveryFlowTests(ReviewCase):
    def recovery(self) -> Path:
        return self.base / "private recovery"

    def read_recovery(self, name: str) -> dict:
        return json.loads((self.recovery() / name).read_text())

    def test_validated_result_and_exact_request_are_retained(self):
        result = self.review("--recovery-dir", str(self.recovery()), "--paths", "a.py")
        self.assertEqual(task_review.EXIT_OK, result.returncode, result.stderr)
        decision = self.assertSingleJsonLine(result)
        self.assertEqual(decision, self.read_recovery("result.json"))
        request = self.read_recovery("request.json")
        self.assertEqual(decision["review_id"], request["review_id"])
        self.assertEqual([{"root": str(self.root), "paths": ["a.py"]}], request["repositories"])
        state = self.read_recovery("state.json")
        self.assertEqual(("finished", "approve", 0), (state["state"], state["decision"], state["exit_code"]))
        self.assertEqual(task_review.EXIT_OK, self.verify("--paths", "a.py").returncode)
        self.assertEqual(0o700, stat.S_IMODE(self.recovery().stat().st_mode))
        for artifact in self.recovery().iterdir():
            self.assertEqual(0o600, stat.S_IMODE(artifact.stat().st_mode), artifact.name)

    def test_nonapproval_is_a_finished_decision_not_a_launcher_error(self):
        result = self.review("--recovery-dir", str(self.recovery()), STUB_RESULT=REJECT)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, result.returncode, result.stderr)
        self.assertEqual("request-changes", self.read_recovery("result.json")["decision"])
        state = self.read_recovery("state.json")
        self.assertEqual(("finished", 1), (state["state"], state["exit_code"]))
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)

    def test_malformed_result_retains_error_without_an_approval_artifact(self):
        result = self.review("--recovery-dir", str(self.recovery()), STUB_MODE="garbage")
        self.assertNoApproval(result)
        self.assertFalse((self.recovery() / "result.json").exists())
        state = self.read_recovery("state.json")
        self.assertEqual(("error", 2), (state["state"], state["exit_code"]))
        self.assertIn("JSON", state["error"])

    def test_approval_for_changed_inputs_is_not_retained_as_a_result(self):
        result = self.review(
            "--recovery-dir", str(self.recovery()), STUB_MODE="mutate", STUB_MUTATE=str(self.root / "a.py"),
        )
        self.assertNoApproval(result)
        self.assertFalse((self.recovery() / "result.json").exists())
        self.assertIn("changed while the human", self.read_recovery("state.json")["error"])

    def test_recovery_storage_failure_cannot_leave_a_verifiable_approval(self):
        document = self.root / "plan.md"
        document.write_text("# Approved plan\n")
        replace_file = os.replace
        for command in ("review", "review-doc"):
            for artifact in ("result.json", "state.json"):
                with self.subTest(command=command, artifact=artifact):
                    directory = self.base / f"{command}-{artifact}"
                    scope = ["--repo", str(self.root)] if command == "review" else ["--doc", str(document)]
                    args = task_review.build_parser().parse_args(
                        [command, "--criterion", "ship it", *scope, "--recovery-dir", str(directory)],
                    )

                    def fail_final_write(source, destination):
                        if Path(destination).name == artifact:
                            payload = json.loads(Path(source).read_text())
                            if artifact == "result.json" or payload.get("state") == "finished":
                                raise OSError("recovery storage unavailable")
                        return replace_file(source, destination)

                    with self.captured(), mock.patch.object(task_review.os, "replace", side_effect=fail_final_write):
                        with self.assertRaises(OSError):
                            task_review.dispatch(
                                args, {}, git=task_review.run_git,
                                launch=GuidedReviewTests.approve, launch_doc=GuidedReviewTests.approve,
                            )
                    verify_command = "verify" if command == "review" else "verify-doc"
                    verified = self.run_client(verify_command, *scope)
                    self.assertEqual(task_review.EXIT_NOT_APPROVED, verified.returncode, verified.stdout)
                    self.assertEqual("error", json.loads((directory / "state.json").read_text())["state"])

    def test_complete_multi_repository_scope_is_retained_and_verified_together(self):
        other = self.make_repo("second repository")
        (other / "a.py").write_text("second change\n")
        result = self.run_client(
            "review", "--criterion", "ship both", "--repo", str(self.root), "--repo", str(other),
            "--recovery-dir", str(self.recovery()),
        )
        self.assertEqual(task_review.EXIT_OK, result.returncode, result.stderr)
        verify = self.run_client("verify", "--repo", str(self.root), "--repo", str(other))
        self.assertEqual(task_review.EXIT_OK, verify.returncode, verify.stderr)
        (other / "a.py").write_text("changed after approval\n")
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.run_client(
            "verify", "--repo", str(self.root), "--repo", str(other),
        ).returncode)

    def test_existing_run_is_not_overwritten_or_relaunched(self):
        first = self.review("--recovery-dir", str(self.recovery()))
        self.assertEqual(task_review.EXIT_OK, first.returncode, first.stderr)
        saved = {p.name: p.read_bytes() for p in self.recovery().iterdir()}
        second = self.review("--recovery-dir", str(self.recovery()))
        self.assertEqual(task_review.EXIT_ERROR, second.returncode, second.stderr)
        self.assertIn("recover", second.stderr)
        self.assertEqual(saved, {p.name: p.read_bytes() for p in self.recovery().iterdir()})
        self.assertEqual(task_review.EXIT_OK, self.verify().returncode)

    def test_recovery_inside_reviewed_tree_or_public_directory_is_rejected(self):
        public = self.base / "public"
        public.mkdir(mode=0o755)
        for path in (self.root / "recovery", public):
            with self.subTest(path=path):
                result = self.review("--recovery-dir", str(path))
                self.assertEqual(task_review.EXIT_ERROR, result.returncode, result.stderr)
                self.assertEqual([], self.entries())
        self.assertFalse((self.root / "recovery").exists())

    @unittest.skipUnless(os.name == "posix", "native startup cancellation requires POSIX")
    def test_cancellation_during_process_recording_reaps_the_reviewer(self):
        self.launcher.write_text("#!/usr/bin/env python3\nimport signal\nsignal.pause()\n")
        bootstrap = (
            "import os,signal,sys; "
            f"sys.path.insert(0,{str(ROOT / 'scripts')!r}); "
            "import task_review; original=task_review.ReviewRecovery.reviewer_started\n"
            "def started(self,pid,command):\n"
            " original(self,pid,command)\n"
            " os.kill(os.getpid(),signal.SIGTERM)\n"
            "task_review.ReviewRecovery.reviewer_started=started\n"
            "sys.exit(task_review.main(sys.argv[1:]))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", bootstrap, "review", "--criterion", "ship it",
             "--repo", str(self.root), "--recovery-dir", str(self.recovery())],
            capture_output=True, env=self.env(), timeout=10,
        )
        record = self.read_recovery("process.json")
        pid = record["reviewer_pid"]

        def cleanup() -> None:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        self.addCleanup(cleanup)
        self.assertEqual(task_review.EXIT_ERROR, result.returncode, result.stderr.decode())
        self.assertEqual(b"", result.stdout)
        self.assertEqual("error", self.read_recovery("state.json")["state"])
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)

    @unittest.skipUnless(os.name == "posix", "FIFO handshake and native cancellation require POSIX")
    def test_live_diagnostics_arrive_before_decision_and_cancellation_reaps_reviewer(self):
        fifo = self.base / "decision"
        os.mkfifo(fifo)
        self.launcher.write_text(
            "#!/usr/bin/env python3\n"
            "import os,sys\n"
            "print('review page ready', file=sys.stderr, flush=True)\n"
            "with open(os.environ['DECISION_FIFO'], 'rb') as stream: stream.read(1)\n"
        )
        process = subprocess.Popen(
            [sys.executable, str(CLIENT), "review", "--criterion", "ship it",
             "--repo", str(self.root), "--recovery-dir", str(self.recovery())],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=self.env(DECISION_FIFO=str(fifo)),
        )
        def cleanup() -> None:
            if process.poll() is None:
                process.terminate()
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                record = self.recovery() / "process.json"
                if record.exists():
                    pid = json.loads(record.read_text()).get("reviewer_pid")
                    if pid is not None:
                        try:
                            os.killpg(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                process.kill()
                process.communicate(timeout=10)

        self.addCleanup(cleanup)
        with selectors.DefaultSelector() as selector:
            selector.register(process.stderr, selectors.EVENT_READ)
            self.assertTrue(selector.select(10), "reviewer diagnostics were buffered until exit")
            self.assertEqual(b"review page ready\n", process.stderr.readline())
        self.assertIsNone(process.poll())
        state = self.read_recovery("state.json")
        self.assertEqual("reviewing", state["state"])
        reviewer_pid = self.read_recovery("process.json")["reviewer_pid"]
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(task_review.EXIT_ERROR, process.returncode, stderr.decode())
        self.assertEqual(b"", stdout)
        self.assertEqual("error", self.read_recovery("state.json")["state"])
        with self.assertRaises(ProcessLookupError):
            os.kill(reviewer_pid, 0)
        self.assertEqual(task_review.EXIT_NOT_APPROVED, self.verify().returncode)


class PreflightTests(ReviewCase):
    guide = GuidedReviewTests.guide

    def test_valid_guide_preflight_does_not_change_existing_approval(self):
        self.assertEqual(task_review.EXIT_OK, self.review("--paths", "a.py").returncode)
        ledger = (self.root / ".git" / task_review.LEDGER_NAME).read_bytes()
        guide = self.base / "guide.json"
        guide.write_text(json.dumps(self.guide()))
        result = self.run_client(
            "preflight", "--criterion", "ship it", "--repo", str(self.root), "--paths", "a.py",
            "--guide", str(guide), **{task_review.REVIEWER_ENV: "html"},
        )
        self.assertEqual(task_review.EXIT_OK, result.returncode, result.stderr)
        payload = self.assertSingleJsonLine(result)
        self.assertEqual(self.guide()["fingerprint"], payload["fingerprint"])
        self.assertNotIn("decision", payload)
        self.assertEqual(ledger, (self.root / ".git" / task_review.LEDGER_NAME).read_bytes())

    def test_duplicate_stale_and_out_of_scope_guides_fail_without_ledger_mutation(self):
        for problem in ("duplicate", "stale", "scope"):
            with self.subTest(problem=problem):
                value = self.guide()
                if problem == "duplicate":
                    value["chapters"].append(value["chapters"][0])
                elif problem == "stale":
                    value["fingerprint"] = "0" * 64
                else:
                    value["chapters"][0]["files"][0]["path"] = "other/b.txt"
                guide = self.base / "guide.json"
                guide.write_text(json.dumps(value))
                result = self.run_client(
                    "preflight", "--criterion", "ship it", "--repo", str(self.root), "--paths", "a.py",
                    "--guide", str(guide), **{task_review.REVIEWER_ENV: "html"},
                )
                self.assertEqual(task_review.EXIT_ERROR, result.returncode, result.stderr)
                self.assertIn({"duplicate": "duplicate", "stale": "stale", "scope": "outside the captured diff"}[problem], result.stderr)
                self.assertEqual("", result.stdout)
                self.assertEqual([], self.entries())


if __name__ == "__main__":
    unittest.main()
