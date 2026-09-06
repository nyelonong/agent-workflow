"""Canonical policy is rendered consistently while runtime mechanics stay local."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install  # noqa: E402
import render_policy  # noqa: E402

POLICY = (ROOT / "policy.md").read_text(encoding="utf-8")
CORE = (ROOT / "policy/core.md").read_text(encoding="utf-8")
POLICY_HEADINGS = re.findall(r"(?m)^## .+$", POLICY)
PHASES = ("shape", "plan", "implement", "review", "finish")
PORTABLE_SKILL = (ROOT / "skills/workflow/SKILL.md").read_text(encoding="utf-8")

MECHANICS = {
    "pi": ("ask_decision", "workflowScript", "vcc_recall", "/council", "pi-subagents"),
    "claude": ("Claude Code", "golang-how-to", "/graphify"),
    "agy": ("Antigravity",),
    "codex": ("spawn", "$workflow", "Codex"),
}


def rendered() -> dict[str, str]:
    claude = (ROOT / "adapters/claude/CLAUDE.md").read_text(encoding="utf-8").replace("@__POLICY_PATH__", POLICY)
    agy = install.managed_block().replace(f"@{ROOT / 'policy.md'}", POLICY)
    return {"pi": install.pi_block(), "claude": claude, "agy": agy, "codex": install.codex_block()}


class ParityTests(unittest.TestCase):
    def test_policy_is_generated_from_the_canonical_source(self) -> None:
        self.assertEqual(render_policy.render(CORE), POLICY)
        self.assertTrue(POLICY.startswith("# Personal engineering workflow\n"))
        self.assertGreaterEqual(len(POLICY_HEADINGS), 9)

    def test_every_runtime_carries_every_policy_heading(self) -> None:
        for runtime, text in rendered().items():
            for heading in POLICY_HEADINGS:
                self.assertIn(heading, text, f"{runtime} lacks {heading}")

    def test_every_runtime_names_every_workflow_phase(self) -> None:
        for runtime, text in rendered().items():
            combined = (text + "\n" + PORTABLE_SKILL).lower()
            for phase in PHASES:
                self.assertIn(phase, combined, f"{runtime} never mentions {phase}")

    def test_runtime_mechanics_stay_in_their_own_runtime(self) -> None:
        texts = rendered()
        for owner, tokens in MECHANICS.items():
            for token in tokens:
                self.assertIn(token, texts[owner], f"{owner} adapter should mention {token}")
                for other, text in texts.items():
                    if other != owner:
                        self.assertNotIn(token, text, f"{token} belongs to {owner} but appears in {other}")

    def test_adapters_consume_canonical_policy_without_restatement(self) -> None:
        for name, adapter in (("claude", ROOT / "adapters/claude/CLAUDE.md"), ("agy", ROOT / "adapters/agy/GEMINI.md"), ("codex", ROOT / "adapters/codex/AGENTS.md")):
            text = adapter.read_text(encoding="utf-8")
            for heading in POLICY_HEADINGS:
                self.assertNotIn(heading, text, f"{name} adapter restates policy section {heading}")
        self.assertIn("@__POLICY_PATH__", (ROOT / "adapters/claude/CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn(f"@{ROOT / 'policy.md'}", install.managed_block())
        self.assertIn(POLICY.strip(), install.codex_block())

    def test_portable_sources_are_free_of_pi_mechanics(self) -> None:
        sources = POLICY + "\n" + PORTABLE_SKILL
        for token in MECHANICS["pi"] + ("BASE_TOOLS", "~/.pi/", "pi-only"):
            self.assertNotIn(token, sources, token)
        block = install.pi_block()
        for token in MECHANICS["pi"]:
            self.assertIn(token, block)


if __name__ == "__main__":
    unittest.main()
