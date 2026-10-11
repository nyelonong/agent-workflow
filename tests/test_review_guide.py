from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import html_review
import task_review


def guide_value(root: str = "/repo") -> dict:
    return {
        "version": 1, "fingerprint": "a" * 64,
        "summary": "Enable sharing", "before": "No sharing", "after": "Share to threads",
        "flow": {"before": ["Content"], "after": ["Content", "Thread"]},
        "chapters": [{"title": "Send content", "summary": "Upload then send",
                      "files": [{"repository": root, "path": "src/send.py"}]}],
    }


class GuideValidationTests(unittest.TestCase):
    def test_request_round_trip_captures_metadata_without_changing_guide_free_requests(self):
        payload = {"version": "1", "review_id": "review", "criterion": "Sharing works",
                   "repositories": [{"root": "/repo"}]}
        plain = task_review.normalize_request(payload)
        self.assertNotIn("guide", plain.payload())
        value = guide_value()
        request = task_review.normalize_request({**payload, "guide": value})
        captured = request.to_json()
        value["summary"] = "changed after capture"
        self.assertEqual("Enable sharing", json.loads(captured)["guide"]["summary"])
        self.assertEqual(request.payload(), task_review.parse_request_json(captured).payload())

    def test_invalid_metadata_and_duplicate_identity_are_rejected(self):
        mutations = [
            lambda value: value.update(version=True),
            lambda value: value.update(fingerprint="not a fingerprint"),
            lambda value: value.update(summary=" "),
            lambda value: value.update(unknown="field"),
            lambda value: value.update(flow={"before": [], "after": ["a"]}),
            lambda value: value.update(chapters=[{"title": "Chapter", "summary": "Explanation", "files": []}]),
            lambda value: value["chapters"][0]["files"][0].update(path="../secret"),
            lambda value: value["chapters"].append(copy.deepcopy(value["chapters"][0])),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                value = guide_value()
                mutate(value)
                with self.assertRaises(task_review.ResultError):
                    task_review.normalize_guide(value)
        value = guide_value()
        value["chapters"] = [{"title": str(i), "summary": "x" * 8000, "files": [{"repository": "/repo", "path": f"{i}.py"}]} for i in range(7)]
        with self.assertRaisesRegex(task_review.ResultError, "48 KiB"):
            task_review.normalize_guide(value)

    def test_freshness_and_scope_validation_use_snapshot_not_narration(self):
        root = str(Path("/repo").resolve())
        file = task_review.FileSnapshot("src/send.py", None, "100644", "100644", "hash", "patch")
        repo = task_review.RepositorySnapshot(root, "HEAD", ["src"], (file,), "repo-hash")
        snapshot = task_review.Snapshot((repo,), "a" * 64)
        guide = task_review.normalize_guide(guide_value(root))
        task_review.validate_guide_snapshot(guide, snapshot)
        guide["fingerprint"] = "b" * 64
        with self.assertRaisesRegex(task_review.ResultError, "stale"):
            task_review.validate_guide_snapshot(guide, snapshot)
        guide["fingerprint"] = snapshot.fingerprint
        guide["chapters"][0]["files"][0]["path"] = "not-in-scope.py"
        with self.assertRaisesRegex(task_review.ResultError, "outside the captured diff"):
            task_review.validate_guide_snapshot(guide, snapshot)

    def test_chapters_cover_each_captured_file_once_across_repositories_and_change_kinds(self):
        repositories = [
            {"root": "/repo", "files": [
                {"repository": "/repo", "path": "src/send.py", "status": "renamed", "old_path": "old.py"},
                {"repository": "/repo", "path": "empty.txt", "status": "deleted"},
                {"repository": "/repo", "path": "picture.png", "binary": True},
            ]},
            {"root": "/other", "files": [{"repository": "/other", "path": "src/send.py", "status": "added"}]},
        ]
        value = guide_value()
        value["chapters"][0]["files"] = [{"repository": "/other", "path": "src/send.py"}, {"repository": "/repo", "path": "src/send.py"}]
        result = html_review.build_guide(value, repositories)
        self.assertEqual([[3, 0], [1, 2]], [chapter["file_indices"] for chapter in result["chapters"]])
        self.assertEqual("Other changes", result["chapters"][-1]["title"])
        self.assertTrue(result["authored"])
        for bad in ("old.py", "outside.py"):
            value["chapters"][0]["files"][0]["path"] = bad
            with self.assertRaises(task_review.ResultError):
                html_review.build_guide(value, repositories)

    def test_fallback_groups_every_file_and_never_claims_before_after_behavior(self):
        repositories = [{"root": "/repo", "files": [
            {"repository": "/repo", "path": "src/a.py"},
            {"repository": "/repo", "path": "src/b.py"},
            {"repository": "/repo", "path": "README.md"},
        ]}]
        result = html_review.build_guide(None, repositories)
        self.assertFalse(result["authored"])
        self.assertNotIn("before", result)
        self.assertNotIn("after", result)
        self.assertEqual([[0, 1], [2]], [chapter["file_indices"] for chapter in result["chapters"]])
        self.assertIn("not by behavior", result["chapters"][0]["summary"])
        self.assertEqual([], html_review.build_guide(None, [])["chapters"])


if __name__ == "__main__":
    unittest.main()
