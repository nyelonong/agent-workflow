from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"


class WorkflowContractTests(unittest.TestCase):
    def test_portable_policy_matches_the_pi_experience(self) -> None:
        policy = (ROOT / "policy.md").read_text(encoding="utf-8")
        workflow = (ROOT / "skills/workflow/SKILL.md").read_text(encoding="utf-8")
        lowered = policy.lower()

        for required in (
            "production implementation requires explicit approval",
            "clear, routine single change",
            "exactly one oracle",
            "one complete uncommitted review packet",
            "fresh independent review is mandatory only when",
            "application runtime behavior",
            "data integrity",
            "security, privacy, authentication, or authorization",
            "concurrency, asynchronous ownership, cancellation, or resource lifetime",
            "external systems",
            "operational authority or safety",
            "documentation, skills, prompts, and configuration prose",
            "remote write",
        ):
            self.assertIn(required, lowered)
        self.assertNotIn("no production code without a failing test first", lowered)
        self.assertNotIn("routing:", lowered)

        self.assertIn("exactly one `oracle`", workflow)
        self.assertIn("parent implements", workflow)
        self.assertIn("complete uncommitted review packet", workflow)
        self.assertIn("no mandatory subagent review", workflow)
        self.assertIn("at most one fresh `reviewer`", workflow)

    def test_native_role_layouts_are_present_and_read_only(self) -> None:
        paths = (
            ROOT / "adapters/claude/agents/oracle.md",
            ROOT / "adapters/claude/agents/reviewer.md",
            ROOT / "adapters/agy/agents/oracle/agent.md",
            ROOT / "adapters/agy/agents/reviewer/agent.md",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("read-only", text)
            self.assertIn("do not edit", text)


class InstallerTests(unittest.TestCase):
    def run_installer(self, home: Path, action: str = "install", check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(INSTALLER), "--home", str(home), action, "agy"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "HOME": str(home)},
        )
        if check and result.returncode != 0:
            self.fail(f"installer failed: {result.stdout}\n{result.stderr}")
        return result

    @staticmethod
    def snapshot(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def test_install_is_idempotent_and_checkable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.run_installer(home)
            first = self.snapshot(home)
            self.run_installer(home)
            self.assertEqual(first, self.snapshot(home))
            self.run_installer(home, "check")

            gemini = (home / ".gemini/GEMINI.md").read_text(encoding="utf-8")
            self.assertIn(f"@{ROOT / 'policy.md'}", gemini)
            self.assertTrue((home / ".gemini/config/skills/workflow/SKILL.md").is_file())
            self.assertTrue((home / ".gemini/config/agents/oracle/agent.md").is_file())
            self.assertTrue((home / ".gemini/config/agents/reviewer/agent.md").is_file())

    def test_install_preserves_unrelated_gemini_content_and_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            gemini = home / ".gemini/GEMINI.md"
            gemini.parent.mkdir(parents=True)
            gemini.write_text("unrelated rule\n", encoding="utf-8")
            gemini.chmod(0o640)

            self.run_installer(home)
            text = gemini.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("unrelated rule\n"))
            self.assertEqual(0o640, gemini.stat().st_mode & 0o777)

    def test_install_refuses_to_replace_an_unmanaged_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            target = home / ".gemini/config/skills/workflow"
            target.mkdir(parents=True)
            existing = target / "SKILL.md"
            existing.write_text("unrelated\n", encoding="utf-8")

            result = self.run_installer(home, check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertEqual("unrelated\n", existing.read_text(encoding="utf-8"))

    def test_install_removes_an_old_galdr_only_agents_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = home / ".gemini/AGENTS.md"
            agents.parent.mkdir(parents=True)
            agents.write_text("<!-- galdr:start -->\nold rules\n<!-- galdr:end -->\n", encoding="utf-8")

            self.run_installer(home)
            self.assertFalse(agents.exists())

    def test_install_preserves_content_around_an_old_galdr_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = home / ".gemini/AGENTS.md"
            agents.parent.mkdir(parents=True)
            agents.write_text(
                "before\n<!-- galdr:start -->\nold rules\n<!-- galdr:end -->\nafter\n",
                encoding="utf-8",
            )

            self.run_installer(home)
            self.assertEqual("before\nafter\n", agents.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
