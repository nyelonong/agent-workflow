from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLAUDE_BOOTSTRAP = Path.home() / "Projects/personal/claude-config/bootstrap.sh"
INSTALLER = ROOT / "install.sh"


class WorkflowContractTests(unittest.TestCase):

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


class CodexInstallerTests(InstallerTests):
    RTK_LINE = "@/home/example/.codex/RTK.md\n"

    def seed(self, home: Path) -> Path:
        go = home / ".pi/agent/skills/go-engineering"
        (go / "references").mkdir(parents=True)
        (go / "SKILL.md").write_text("---\nname: go-engineering\ndescription: Go guidance\n---\n[Concurrency](references/concurrency.md)\n")
        (go / "references/concurrency.md").write_text("Preserve cancellation.\n")
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
            for name in (
                "plan", "implement", "investigate", "review", "verify", "finish",
                "no-comments", "domain-language", "plan-review", "interactive-review",
                "prepush", "resume-plan", "project", "feature-journey", "research",
                "repo-fit", "retry", "task-boundary", "task-review", "go-engineering",
            ):
                self.assertTrue((home / f".codex/skills/{name}/SKILL.md").is_file(), name)
            self.assertEqual(
                "Preserve cancellation.\n",
                (home / ".codex/skills/go-engineering/references/concurrency.md").read_text(),
            )

    def test_migrates_only_the_known_workflow_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.seed(home)
            workflow = home / ".codex/skills/workflow"
            workflow.parent.mkdir()
            workflow.symlink_to(ROOT / "adapters/codex/skills/workflow")
            unrelated = home / ".codex/config.toml"
            unrelated.write_text('model = "existing-model"\n')
            self.run_installer(home, runtime="codex")
            self.assertEqual(ROOT / "skills/workflow", Path(os.readlink(workflow)))
            self.assertEqual('model = "existing-model"\n', unrelated.read_text())

    def test_retires_only_its_owned_shape_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.seed(home)
            self.run_installer(home, runtime="codex")
            retired = home / ".codex/skills/shape"
            retired.symlink_to(ROOT / "adapters/codex/skills/shape")
            result = self.run_installer(home, "check", runtime="codex", check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("retired managed skill", result.stderr)
            self.run_installer(home, runtime="codex")
            self.assertFalse(retired.is_symlink())
            self.run_installer(home, "check", runtime="codex")
            first = self.snapshot(home)
            self.run_installer(home, runtime="codex")
            self.assertEqual(first, self.snapshot(home))

    def test_preserves_unowned_shape_paths(self) -> None:
        for kind in ("directory", "foreign-link", "broken-link"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                self.seed(home)
                retired = home / ".codex/skills/shape"
                retired.parent.mkdir()
                if kind == "directory":
                    retired.mkdir()
                    (retired / "SKILL.md").write_text("User-owned design guidance\n")
                else:
                    foreign = home / "foreign"
                    if kind == "foreign-link":
                        foreign.mkdir()
                        (foreign / "SKILL.md").write_text("User-owned design guidance\n")
                    retired.symlink_to(foreign)
                self.run_installer(home, runtime="codex")
                self.run_installer(home, "check", runtime="codex")
                if kind == "directory":
                    self.assertEqual("User-owned design guidance\n", (retired / "SKILL.md").read_text())
                else:
                    self.assertEqual(foreign, Path(os.readlink(retired)))

    def test_workflow_collisions_fail_before_any_write(self) -> None:
        for kind in ("directory", "foreign-link", "broken-link"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                self.seed(home)
                target = home / ".codex/skills/workflow"
                target.parent.mkdir()
                if kind == "directory":
                    target.mkdir()
                    (target / "SKILL.md").write_text("User workflow\n")
                else:
                    foreign = home / "foreign"
                    if kind == "foreign-link":
                        foreign.mkdir()
                    target.symlink_to(foreign)
                before = self.snapshot(home)
                result = self.run_installer(home, runtime="codex", check=False)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("refusing", result.stderr)
                self.assertEqual(before, self.snapshot(home))

    def test_skill_collisions_fail_before_any_write(self) -> None:
        for kind in ("directory", "foreign-link", "broken-link"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                agents = self.seed(home)
                workflow = home / ".codex/skills/workflow"
                workflow.parent.mkdir()
                workflow.symlink_to(ROOT / "skills/workflow")
                target = home / ".codex/skills/verify"
                if kind == "directory":
                    target.mkdir()
                    (target / "SKILL.md").write_text("User skill\n")
                else:
                    foreign = home / "foreign"
                    if kind == "foreign-link":
                        foreign.mkdir()
                    target.symlink_to(foreign)
                before = self.snapshot(home)
                result = self.run_installer(home, runtime="codex", check=False)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("refusing", result.stderr)
                self.assertEqual(before, self.snapshot(home))
                self.assertEqual(ROOT / "skills/workflow", Path(os.readlink(workflow)))
                self.assertEqual(self.RTK_LINE, agents.read_text())
                self.assertFalse((home / ".codex/agents").exists())

    def test_missing_go_source_fails_install_and_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.seed(home)
            source = home / ".pi/agent/skills/go-engineering/SKILL.md"
            contents = source.read_text()
            source.unlink()
            before = self.snapshot(home)
            result = self.run_installer(home, runtime="codex", check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("missing", result.stderr)
            self.assertEqual(before, self.snapshot(home))
            source.write_text(contents)
            self.run_installer(home, runtime="codex")
            source.unlink()
            result = self.run_installer(home, "check", runtime="codex", check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("missing", result.stderr)

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



class OmpInstallerTests(InstallerTests):
    def seed(self, home: Path) -> Path:
        agents = home / ".omp/agent/AGENTS.md"
        agents.parent.mkdir(parents=True)
        agents.write_text("user rules\n", encoding="utf-8")
        agents.chmod(0o640)
        return agents

    def test_install_appends_one_block_and_links_the_task_review_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = self.seed(home)
            self.run_installer(home, runtime="omp")
            first = self.snapshot(home)
            self.run_installer(home, runtime="omp")
            self.assertEqual(first, self.snapshot(home))
            self.run_installer(home, "check", runtime="omp")

            text = agents.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("user rules\n"), "existing rules are preserved")
            self.assertEqual(1, text.count("<!-- personal-workflow:omp:start -->"))
            self.assertIn(f"@{ROOT / 'policy.md'}", text, "the policy is imported by path")
            self.assertIn("# omp adapter", text)
            self.assertEqual(0o640, agents.stat().st_mode & 0o777)
            link = home / ".agents/skills/task-review"
            self.assertTrue(link.is_symlink())
            self.assertEqual(ROOT / "skills/task-review", Path(os.readlink(link)))

    def test_check_fails_when_the_block_or_the_link_is_stale_or_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = self.seed(home)
            missing = self.run_installer(home, "check", check=False, runtime="omp")
            self.assertNotEqual(0, missing.returncode)
            self.run_installer(home, runtime="omp")
            agents.write_text(agents.read_text(encoding="utf-8").replace("# omp adapter", "# Old adapter"))
            stale = self.run_installer(home, "check", check=False, runtime="omp")
            self.assertNotEqual(0, stale.returncode)
            self.assertIn("differs", stale.stderr)
            self.run_installer(home, runtime="omp")
            (home / ".agents/skills/task-review").unlink()
            unlinked = self.run_installer(home, "check", check=False, runtime="omp")
            self.assertNotEqual(0, unlinked.returncode)
            self.assertIn("missing or points elsewhere", unlinked.stderr)

    def test_install_refuses_a_foreign_skill_link_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = self.seed(home)
            foreign = home / "elsewhere"
            foreign.mkdir()
            link = home / ".agents/skills/task-review"
            link.parent.mkdir(parents=True)
            link.symlink_to(foreign)

            result = self.run_installer(home, check=False, runtime="omp")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("refusing", result.stderr)
            self.assertEqual("user rules\n", agents.read_text(encoding="utf-8"), "preflight runs before the block is written")


class TaskReviewWiringTests(unittest.TestCase):
    def run_installer(self, home: Path, runtime: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(INSTALLER), "--home", str(home), "install", runtime],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "HOME": str(home)},
        )
        if result.returncode != 0:
            self.fail(f"installer failed: {result.stdout}\n{result.stderr}")
        return result


    def test_the_codex_copy_names_its_own_invocation_and_decision_flow(self) -> None:
        codex = (ROOT / "adapters/codex/skills/task-review/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: task-review", codex)
        self.assertIn("$task-review", codex)
        self.assertIn("plain numbered question", codex)
        self.assertIn("RDG_CONTROL_COMMAND", codex)
        self.assertNotIn("rdg --review", codex, "the gate owns the reviewer invocation")

    def test_agy_codex_and_omp_install_the_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            go = home / ".pi/agent/skills/go-engineering"
            go.mkdir(parents=True)
            (go / "SKILL.md").write_text("---\nname: go-engineering\n---\nGo\n", encoding="utf-8")
            for runtime in ("agy", "codex", "omp"):
                with self.subTest(runtime=runtime):
                    self.run_installer(home, runtime)
            self.assertTrue((home / ".gemini/config/skills/task-review/SKILL.md").is_file())
            self.assertEqual(
                ROOT / "skills/task-review",
                Path(os.readlink(home / ".agents/skills/task-review")),
            )
            self.assertEqual(
                ROOT / "adapters/codex/skills/task-review",
                Path(os.readlink(home / ".codex/skills/task-review")),
            )

    @unittest.skipUnless(CLAUDE_BOOTSTRAP.is_file(), "claude-config is not checked out here")
    def test_claude_bootstrap_links_the_skill(self) -> None:
        bootstrap = CLAUDE_BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn(
            "$agent_workflow/skills/task-review|$claude_home/skills/task-review",
            bootstrap,
        )


if __name__ == "__main__":
    unittest.main()


class EveryRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        base = Path(directory.name).resolve()
        self.package = base / "package"
        self.package.mkdir()
        for name in ("install.sh", "policy.md"):
            shutil.copy2(ROOT / name, self.package / name)
        for name in ("scripts", "skills", "adapters"):
            shutil.copytree(
                ROOT / name, self.package / name, symlinks=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        self.home = base / "home"
        go = self.home / ".pi/agent/skills/go-engineering"
        go.mkdir(parents=True)
        (go / "SKILL.md").write_text("# go\n", encoding="utf-8")
        (self.home / ".pi/agent/AGENTS.md").write_text(RenderPolicyTests.PI_TEXT, encoding="utf-8")

    def run_installer(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.package / "install.sh"), "--home", str(self.home), *args],
            cwd=self.package,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "HOME": str(self.home), "PYTHONDONTWRITEBYTECODE": "1"},
        )

    @staticmethod
    def snapshot(root: Path) -> dict[str, tuple[int, bytes | str | None]]:
        result = {}
        for path in (root, *sorted(root.rglob("*"))):
            mode = path.lstat().st_mode
            content = os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None
            result[str(path.relative_to(root))] = (mode, content)
        return result

    def install_all(self) -> None:
        result = self.run_installer("install-all")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def check_without_writes(self) -> subprocess.CompletedProcess[str]:
        before = self.snapshot(self.package), self.snapshot(self.home)
        result = self.run_installer("check-all")
        self.assertEqual(before, (self.snapshot(self.package), self.snapshot(self.home)))
        return result

    def test_one_command_installs_every_runtime(self) -> None:
        result = self.run_installer("install-all")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        for runtime in ("codex", "claude", "agy", "omp"):
            self.assertIn(f"{runtime} personal workflow: install ok", result.stdout)
        self.assertIn("pi personal workflow: render ok", result.stdout)

    def test_check_all_succeeds_without_writes(self) -> None:
        self.install_all()
        result = self.check_without_writes()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_check_all_rejects_stale_policy_without_writes(self) -> None:
        self.install_all()
        policy = self.package / "policy.md"
        policy.write_text(policy.read_text(encoding="utf-8") + "\nstale\n", encoding="utf-8")
        policy.chmod(0o640)
        result = self.check_without_writes()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("stale", result.stderr)

    def test_check_all_rejects_missing_policy_without_writes(self) -> None:
        self.install_all()
        (self.package / "policy.md").unlink()
        result = self.check_without_writes()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("stale", result.stderr)

    def test_check_all_rejects_missing_pi_source_without_writes(self) -> None:
        self.install_all()
        (self.home / ".pi/agent/AGENTS.md").unlink()
        result = self.check_without_writes()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Pi instructions are missing", result.stderr)

    def test_check_all_fails_when_a_runtime_is_behind(self) -> None:
        self.install_all()
        stale = self.home / ".gemini/config/skills/task-review/SKILL.md"
        self.assertTrue(stale.is_file(), "agy holds a copy, so it can be edited by hand")
        stale.write_text(stale.read_text(encoding="utf-8") + "\nstale\n", encoding="utf-8")
        result = self.check_without_writes()
        self.assertNotEqual(0, result.returncode, "a runtime that has drifted must fail the check")

    def test_install_all_renders_changed_pi_policy(self) -> None:
        self.install_all()
        source = self.home / ".pi/agent/AGENTS.md"
        source.write_text(source.read_text(encoding="utf-8") + "\nThird rule.\n", encoding="utf-8")
        self.install_all()
        self.assertIn("Third rule.", (self.package / "policy.md").read_text(encoding="utf-8"))
        result = self.check_without_writes()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

