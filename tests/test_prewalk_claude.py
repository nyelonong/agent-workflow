from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts/prewalk_hook.py"
RENDER = ROOT / "scripts/prewalk_render.py"
WRAPPER = ROOT / "adapters/claude/bin/claude-prewalk"
INSTALLER = ROOT / "install.sh"
FIXTURE = ROOT / "tests/fixtures/claude-phase1.jsonl"

FAKE_CLAUDE = r'''#!/bin/sh
# Fake claude: logs argv per phase; phase 1 replays the fixture and emulates
# the hooks having recorded the markers named in FAKE_CLAUDE_MARKERS.
printf '%s\n' "$*" >> "$FAKE_CLAUDE_LOG"
case " $* " in
  *" -p "*)
    [ -z "${FAKE_CLAUDE_FAIL:-}" ] || { echo "auth failed" >&2; exit 1; }
    [ -z "${CLAUDE_PREWALK_STATE:-}" ] || printf '%s' "$FAKE_CLAUDE_MARKERS" >> "$CLAUDE_PREWALK_STATE"
    printf '%s\n' "$PWD" >> "$FAKE_CLAUDE_LOG"
    cat "$FAKE_CLAUDE_FIXTURE"
    ;;
  *) printf 'interactive:%s\n' "${CLAUDE_PREWALK_STATE:-unset}" >> "$FAKE_CLAUDE_LOG" ;;
esac
'''


def clean_env(extra: dict[str, str]) -> dict[str, str]:
    base = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_PREWALK_")}
    return {**base, **extra}


def run_hook(event: dict | None, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK), "claude"],
        input=json.dumps(event) if event is not None else "",
        text=True,
        capture_output=True,
        env=clean_env(env),
    )


class HookTests(unittest.TestCase):
    def test_hook_is_inert_without_the_state_variable(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOK), "claude"],
            input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit"}),
            text=True,
            capture_output=True,
            env=clean_env({}),
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)

    def test_first_edit_then_deny(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            env = {"CLAUDE_PREWALK_STATE": str(state)}

            run_hook({"hook_event_name": "PostToolUse", "tool_name": "TodoWrite"}, env)
            self.assertEqual({"todo"}, set(state.read_text().split()), "a todo tool is still recorded when present")

            allowed = run_hook({"hook_event_name": "PreToolUse", "tool_name": "Write"}, env)
            self.assertEqual("", allowed.stdout, "the first edit is allowed through")

            run_hook({"hook_event_name": "PostToolUse", "tool_name": "Write"}, env)
            self.assertEqual({"todo", "edit"}, set(state.read_text().split()))

            denied = run_hook({"hook_event_name": "PreToolUse", "tool_name": "Edit"}, env)
            self.assertEqual(0, denied.returncode)
            output = json.loads(denied.stdout)["hookSpecificOutput"]
            self.assertEqual("PreToolUse", output["hookEventName"])
            self.assertEqual("deny", output["permissionDecision"])
            self.assertIn("Prewalk handoff", output["permissionDecisionReason"])

            bash = run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash"}, env)
            self.assertEqual("", bash.stdout, "non-edit tools are never denied")

    def test_todo_gate_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            env = {"CLAUDE_PREWALK_STATE": str(state)}
            run_hook({"hook_event_name": "PostToolUse", "tool_name": "MultiEdit"}, env)
            self.assertEqual({"edit"}, set(state.read_text().split()), "no todo tool exists in this Claude build")

            gated = Path(tmp) / "gated"
            env = {"CLAUDE_PREWALK_STATE": str(gated), "CLAUDE_PREWALK_REQUIRE_TODO": "1"}
            run_hook({"hook_event_name": "PostToolUse", "tool_name": "MultiEdit"}, env)
            self.assertFalse(gated.exists(), "with the gate on, an edit before any todo is not recorded")
            run_hook({"hook_event_name": "PostToolUse", "tool_name": "TodoWrite"}, env)
            run_hook({"hook_event_name": "PostToolUse", "tool_name": "MultiEdit"}, env)
            self.assertEqual({"todo", "edit"}, set(gated.read_text().split()))

    def test_malformed_input_and_unknown_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {"CLAUDE_PREWALK_STATE": str(Path(tmp) / "state")}
            for payload in ("not json", "[1, 2]"):
                result = subprocess.run(
                    [sys.executable, str(HOOK), "claude"], input=payload, text=True, capture_output=True, env=clean_env(env)
                )
                self.assertEqual(0, result.returncode)
                self.assertEqual("", result.stdout)
            unwritable = run_hook(
                {"hook_event_name": "PostToolUse", "tool_name": "Edit"},
                {"CLAUDE_PREWALK_STATE": str(Path(tmp) / "missing-dir" / "state")},
            )
            self.assertEqual(0, unwritable.returncode, "an unwritable state file fails open")
            self.assertEqual("", unwritable.stdout)
        unknown = subprocess.run([sys.executable, str(HOOK), "codex"], input="{}", text=True, capture_output=True)
        self.assertEqual(64, unknown.returncode)


class RenderTests(unittest.TestCase):
    def test_renders_model_text_tools_and_result(self) -> None:
        result = subprocess.run([sys.executable, str(RENDER)], input=FIXTURE.read_text(), text=True, capture_output=True)
        self.assertEqual(0, result.returncode)
        self.assertIn("[init] model claude-fable-5-1", result.stdout)
        self.assertIn("Plan: add greet() and its test.", result.stdout)
        self.assertIn("> TodoWrite", result.stdout)
        self.assertIn("> Write: greet.py", result.stdout)
        self.assertIn("[result] success turns 3 cost $0.0421", result.stdout)


class WrapperTests(unittest.TestCase):
    def run_wrapper(self, markers: str, *args: str, fail_phase1: bool = False, cwd_args: bool = False, config: str | None = None) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "claude"
            fake.write_text(FAKE_CLAUDE)
            fake.chmod(0o755)
            log = Path(tmp) / "argv.log"
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "FAKE_CLAUDE_LOG": str(log),
                "FAKE_CLAUDE_FIXTURE": str(FIXTURE),
                "FAKE_CLAUDE_MARKERS": markers,
            }
            if fail_phase1:
                env["FAKE_CLAUDE_FAIL"] = "1"
            for key in [k for k in env if k.startswith("CLAUDE_PREWALK_")]:
                env.pop(key)
            env["CLAUDE_CONFIG_DIR"] = str(Path(tmp) / "claude-home")
            if config is not None:
                (Path(tmp) / "claude-home").mkdir(parents=True)
                (Path(tmp) / "claude-home/prewalk.json").write_text(config)
            work = Path(tmp) / "work"
            work.mkdir()
            if cwd_args:
                args = ("--cwd", str(work), *args)
            result = subprocess.run([str(WRAPPER), *args], text=True, capture_output=True, env=env, cwd=tmp)
            lines = log.read_text().splitlines() if log.exists() else []
            return result, lines

    def test_phase_one_then_resume_on_the_cheap_model(self) -> None:
        result, lines = self.run_wrapper("todo\nedit\n", "--", "add greet")
        self.assertEqual(0, result.returncode, result.stderr)
        phase1, _cwd, phase2, interactive = lines
        self.assertTrue(phase1.startswith("-p add greet --session-id "), phase1)
        session = phase1.split("--session-id ")[1].split()[0]
        self.assertRegex(session, r"^[0-9a-f-]{36}$")
        for flag in ("--model fable", "--append-system-prompt Prewalk phase 1.", "--output-format stream-json", "--verbose"):
            self.assertIn(flag, phase1)
        self.assertIn("Plan: add greet() and its test.", result.stdout, "phase 1 stream is rendered")
        self.assertIn(f"--resume {session} --model sonnet --append-system-prompt Prewalk phase 2.", phase2)
        self.assertIn("Continue from the todo list.", phase2)
        self.assertEqual("interactive:unset", interactive, "phase 2 must not carry the hook variable")
        self.assertIn("phase 2 on sonnet", result.stderr)

    def test_no_edit_resumes_on_the_strong_model(self) -> None:
        result, lines = self.run_wrapper("todo\n", "--from", "opus", "--into", "haiku", "--", "explain", "the", "module")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("-p explain the module --session-id", lines[0])
        self.assertIn("--model opus", lines[0])
        self.assertIn("--model opus --append-system-prompt Prewalk phase 2.", lines[2])
        self.assertNotIn("--model haiku", lines[2])
        self.assertIn("no edit recorded", result.stderr)

    def test_permission_mode_passthrough_and_usage(self) -> None:
        result, lines = self.run_wrapper("", "--permission-mode", "acceptEdits", "--", "task")
        self.assertIn("--permission-mode acceptEdits", lines[0])
        usage, _ = self.run_wrapper("", "--from")
        self.assertEqual(64, usage.returncode)
        self.assertIn("usage:", usage.stderr)

    def test_task_text_is_passed_verbatim(self) -> None:
        task = "fix \"quoted\" $HOME  double  spaces 'single'"
        _, lines = self.run_wrapper("edit\n", "--", task)
        self.assertTrue(lines[0].startswith(f"-p {task} --session-id "), lines[0])

    def test_cwd_flag_runs_both_phases_in_that_directory(self) -> None:
        _, lines = self.run_wrapper("edit\n", "--", "task", cwd_args=True)
        self.assertTrue(lines[1].endswith("/work"), lines[1])

    def test_config_file_sets_defaults_and_flags_win(self) -> None:
        config = json.dumps({"from": "opus", "into": "haiku", "permissionMode": "acceptEdits"})
        _, lines = self.run_wrapper("edit\n", "--", "task", config=config)
        self.assertIn("--model opus", lines[0])
        self.assertIn("--permission-mode acceptEdits", lines[0])
        self.assertIn("--model haiku --append-system-prompt", lines[2])

        _, lines = self.run_wrapper("edit\n", "--into", "sonnet", "--", "task", config=config)
        self.assertIn("--model opus", lines[0], "file default still applies to the flag not given")
        self.assertIn("--model sonnet --append-system-prompt", lines[2], "the flag wins")

        result, lines = self.run_wrapper("edit\n", "--", "task", config="{broken")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(1, result.stderr.count("not valid JSON"), "warned once")
        self.assertIn("--model fable", lines[0], "shipped defaults on invalid config")

    def test_phase_one_failure_does_not_resume(self) -> None:
        result, lines = self.run_wrapper("", "--", "task", fail_phase1=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("did not start", result.stderr)
        self.assertEqual(1, len(lines), "no --resume after a failed phase 1")


class ConfigHelperTests(unittest.TestCase):
    def run_helper(self, home: Path, *keys: str, runtime: str = "claude", env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/prewalk_config.py"), runtime, *keys],
            text=True, capture_output=True, env={**os.environ, "HOME": str(home), "CLAUDE_CONFIG_DIR": "", **(env or {})},
        )

    def test_helper_reads_each_runtime_from_its_own_home_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir()
            (home / ".claude/prewalk.json").write_text(json.dumps({"from": "opus", "nested": {"x": 1}, "flag": True}))
            self.assertEqual("from=opus\nflag=true\n", self.run_helper(home, "from", "into", "nested", "flag").stdout)
            self.assertEqual("", self.run_helper(home, "into").stdout)
            self.assertEqual("", self.run_helper(home, "from", runtime="agy").stdout, "agy does not read the claude file")
            (home / ".gemini").mkdir()
            (home / ".gemini/prewalk.json").write_text(json.dumps({"from": "gemini-3.1-pro-high"}))
            self.assertEqual("from=gemini-3.1-pro-high\n", self.run_helper(home, "from", runtime="agy").stdout)
            elsewhere = home / "elsewhere"
            elsewhere.mkdir()
            (elsewhere / "prewalk.json").write_text(json.dumps({"from": "haiku"}))
            self.assertEqual("from=haiku\n", self.run_helper(home, "from", env={"CLAUDE_CONFIG_DIR": str(elsewhere)}).stdout, "CLAUDE_CONFIG_DIR wins for claude")

    def test_helper_is_silent_without_a_file_and_warns_on_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            absent = self.run_helper(home, "from")
            self.assertEqual((0, "", ""), (absent.returncode, absent.stdout, absent.stderr))
            (home / ".claude").mkdir()
            (home / ".claude/prewalk.json").write_text("{oops")
            invalid = self.run_helper(home, "from")
            self.assertEqual((0, ""), (invalid.returncode, invalid.stdout))
            self.assertIn("not valid JSON", invalid.stderr)
            usage = subprocess.run([sys.executable, str(ROOT / "scripts/prewalk_config.py"), "claude"], text=True, capture_output=True)
            self.assertEqual(64, usage.returncode)
            unknown = subprocess.run([sys.executable, str(ROOT / "scripts/prewalk_config.py"), "codex", "from"], text=True, capture_output=True)
            self.assertEqual(64, unknown.returncode)


class InstallerTests(unittest.TestCase):
    def run_installer(self, home: Path, action: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(INSTALLER), "--home", str(home), action, "claude"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "HOME": str(home)},
        )
        if check and result.returncode != 0:
            self.fail(f"installer failed: {result.stdout}\n{result.stderr}")
        return result

    def seeded_settings(self) -> dict:
        return {
            "permissions": {"defaultMode": "auto"},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook claude"}]}]},
            "statusLine": {"type": "command", "command": "statusline"},
        }

    def test_install_merges_hooks_idempotently_and_preserves_everything_else(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            settings = home / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps(self.seeded_settings(), indent=2) + "\n")
            settings.chmod(0o640)

            self.run_installer(home, "install")
            first = settings.read_text()
            self.run_installer(home, "install")
            self.assertEqual(first, settings.read_text())
            self.run_installer(home, "check")

            data = json.loads(first)
            self.assertEqual(self.seeded_settings()["permissions"], data["permissions"])
            self.assertEqual(self.seeded_settings()["statusLine"], data["statusLine"])
            pre = data["hooks"]["PreToolUse"]
            self.assertEqual({"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook claude"}]}, pre[0])
            self.assertEqual("Edit|Write|MultiEdit|NotebookEdit", pre[1]["matcher"])
            self.assertIn("prewalk_hook.py claude || true", pre[1]["hooks"][0]["command"])
            post_matchers = [group["matcher"] for group in data["hooks"]["PostToolUse"]]
            self.assertEqual(["Edit|Write|MultiEdit|NotebookEdit", "TodoWrite"], post_matchers)
            self.assertEqual(0o640, settings.stat().st_mode & 0o777)

            config_link = home / ".claude/prewalk.json"
            self.assertEqual(ROOT / "adapters/claude/prewalk.json", Path(os.readlink(config_link)))
            self.assertEqual("fable", json.loads(config_link.read_text())["from"])
            link = home / ".local/bin/claude-prewalk"
            self.assertTrue(link.is_symlink())
            self.assertEqual(ROOT / "adapters/claude/bin/claude-prewalk", Path(os.readlink(link)))

    def test_install_converges_a_stale_hook_command_and_tolerates_null_groups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            settings = home / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            stale = {"hooks": {"PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [{"type": "command", "command": "python3 /old/place/scripts/prewalk_hook.py claude"}]}], "PostToolUse": None}}
            settings.write_text(json.dumps(stale))
            failed = self.run_installer(home, "check", check=False)
            self.assertNotEqual(0, failed.returncode, "check must not crash on a null group list")
            result = self.run_installer(home, "install", check=False)
            self.assertNotEqual(0, result.returncode, "a null PostToolUse list is refused, not overwritten")
            stale["hooks"]["PostToolUse"] = []
            settings.write_text(json.dumps(stale))
            self.run_installer(home, "install")
            data = json.loads(settings.read_text())
            pre = data["hooks"]["PreToolUse"]
            self.assertEqual(1, len(pre), "the stale group is converged, not duplicated")
            self.assertIn("[ -f ", pre[0]["hooks"][0]["command"])
            self.assertIn("|| true", pre[0]["hooks"][0]["command"])
            self.run_installer(home, "check")

    def test_install_writes_through_a_symlinked_settings_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            real = home / "owner/settings.json"
            real.parent.mkdir(parents=True)
            real.write_text("{}")
            link = home / ".claude/settings.json"
            link.parent.mkdir(parents=True)
            link.symlink_to(real)
            self.run_installer(home, "install")
            self.assertTrue(link.is_symlink(), "the link survives")
            self.assertIn("prewalk_hook.py", real.read_text())

    def test_install_creates_settings_when_absent_and_check_fails_before_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            failed = self.run_installer(home, "check", check=False)
            self.assertNotEqual(0, failed.returncode)
            self.run_installer(home, "install")
            data = json.loads((home / ".claude/settings.json").read_text())
            self.assertEqual(["hooks"], list(data))

    def test_install_refuses_to_replace_an_unmanaged_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            target = home / ".local/bin/claude-prewalk"
            target.parent.mkdir(parents=True)
            target.write_text("#!/bin/sh\necho mine\n")
            result = self.run_installer(home, "install", check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("refusing", result.stderr)
            self.assertEqual("#!/bin/sh\necho mine\n", target.read_text())
            self.assertFalse((home / ".claude/settings.json").exists(), "preflight runs before any write")


if __name__ == "__main__":
    unittest.main()
