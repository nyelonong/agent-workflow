from __future__ import annotations

import json
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
        self.assertIn("`golang-how-to`", claude)

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
    def test_render_uses_canonical_source(self) -> None:
        source = ROOT / "policy/core.md"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/render_policy.py"), str(source), "--output", str(ROOT / "policy.md"), "--check"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(source.read_text(encoding="utf-8"), (ROOT / "policy.md").read_text(encoding="utf-8"))

    def test_render_refuses_pi_markers_in_portable_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "core.md"
            source.write_text("rule\n<!-- pi-only:start -->\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/render_policy.py"), str(source)], text=True, capture_output=True
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("Pi-only", result.stderr)

    def test_pi_block_replacement_preserves_unmanaged_content(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        import render_policy

        block = render_policy.pi_block("portable rule\n", "Pi rule\n")
        original = "before\n\n" + block + "after\n"
        updated = render_policy.replace_pi_block(original, block.replace("Pi rule", "new Pi rule"))
        self.assertTrue(updated.startswith("before\n\n"))
        self.assertTrue(updated.endswith("after\n"))
        for broken in ("<!-- personal-workflow:pi:start -->\n", block + block):
            with self.assertRaises(ValueError):
                render_policy.replace_pi_block(broken, block)


class PiInstallerTests(InstallerTests):
    def test_install_is_idempotent_and_preserves_pi_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = home / ".pi/agent/AGENTS.md"
            settings = home / ".pi/agent/settings.json"
            agents.parent.mkdir(parents=True)
            agents.write_text("unrelated rule\n", encoding="utf-8")
            other_skill = home / "elsewhere.md"
            other_skill.write_text("---\nname: elsewhere\n---\n", encoding="utf-8")
            settings.write_text(json.dumps({"theme": "dark", "skills": [str(other_skill)]}) + "\n", encoding="utf-8")
            self.run_installer(home, runtime="pi")
            first = self.snapshot(home)
            self.run_installer(home, runtime="pi")
            self.assertEqual(first, self.snapshot(home))
            self.run_installer(home, "check", runtime="pi")
            self.assertTrue(agents.read_text(encoding="utf-8").startswith("unrelated rule\n"))
            self.assertIn("<!-- personal-workflow:pi:start -->", agents.read_text(encoding="utf-8"))
            data = __import__("json").loads(settings.read_text(encoding="utf-8"))
            self.assertIn(str(ROOT / "skills/workflow"), data["skills"])
            self.assertIn(str(ROOT / "adapters/pi/prompts"), data["prompts"])

    def test_install_preflight_refuses_bad_settings_markers_and_collisions(self) -> None:
        def write(path: Path, text: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        cases = (
            ("settings", lambda home: write(home / ".pi/agent/settings.json", "[]")),
            ("markers", lambda home: write(home / ".pi/agent/AGENTS.md", "<!-- personal-workflow:pi:start -->\n")),
            ("collision", lambda home: write(home / ".pi/agent/skills/workflow/SKILL.md", "---\nname: workflow\n---\n")),
        )
        for name, seed in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                seed(home)
                before = self.snapshot(home)
                result = self.run_installer(home, check=False, runtime="pi")
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(before, self.snapshot(home))

    def test_default_root_renamed_workflow_skill_collision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            skill = home / ".pi/agent/skills/a-different-directory/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: workflow\n---\n", encoding="utf-8")
            # Other default-root resources remain available and are not collisions.
            other_skill = home / ".pi/agent/skills/other/SKILL.md"
            other_skill.parent.mkdir(parents=True)
            other_skill.write_text("---\nname: another-skill\n---\n", encoding="utf-8")
            prompt = home / ".pi/agent/prompts/unrelated.md"
            prompt.parent.mkdir(parents=True)
            prompt.write_text("prompt\n", encoding="utf-8")

            before = self.snapshot(home)
            result = self.run_installer(home, check=False, runtime="pi")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("default-root resource collision", result.stderr)
            self.assertIn(str(skill), result.stderr)
            self.assertEqual(before, self.snapshot(home))

    def test_default_root_noncolliding_resources_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            skill = home / ".pi/agent/skills/a-different-directory/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: another-skill\n---\n", encoding="utf-8")
            prompt = home / ".pi/agent/prompts/unrelated.md"
            prompt.parent.mkdir(parents=True)
            prompt.write_text("prompt\n", encoding="utf-8")

            self.run_installer(home, runtime="pi")
            self.assertEqual("---\nname: another-skill\n---\n", skill.read_text(encoding="utf-8"))
            self.assertEqual("prompt\n", prompt.read_text(encoding="utf-8"))

    def test_check_rejects_missing_entries_and_duplicate_settings_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.run_installer(home, runtime="pi")
            settings = home / ".pi/agent/settings.json"
            data = __import__("json").loads(settings.read_text(encoding="utf-8"))
            data["skills"].append(str(ROOT / "skills/workflow"))
            settings.write_text(__import__("json").dumps(data), encoding="utf-8")
            result = self.run_installer(home, "check", check=False, runtime="pi")
            self.assertNotEqual(0, result.returncode)

    def test_configured_sources_that_shadow_managed_resources_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            external = home / "external"
            nested_skill = external / "skills/nested/SKILL.md"
            nested_skill.parent.mkdir(parents=True)
            nested_skill.write_text("---\nname: workflow\n---\n", encoding="utf-8")
            prompts = external / "prompts"
            prompts.mkdir(parents=True)
            (prompts / "prepush.md").write_text("prompt\n", encoding="utf-8")
            settings = home / ".pi/agent/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"skills": [str(external / "skills")], "prompts": [str(prompts)]}), encoding="utf-8")

            before = self.snapshot(home)
            result = self.run_installer(home, check=False, runtime="pi")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("configured skills source", result.stderr)
            self.assertEqual(before, self.snapshot(home))

    def test_configured_prompt_file_that_shadows_a_managed_command_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            prompt = home / "external/prepush.md"
            prompt.parent.mkdir(parents=True)
            prompt.write_text("prompt\n", encoding="utf-8")
            settings = home / ".pi/agent/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"prompts": [str(prompt)]}), encoding="utf-8")

            result = self.run_installer(home, check=False, runtime="pi")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("configured prompts source", result.stderr)

    def test_configured_source_aliases_and_unverifiable_sources_are_rejected(self) -> None:
        cases = (
            ("canonical alias", {"skills": [str(ROOT / "skills/workflow") + "/"]}),
            ("missing", {"prompts": ["/does/not/exist"]}),
            ("cwd relative", {"skills": ["relative/skills"]}),
        )
        for name, settings_data in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                settings = home / ".pi/agent/settings.json"
                settings.parent.mkdir(parents=True)
                settings.write_text(json.dumps(settings_data), encoding="utf-8")
                before = self.snapshot(home)
                result = self.run_installer(home, check=False, runtime="pi")
                self.assertNotEqual(0, result.returncode)
                self.assertIn("configured", result.stderr)
                self.assertEqual(before, self.snapshot(home))

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            alias = home / "workflow-alias"
            alias.symlink_to(ROOT / "skills/workflow", target_is_directory=True)
            settings = home / ".pi/agent/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"skills": [str(alias)]}), encoding="utf-8")
            result = self.run_installer(home, check=False, runtime="pi")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("source alias", result.stderr)

    def test_pi_block_update_preserves_unmanaged_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = home / ".pi/agent/AGENTS.md"
            agents.parent.mkdir(parents=True)
            prefix = "prefix \t\n"
            suffix = "suffix \t\n\n"
            agents.write_text(
                prefix
                + "<!-- personal-workflow:pi:start -->\nold\n<!-- personal-workflow:pi:end -->\n"
                + suffix,
                encoding="utf-8",
            )
            self.run_installer(home, runtime="pi")
            updated = agents.read_text(encoding="utf-8")
            self.assertTrue(updated.startswith(prefix))
            self.assertTrue(updated.endswith(suffix))

            markerless = "unmanaged trailing whitespace \t"
            agents.write_text(markerless, encoding="utf-8")
            self.run_installer(home, runtime="pi")
            self.assertTrue(agents.read_text(encoding="utf-8").startswith(markerless))

    def test_pi_crlf_splices_preserve_unmanaged_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = home / ".pi/agent/AGENTS.md"
            settings = home / ".pi/agent/settings.json"
            agents.parent.mkdir(parents=True)
            prefix = b"prefix \t\r\n"
            suffix = b"suffix \t\r\n\r\n"
            agents.write_bytes(
                prefix
                + b"<!-- personal-workflow:pi:start -->\r\nold\r\n<!-- personal-workflow:pi:end -->\r\n"
                + suffix
            )
            settings_prefix = b" \t\r\n"
            settings_suffix = b"\r\n \t"
            settings.write_bytes(settings_prefix + b'{"theme": "dark"}' + settings_suffix)

            self.run_installer(home, runtime="pi")
            updated_agents = agents.read_bytes()
            updated_settings = settings.read_bytes()
            self.assertTrue(updated_agents.startswith(prefix))
            self.assertTrue(updated_agents.endswith(suffix))
            self.assertTrue(updated_settings.startswith(settings_prefix))
            self.assertTrue(updated_settings.endswith(settings_suffix))
            self.assertNotIn(b"\n", updated_agents.replace(b"\r\n", b""))
            self.assertNotIn(b"\n", updated_settings.replace(b"\r\n", b""))

            markerless = b"unmanaged trailing whitespace \t\r\n"
            agents.write_bytes(markerless)
            self.run_installer(home, runtime="pi")
            self.assertTrue(agents.read_bytes().startswith(markerless))

    def test_pi_file_symlinks_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            linked = home / "linked"
            linked.mkdir()
            agents_target = linked / "AGENTS.md"
            settings_target = linked / "settings.json"
            agents_target.write_text("unmanaged\n", encoding="utf-8")
            settings_target.write_text('{"theme": "dark"}\n', encoding="utf-8")
            agent_dir = home / ".pi/agent"
            agent_dir.mkdir(parents=True)
            agents = agent_dir / "AGENTS.md"
            settings = agent_dir / "settings.json"
            agents.symlink_to(agents_target)
            settings.symlink_to(settings_target)

            self.run_installer(home, runtime="pi")
            self.assertTrue(agents.is_symlink())
            self.assertTrue(settings.is_symlink())
            self.assertIn("personal-workflow:pi:start", agents_target.read_text(encoding="utf-8"))
            self.assertIn(str(ROOT / "skills/workflow"), json.loads(settings_target.read_text(encoding="utf-8"))["skills"])
            self.run_installer(home, "check", runtime="pi")


class PolicyFreshnessTests(InstallerTests):
    def test_policy_staleness_blocks_consuming_installs_and_checks_before_writes(self) -> None:
        policy = ROOT / "policy.md"
        original = policy.read_bytes()
        try:
            policy.write_text("stale\n", encoding="utf-8")
            for runtime, action in (
                ("agy", "install"),
                ("agy", "check"),
                ("codex", "install"),
                ("codex", "check"),
                ("pi", "install"),
                ("pi", "check"),
                ("claude", "install"),
                ("claude", "check"),
            ):
                with self.subTest(runtime=runtime, action=action), tempfile.TemporaryDirectory() as tmp:
                    home = Path(tmp)
                    before = self.snapshot(home)
                    result = self.run_installer(home, action, check=False, runtime=runtime)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn("stale", result.stderr)
                    self.assertEqual(before, self.snapshot(home))
        finally:
            policy.write_bytes(original)


class ClaudeInstallerTests(InstallerTests):
    def test_install_owns_policy_workflow_and_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            policy = home / ".claude/CLAUDE.md"
            policy.parent.mkdir(parents=True)
            policy.write_text(
                "unrelated rule\n<!-- homie:baseline-golang legacy -->\nold managed rules\n"
                "<!-- agents:global-rules:end -->\nunrelated suffix\n",
                encoding="utf-8",
            )
            policy.chmod(0o640)

            self.run_installer(home, runtime="claude")
            self.run_installer(home, "check", runtime="claude")
            text = policy.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("unrelated rule\n"))
            self.assertIn("unrelated suffix\n", text)
            self.assertNotIn("old managed rules", text)
            self.assertEqual(1, text.count("<!-- personal-workflow:claude:start -->"))
            self.assertIn(f"@{ROOT / 'policy.md'}", text)
            self.assertEqual(0o640, policy.stat().st_mode & 0o777)
            for source, target in (
                (ROOT / "skills/workflow", home / ".claude/skills/workflow"),
                (ROOT / "adapters/claude/agents/architect.md", home / ".claude/agents/architect.md"),
                (ROOT / "adapters/claude/agents/reviewer.md", home / ".claude/agents/reviewer.md"),
            ):
                self.assertTrue(target.is_symlink())
                self.assertEqual(source, Path(os.readlink(target)))

    def test_current_marker_crlf_splice_preserves_unmanaged_bytes_and_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            policy = home / ".claude/CLAUDE.md"
            policy.parent.mkdir(parents=True)
            prefix = b"prefix \t\r\n"
            suffix = b"suffix \t\r\n\r\n"
            policy.write_bytes(
                prefix
                + b"<!-- personal-workflow:claude:start -->\r\nold\r\n<!-- personal-workflow:claude:end -->\r\n"
                + suffix
            )
            policy.chmod(0o640)

            self.run_installer(home, runtime="claude")
            updated = policy.read_bytes()
            self.assertTrue(updated.startswith(prefix))
            self.assertTrue(updated.endswith(suffix))
            self.assertNotIn(b"\n", updated.replace(b"\r\n", b""))
            self.assertEqual(0o640, policy.stat().st_mode & 0o777)
            self.run_installer(home, "check", runtime="claude")

    def test_legacy_marker_crlf_splice_preserves_unmanaged_bytes_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            target = home / "owner/CLAUDE.md"
            target.parent.mkdir(parents=True)
            prefix = b"prefix \t\r\n"
            suffix = b"suffix \t\r\n\r\n"
            target.write_bytes(
                prefix
                + b"<!-- homie:baseline-golang legacy -->\r\nold\r\n<!-- agents:global-rules:end -->\r\n"
                + suffix
            )
            target.chmod(0o640)
            policy = home / ".claude/CLAUDE.md"
            policy.parent.mkdir(parents=True)
            policy.symlink_to(target)

            self.run_installer(home, runtime="claude")
            updated = target.read_bytes()
            self.assertTrue(policy.is_symlink())
            self.assertTrue(updated.startswith(prefix))
            self.assertTrue(updated.endswith(suffix))
            self.assertNotIn(b"\n", updated.replace(b"\r\n", b""))
            self.assertEqual(0o640, target.stat().st_mode & 0o777)
            self.run_installer(home, "check", runtime="claude")

    def test_install_writes_through_policy_symlink_after_complete_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            target = home / "owned/CLAUDE.md"
            target.parent.mkdir(parents=True)
            target.write_text("unrelated rule\n", encoding="utf-8")
            policy = home / ".claude/CLAUDE.md"
            policy.parent.mkdir(parents=True)
            policy.symlink_to(target)
            unmanaged = home / ".claude/skills/workflow"
            unmanaged.mkdir(parents=True)
            (unmanaged / "SKILL.md").write_text("unrelated\n", encoding="utf-8")

            result = self.run_installer(home, check=False, runtime="claude")
            self.assertNotEqual(0, result.returncode)
            self.assertTrue(policy.is_symlink())
            self.assertEqual("unrelated rule\n", target.read_text(encoding="utf-8"))


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
