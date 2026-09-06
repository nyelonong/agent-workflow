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
WRAPPER = ROOT / "adapters/agy/bin/agy-prewalk"
INSTALLER = ROOT / "install.sh"
FIXTURE = ROOT / "tests/fixtures/agy-phase1.jsonl"

FAKE_AGY = r'''#!/bin/sh
# Fake agy: logs argv per phase; phase 1 replays the fixture and emulates the
# installed hooks having written FAKE_AGY_MARKERS into the state file.
printf '%s\n' "$*" >> "$FAKE_AGY_LOG"
case " $* " in
  *" -p "*)
    [ -z "${FAKE_AGY_FAIL:-}" ] || { echo "not signed in" >&2; exit 1; }
    [ -z "${AGY_PREWALK_STATE:-}" ] || printf '%s' "$FAKE_AGY_MARKERS" >> "$AGY_PREWALK_STATE"
    printf 'pwd:%s\n' "$PWD" >> "$FAKE_AGY_LOG"
    cat "$FAKE_AGY_FIXTURE"
    ;;
  *) printf 'interactive:%s\n' "${AGY_PREWALK_STATE:-unset}" >> "$FAKE_AGY_LOG" ;;
esac
'''


def clean_env(extra: dict[str, str]) -> dict[str, str]:
    base = {k: v for k, v in os.environ.items() if not k.startswith(("AGY_PREWALK_", "CLAUDE_PREWALK_"))}
    return {**base, **extra}


def run_hook(event_name: str, event: dict | str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK), "agy", event_name],
        input=event if isinstance(event, str) else json.dumps(event),
        text=True,
        capture_output=True,
        env=clean_env(env),
    )


def tool_event(name: str, error: str | None = None) -> dict:
    event = {"toolCall": {"name": name, "args": {}}, "stepIdx": 1, "modelName": "m"}
    if error:
        event["error"] = error
    return event


class HookTests(unittest.TestCase):
    def test_unarmed_hooks_print_nothing(self) -> None:
        # Empty stdout leaves Antigravity's permission flow untouched; "{}" would deny.
        for event_name, event in (("PreToolUse", tool_event("write_to_file")), ("PostToolUse", tool_event("edit")), ("PreInvocation", {"invocationNum": 1}), ("Stop", {"terminationReason": "done"})):
            result = run_hook(event_name, event, {})
            self.assertEqual(0, result.returncode)
            self.assertEqual("", result.stdout)

    def test_armed_flow_nudge_once_silent_allow_record_deny(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            env = {"AGY_PREWALK_STATE": str(state)}

            first = json.loads(run_hook("PreInvocation", {"invocationNum": 1}, env).stdout)
            self.assertIn("Prewalk phase 1.", first["injectSteps"][0]["ephemeralMessage"])
            self.assertEqual("", run_hook("PreInvocation", {"invocationNum": 2}, env).stdout, "the nudge is injected once")

            pushed = json.loads(run_hook("Stop", {"terminationReason": "done"}, env).stdout)
            self.assertEqual("continue", pushed["decision"], "a plan-only run is pushed on once")
            self.assertEqual("", run_hook("Stop", {"terminationReason": "done"}, env).stdout)

            # Never an explicit allow: permissions stay with the user's mode, even for shell tools.
            self.assertEqual("", run_hook("PreToolUse", tool_event("write_to_file"), env).stdout)
            self.assertEqual("", run_hook("PreToolUse", tool_event("run_command"), env).stdout)
            run_hook("PostToolUse", tool_event("write_to_file", error="permission denied"), env)
            self.assertNotIn("edit", state.read_text().split(), "a failed tool is not a first edit")
            self.assertEqual("", run_hook("PostToolUse", tool_event("write_to_file"), env).stdout)
            self.assertIn("edit", state.read_text().split())

            denied = json.loads(run_hook("PreToolUse", tool_event("replace"), env).stdout)
            self.assertEqual("deny", denied["decision"])
            self.assertIn("Prewalk handoff", denied["reason"])
            self.assertEqual("", run_hook("PreToolUse", tool_event("run_command"), env).stdout, "shell tools are never denied or allowed")
            self.assertEqual("", run_hook("PreInvocation", {"invocationNum": 3}, env).stdout)
            self.assertEqual("", run_hook("Stop", {"terminationReason": "done"}, env).stdout, "no push after the edit")

    def test_malformed_input_never_denies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {"AGY_PREWALK_STATE": str(Path(tmp) / "missing" / "state")}
            self.assertEqual("", run_hook("PreToolUse", "not json", env).stdout)
            result = run_hook("PostToolUse", tool_event("edit"), env)
            self.assertEqual(0, result.returncode, "an unwritable state file fails open")
            self.assertEqual("", result.stdout)


class RenderTests(unittest.TestCase):
    def test_renders_agy_stream(self) -> None:
        result = subprocess.run([sys.executable, str(RENDER), "agy"], input=FIXTURE.read_text(), text=True, capture_output=True)
        self.assertEqual(0, result.returncode)
        self.assertIn("[init] model claude-opus-4-6-thinking", result.stdout)
        self.assertIn("Plan: 1. write greet.py", result.stdout)
        self.assertIn("> write_to_file: /work/greet.py", result.stdout)
        self.assertIn("! write_to_file: tool call denied by pre-tool hook", result.stdout)
        self.assertIn("[result] SUCCESS turns 1", result.stdout)

    def test_stream_without_init_fails(self) -> None:
        result = subprocess.run([sys.executable, str(RENDER), "agy"], input='{"event":"result","result":{}}\n', text=True, capture_output=True)
        self.assertEqual(1, result.returncode)


class WrapperTests(unittest.TestCase):
    def run_wrapper(self, markers: str, *args: str, fail_phase1: bool = False, config: str | None = None) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "agy"
            fake.write_text(FAKE_AGY)
            fake.chmod(0o755)
            log = Path(tmp) / "argv.log"
            env = clean_env({
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "FAKE_AGY_LOG": str(log),
                "FAKE_AGY_FIXTURE": str(FIXTURE),
                "FAKE_AGY_MARKERS": markers,
                "TMPDIR": tmp,
            })
            if fail_phase1:
                env["FAKE_AGY_FAIL"] = "1"
            env["HOME"] = str(Path(tmp) / "home")
            (Path(tmp) / "home").mkdir()
            if config is not None:
                (Path(tmp) / "home/.gemini").mkdir()
                (Path(tmp) / "home/.gemini/prewalk.json").write_text(config)
            result = subprocess.run([str(WRAPPER), *args], text=True, capture_output=True, env=env, cwd=tmp)
            lines = log.read_text().splitlines() if log.exists() else []
            leftover = [p for p in Path(tmp).iterdir() if p.name.startswith("agy-prewalk.")]
            return result, lines + [f"leftover:{len(leftover)}"]

    def test_phase_one_then_resume_cheap(self) -> None:
        result, lines = self.run_wrapper("edit\n", "--", "add greet")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(lines[0].startswith("--model claude-opus-4-6-thinking --mode accept-edits --output-format stream-json -p add greet"), lines[0])
        self.assertNotIn("--add-dir", lines[0])
        self.assertIn("Plan: 1. write greet.py", result.stdout)
        phase2 = [line for line in lines if line.startswith("--conversation")][0]
        self.assertTrue(phase2.startswith("--conversation CONV --model gemini-3.8-flash-low -i Continue from the checklist."), phase2)
        self.assertIn("interactive:unset", lines)
        self.assertIn("leftover:0", lines, "the temporary state file is removed before phase 2")

    def test_no_edit_resumes_on_the_strong_model(self) -> None:
        result, lines = self.run_wrapper("", "--from", "gemini-3.1-pro-high", "--into", "gemini-3.8-flash-low", "--mode", "plan", "--", "explain")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("--model gemini-3.1-pro-high --mode plan", lines[0])
        phase2 = [line for line in lines if line.startswith("--conversation")][0]
        self.assertIn("--conversation CONV --model gemini-3.1-pro-high -i Continue the task", phase2)
        self.assertIn("no edit recorded", result.stderr)

    def test_phase_one_failure_does_not_resume_and_cleans_up(self) -> None:
        result, lines = self.run_wrapper("", "--", "task", fail_phase1=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("did not start", result.stderr)
        self.assertFalse(any(line.startswith(("--continue", "--conversation")) for line in lines))
        self.assertIn("leftover:0", lines)

    def test_config_file_sets_defaults_and_flags_win(self) -> None:
        config = json.dumps({"from": "gemini-3.1-pro-high", "into": "gemini-3.8-flash-medium", "mode": "plan"})
        _, lines = self.run_wrapper("edit\n", "--", "task", config=config)
        self.assertIn("--model gemini-3.1-pro-high --mode plan", lines[0])
        self.assertIn("--model gemini-3.8-flash-medium -i", [l for l in lines if l.startswith("--conversation")][0])

        _, lines = self.run_wrapper("edit\n", "--mode", "accept-edits", "--", "task", config=config)
        self.assertIn("--model gemini-3.1-pro-high --mode accept-edits", lines[0], "the flag wins, the file fills the rest")

        result, lines = self.run_wrapper("edit\n", "--", "task", config="[]")
        self.assertIn("JSON object", result.stderr)
        self.assertIn("--model claude-opus-4-6-thinking --mode accept-edits", lines[0], "shipped defaults on a wrong shape")

    def test_usage(self) -> None:
        result, _ = self.run_wrapper("", "--into")
        self.assertEqual(64, result.returncode)


class InstallerTests(unittest.TestCase):
    def test_install_agy_adds_a_prewalk_block_beside_existing_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = {**os.environ, "HOME": str(home)}
            hooks = home / ".gemini/config/hooks.json"
            hooks.parent.mkdir(parents=True)
            orca = {"orca-status": {"PreInvocation": [{"type": "command", "command": "orca.sh", "timeout": 10}]}, "prewalk": {"PreToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "python3 /old/prewalk_hook.py agy PreToolUse"}]}]}}
            hooks.write_text(json.dumps(orca, indent=2) + "\n")
            hooks.chmod(0o640)

            subprocess.run([str(INSTALLER), "--home", str(home), "install", "agy"], cwd=ROOT, check=True, env=env, capture_output=True)
            first = hooks.read_text()
            subprocess.run([str(INSTALLER), "--home", str(home), "install", "agy"], cwd=ROOT, check=True, env=env, capture_output=True)
            self.assertEqual(first, hooks.read_text(), "idempotent")
            data = json.loads(first)
            self.assertEqual(orca["orca-status"], data["orca-status"], "other blocks untouched")
            self.assertEqual(["PreInvocation", "Stop", "PreToolUse", "PostToolUse"], list(data["prewalk"]), "stale block converged")
            command = data["prewalk"]["PreToolUse"][0]["hooks"][0]["command"]
            self.assertIn("prewalk_hook.py agy PreToolUse || true", command)
            self.assertTrue(command.startswith("[ -f "))
            self.assertEqual(0o640, hooks.stat().st_mode & 0o777)
            subprocess.run([str(INSTALLER), "--home", str(home), "check", "agy"], cwd=ROOT, check=True, env=env, capture_output=True)

            data["prewalk"]["PreToolUse"] = []
            hooks.write_text(json.dumps(data))
            failed = subprocess.run([str(INSTALLER), "--home", str(home), "check", "agy"], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertNotEqual(0, failed.returncode)
            self.assertIn("prewalk block", failed.stderr)

    def test_install_agy_links_the_wrapper_and_check_verifies_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = {**os.environ, "HOME": str(home)}
            subprocess.run([str(INSTALLER), "--home", str(home), "install", "agy"], cwd=ROOT, check=True, env=env, capture_output=True)
            self.assertEqual(["PreInvocation", "Stop", "PreToolUse", "PostToolUse"], list(json.loads((home / ".gemini/config/hooks.json").read_text())["prewalk"]))
            config_link = home / ".gemini/prewalk.json"
            self.assertEqual(ROOT / "adapters/agy/prewalk.json", Path(os.readlink(config_link)))
            self.assertEqual("gemini-3.8-flash-low", json.loads(config_link.read_text())["into"])
            link = home / ".local/bin/agy-prewalk"
            self.assertTrue(link.is_symlink())
            self.assertEqual(ROOT / "adapters/agy/bin/agy-prewalk", Path(os.readlink(link)))
            subprocess.run([str(INSTALLER), "--home", str(home), "check", "agy"], cwd=ROOT, check=True, env=env, capture_output=True)
            link.unlink()
            link.write_text("mine")
            failed = subprocess.run([str(INSTALLER), "--home", str(home), "install", "agy"], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertNotEqual(0, failed.returncode)
            self.assertIn("refusing", failed.stderr)


if __name__ == "__main__":
    unittest.main()
