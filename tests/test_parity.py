"""Every runtime renders the same policy; runtime mechanics stay in their own adapter."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install  # noqa: E402

POLICY = (ROOT / "policy.md").read_text(encoding="utf-8")
POLICY_HEADINGS = re.findall(r"(?m)^## .+$", POLICY)
PHASES = ("shape", "plan", "implement", "review", "finish")
PORTABLE_SKILL = (ROOT / "skills/workflow/SKILL.md").read_text(encoding="utf-8")
PI_FILE = Path.home() / ".pi/agent/AGENTS.md"
PI_SKILL = Path.home() / ".pi/agent/skills/workflow/SKILL.md"

MECHANICS = {
    "pi": ("ask_decision", "workflowScript", "vcc_recall", "pi-subagents"),
    "claude": ("Claude Code", "/graphify"),
    "agy": ("Antigravity",),
    "codex": ("spawn", "$workflow", "Codex"),
    "omp": ("skill://", "the `ask` tool", "`scout`"),
}


def rendered() -> dict[str, str]:
    claude = (ROOT / "adapters/claude/CLAUDE.md").read_text(encoding="utf-8").replace("@__POLICY_PATH__", POLICY)
    agy = install.managed_block().replace(f"@{ROOT / 'policy.md'}", POLICY)
    out = {"claude": claude, "agy": agy, "codex": install.codex_block()}
    out["omp"] = install.omp_block().replace(f"@{ROOT / 'policy.md'}", POLICY)
    if PI_FILE.is_file():
        out["pi"] = PI_FILE.read_text(encoding="utf-8")
    return out


class ParityTests(unittest.TestCase):
    def test_policy_has_the_expected_shape(self) -> None:
        self.assertGreaterEqual(len(POLICY_HEADINGS), 9)
        self.assertTrue(POLICY.startswith("# Personal engineering workflow\n"))

    def test_every_runtime_carries_every_policy_heading(self) -> None:
        for runtime, text in rendered().items():
            for heading in POLICY_HEADINGS:
                self.assertIn(heading, text, f"{runtime} lacks {heading}")

    def test_every_runtime_names_every_workflow_phase(self) -> None:
        for runtime, text in rendered().items():
            skill = PI_SKILL.read_text(encoding="utf-8") if runtime == "pi" else PORTABLE_SKILL
            combined = (text + "\n" + skill).lower()
            for phase in PHASES:
                self.assertIn(phase, combined, f"{runtime} never mentions {phase}")

    def test_runtime_mechanics_stay_in_their_own_runtime(self) -> None:
        texts = rendered()
        for owner, tokens in MECHANICS.items():
            if owner not in texts:
                continue
            for token in tokens:
                self.assertIn(token, texts[owner], f"{owner} adapter should mention {token}")
                for other, text in texts.items():
                    if other != owner:
                        self.assertNotIn(token, text, f"{token} belongs to {owner} but appears in {other}")

    def test_adapters_map_mechanics_only_and_consume_the_generated_policy(self) -> None:
        claude = (ROOT / "adapters/claude/CLAUDE.md").read_text(encoding="utf-8")
        agy = (ROOT / "adapters/agy/GEMINI.md").read_text(encoding="utf-8")
        codex = (ROOT / "adapters/codex/AGENTS.md").read_text(encoding="utf-8")
        omp = (ROOT / "adapters/omp/AGENTS.md").read_text(encoding="utf-8")
        for name, adapter in (("claude", claude), ("agy", agy), ("codex", codex), ("omp", omp)):
            for heading in POLICY_HEADINGS:
                self.assertNotIn(heading, adapter, f"{name} adapter restates policy section {heading}")
        self.assertIn("@__POLICY_PATH__", claude, "Claude includes the generated policy by path")
        self.assertIn(f"@{ROOT / 'policy.md'}", install.managed_block(), "Antigravity includes the generated policy by path")
        self.assertIn(f"@{ROOT / 'policy.md'}", install.omp_block(), "omp includes the generated policy by path")
        codex_policy = POLICY.strip().replace(
            "start it on the stronger model and let prewalk hand off after the first edit.",
            "use the current model without an automatic handoff.",
        )
        self.assertIn(codex_policy, install.codex_block(), "Codex changes only its unsupported model handoff")
        self.assertNotIn("let prewalk hand off", install.codex_block())

    def test_generated_policy_is_free_of_pi_mechanics(self) -> None:
        for token in MECHANICS["pi"] + ("BASE_TOOLS", "~/.pi/", "pi-only"):
            self.assertNotIn(token, POLICY, token)

    @unittest.skipUnless(PI_FILE.is_file(), "Pi is not installed here")
    def test_pi_file_marks_every_mechanic(self) -> None:
        text = PI_FILE.read_text(encoding="utf-8")
        outside = install_render(text)
        for token in MECHANICS["pi"]:
            self.assertIn(token, text)
            self.assertNotIn(token, outside, f"{token} appears outside a pi-only block")

    @unittest.skipUnless(PI_FILE.is_file(), "Pi is not installed here")
    def test_pi_uses_the_shared_review_gate(self) -> None:
        # Pi used to be wired to rdg_task_review, whose reviewer cannot return a
        # result, so Pi could never satisfy the portable commit rule. Every
        # runtime must now name the same client and the same skill.
        text = PI_FILE.read_text(encoding="utf-8")
        self.assertIn("task-review", text)
        self.assertIn("scripts/task_review.py", text)
        self.assertNotIn("rdg_task_review", text, "the dead reviewer must not come back")
        pi_skill = Path.home() / ".pi/agent/skills/task-review/SKILL.md"
        self.assertTrue(pi_skill.is_file(), "Pi must reach the shared task-review skill")
        pi_workflow = Path.home() / ".pi/agent/skills/workflow/SKILL.md"
        if pi_workflow.is_file():
            workflow = pi_workflow.read_text(encoding="utf-8")
            self.assertIn("task_review.py", workflow)
            self.assertNotIn("rdg_task_review", workflow, "Pi's workflow skill must not name the dead reviewer")


def install_render(text: str) -> str:
    sys.path.insert(0, str(ROOT / "scripts"))
    import render_policy  # noqa: E402

    return render_policy.render(text)


if __name__ == "__main__":
    unittest.main()
