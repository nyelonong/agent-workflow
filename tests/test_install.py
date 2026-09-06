from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
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
            "exactly one architect",
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

        self.assertIn("exactly one `architect`", workflow)
        self.assertIn("parent implements", workflow)
        self.assertIn("complete uncommitted review packet", workflow)
        self.assertIn("no mandatory subagent review", workflow)
        self.assertIn("at most one fresh `reviewer`", workflow)

    def test_portable_policy_carries_the_hard_engineering_rules(self) -> None:
        policy = (ROOT / "policy.md").read_text(encoding="utf-8").lower()
        claude = (ROOT / "adapters/claude/CLAUDE.md").read_text(encoding="utf-8")

        for required in (
            "start any go work",
            "change only necessary code, callers, interfaces, tests, and documentation",
            "report unrelated defects",
            "comments are rare",
            "async work needs an explicit owner and cancellation path",
            "do not optimize speculatively",
            "## sql and migrations",
            "once applied in a shared, test, staging, or production environment",
            "test observable behavior and stable invariants, not production configuration",
            "postgresql, clickhouse, or redis",
            "integration, smoke, and end-to-end tests are local-only and never committed",
            "use an isolated real database",
            "in-process http server",
            "never request secrets in chat",
            "automatic context compaction is not a task boundary",
            "explain mentioned ids",
            "percent-encoded `file://`",
            "`id.afrani.app.{app_name}`",
        ):
            self.assertIn(required, policy)
        for pi_only in ("ask_decision", "workflowscript", "base_tools", "~/.pi/"):
            self.assertNotIn(pi_only, policy)
        self.assertLessEqual(len(policy), 12_000)
        self.assertLessEqual(len(policy.splitlines()), 200)
        self.assertIn("`go-engineering`", claude)

    def test_native_role_layouts_are_present_and_read_only(self) -> None:
        paths = (
            ROOT / "adapters/claude/agents/architect.md",
            ROOT / "adapters/claude/agents/reviewer.md",
            ROOT / "adapters/agy/agents/architect/agent.md",
            ROOT / "adapters/agy/agents/reviewer/agent.md",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("read-only", text)
            self.assertIn("do not edit", text)


class InstallerTests(unittest.TestCase):
    def run_installer(self, home: Path, action: str = "install", check: bool = True, runtime: str = "agy") -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(INSTALLER), "--home", str(home), action, runtime],
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
            self.assertTrue((home / ".gemini/config/agents/architect/agent.md").is_file())
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


class RenderPolicyTests(unittest.TestCase):
    PI_TEXT = (
        "## Sync\n\nFirst rule line\nwraps here.\n\n<!-- pi-only:start -->\nIn Pi use `ask_decision`.\n<!-- pi-only:end -->\n\n"
        "## Workflow\n\nSecond rule.\n\n<!-- pi-only:start -->\n## Pi ownership\n\nKeep `BASE_TOOLS` lean.\n<!-- pi-only:end -->\n"
    )

    def render(self, text: str, *args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "AGENTS.md"
            source.write_text(text, encoding="utf-8")
            output = Path(tmp) / "policy.md"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/render_policy.py"), str(source), "--output", str(output), *args],
                text=True, capture_output=True,
            )
            result.rendered = output.read_text(encoding="utf-8") if output.exists() else None  # type: ignore[attr-defined]
            return result

    def test_render_strips_pi_only_blocks_and_unwraps_paragraphs(self) -> None:
        result = self.render(self.PI_TEXT)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "# Personal engineering workflow\n\n## Sync\n\nFirst rule line wraps here.\n\n## Workflow\n\nSecond rule.\n",
            result.rendered,
        )

    def test_render_refuses_unbalanced_markers(self) -> None:
        for broken in (self.PI_TEXT.replace("<!-- pi-only:end -->\n\n## Workflow", "## Workflow", 1), "<!-- pi-only:end -->\n", "rule <!-- pi-only:start --> inline\n"):
            result = self.render(broken)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("render_policy:", result.stderr)

    def test_check_detects_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "AGENTS.md"
            source.write_text(self.PI_TEXT, encoding="utf-8")
            output = Path(tmp) / "policy.md"
            cmd = [sys.executable, str(ROOT / "scripts/render_policy.py"), str(source), "--output", str(output)]
            self.assertNotEqual(0, subprocess.run(cmd + ["--check"], capture_output=True).returncode, "missing output is stale")
            subprocess.run(cmd, check=True)
            self.assertEqual(0, subprocess.run(cmd + ["--check"], capture_output=True).returncode)
            source.write_text(self.PI_TEXT + "\nThird rule.\n", encoding="utf-8")
            self.assertNotEqual(0, subprocess.run(cmd + ["--check"], capture_output=True).returncode)

    def test_committed_policy_is_current_with_the_live_pi_file(self) -> None:
        source = Path.home() / ".pi/agent/AGENTS.md"
        if not source.is_file():
            self.skipTest("Pi is not installed here")
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/render_policy.py"), str(source), "--check"], text=True, capture_output=True
        )
        self.assertEqual(0, result.returncode, result.stderr)


class PiInstallerTests(InstallerTests):
    def test_check_and_render_use_the_home_pi_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            missing = self.run_installer(home, "check", check=False, runtime="pi")
            self.assertNotEqual(0, missing.returncode)
            self.assertIn("missing", missing.stderr)
            install = self.run_installer(home, "install", check=False, runtime="pi")
            self.assertNotEqual(0, install.returncode, "pi has no install action")
            render_not_pi = self.run_installer(home, "render", check=False, runtime="agy")
            self.assertNotEqual(0, render_not_pi.returncode)


class ClaudeInstallerTests(InstallerTests):
    def test_install_links_pi_go_skill_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir()
            self.run_installer(home, runtime="claude")
            first = self.snapshot(home)
            self.run_installer(home, runtime="claude")
            self.assertEqual(first, self.snapshot(home))
            self.run_installer(home, "check", runtime="claude")

            link = home / ".claude/skills/go-engineering"
            self.assertTrue(link.is_symlink())
            self.assertEqual(home / ".pi/agent/skills/go-engineering", Path(os.readlink(link)))

    def test_install_refuses_a_go_skill_link_that_points_elsewhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            link = home / ".claude/skills/go-engineering"
            link.parent.mkdir(parents=True)
            link.symlink_to(home / "elsewhere")
            result = self.run_installer(home, check=False, runtime="claude")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("refusing", result.stderr)
            self.assertFalse((home / ".claude/prewalk.json").exists(), "preflight runs before any link is written")


class CodexInstallerTests(InstallerTests):
    RTK_LINE = "@/Users/zaki/.codex/RTK.md\n"

    def seed(self, home: Path) -> Path:
        agents = home / ".codex/AGENTS.md"
        agents.parent.mkdir(parents=True)
        agents.write_text(self.RTK_LINE, encoding="utf-8")
        agents.chmod(0o640)
        return agents

    def test_install_appends_one_block_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = self.seed(home)
            self.run_installer(home, runtime="codex")
            first = self.snapshot(home)
            self.run_installer(home, runtime="codex")
            self.assertEqual(first, self.snapshot(home))
            self.run_installer(home, "check", runtime="codex")

            text = agents.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(self.RTK_LINE), "the existing rtk line is preserved")
            self.assertEqual(1, text.count("<!-- personal-workflow:codex:start -->"))
            self.assertIn("## Workflow", text, "the policy is rendered inline")
            self.assertIn("Fresh independent review is mandatory only when", text)
            self.assertIn("# Codex adapter", text)
            self.assertNotIn("@" + str(ROOT / "policy.md"), text, "no include directive for Codex")
            self.assertLess(len(text.encode("utf-8")), 24_576, "room under the 32 KiB instruction cap")
            self.assertEqual(0o640, agents.stat().st_mode & 0o777)

            for name in ("architect", "reviewer"):
                agent = home / f".codex/agents/{name}.toml"
                self.assertEqual("# personal-workflow managed", agent.read_text().splitlines()[0])
                self.assertIn('sandbox_mode = "read-only"', agent.read_text())
            link = home / ".codex/skills/workflow"
            self.assertTrue(link.is_symlink())
            self.assertEqual(ROOT / "skills/workflow", Path(os.readlink(link)))

    def test_install_refuses_unmanaged_agent_file_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = self.seed(home)
            mine = home / ".codex/agents/architect.toml"
            mine.parent.mkdir(parents=True)
            mine.write_text('name = "architect"\n', encoding="utf-8")
            result = self.run_installer(home, check=False, runtime="codex")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("refusing", result.stderr)
            self.assertEqual('name = "architect"\n', mine.read_text(encoding="utf-8"))
            self.assertEqual(self.RTK_LINE, agents.read_text(encoding="utf-8"), "preflight runs before the block is written")

    def test_check_fails_when_block_is_stale_or_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = self.seed(home)
            missing = self.run_installer(home, "check", check=False, runtime="codex")
            self.assertNotEqual(0, missing.returncode)
            self.run_installer(home, runtime="codex")
            text = agents.read_text(encoding="utf-8").replace("# Codex adapter", "# Old adapter")
            agents.write_text(text, encoding="utf-8")
            stale = self.run_installer(home, "check", check=False, runtime="codex")
            self.assertNotEqual(0, stale.returncode)
            self.assertIn("differs", stale.stderr)
            self.run_installer(home, runtime="codex")
            self.run_installer(home, "check", runtime="codex")
            self.assertEqual(1, agents.read_text().count("<!-- personal-workflow:codex:start -->"), "converged, not duplicated")

    def test_agent_files_are_valid_toml_and_read_only(self) -> None:
        import tomllib

        for name in ("architect", "reviewer"):
            data = tomllib.loads((ROOT / f"adapters/codex/agents/{name}.toml").read_text(encoding="utf-8"))
            self.assertEqual(name, data["name"])
            self.assertEqual("read-only", data["sandbox_mode"])
            self.assertIn("Do not edit, write, stage, commit", data["developer_instructions"])


if __name__ == "__main__":
    unittest.main()
