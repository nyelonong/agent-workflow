from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "adapters/pi/prompts"
PORTABLE_WORKFLOW = ROOT / "skills/workflow/SKILL.md"


class PromptContractTests(unittest.TestCase):
    def test_prompts_have_unique_valid_command_names(self) -> None:
        prompts = sorted(PROMPTS.glob("*.md"))
        self.assertEqual(14, len(prompts))
        names: set[str] = set()
        for prompt in prompts:
            self.assertRegex(prompt.stem, r"^[a-z0-9][a-z0-9-]*$")
            text = prompt.read_text(encoding="utf-8")
            self.assertRegex(text, r"\A---\ndescription: .+\n")
            self.assertNotIn(prompt.stem, names)
            names.add(prompt.stem)

    def test_resume_keeps_the_recorded_execution_path_and_review_boundary(self) -> None:
        text = (PROMPTS / "resume-plan.md").read_text(encoding="utf-8")
        self.assertIn("retain the execution path recorded", text)
        self.assertIn("direct implementation never waives a review", text)
        self.assertNotIn("waives independent review for any consequential", text)

    def test_portable_workflow_has_no_pi_mechanics(self) -> None:
        text = PORTABLE_WORKFLOW.read_text(encoding="utf-8")
        for token in ("ask_decision", "workflowScript", "pi-subagents", "vcc_recall", "rdg_tile"):
            self.assertNotIn(token, text)

    def test_prepush_uses_the_independent_review_boundary(self) -> None:
        text = (PROMPTS / "prepush.md").read_text(encoding="utf-8")
        self.assertIn("independent-review\nboundary", text)
        self.assertNotIn("consequence-based independent", text)


if __name__ == "__main__":
    unittest.main()
