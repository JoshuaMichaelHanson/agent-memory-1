from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class SkillTemplateTests(unittest.TestCase):
    def read_template(self, relative_path: str) -> str:
        return (REPO_ROOT / relative_path).read_text(encoding="utf-8")

    def test_codex_skill_template_contains_required_workflow(self) -> None:
        text = self.read_template("examples/codex-skill-template/agent-memory/SKILL.md")

        self.assertTrue(text.startswith("---\nname: agent-memory\n"))
        self.assertIn("description:", text)
        self.assertIn("agent-memory --help", text)
        self.assertIn("agent-memory status", text)
        self.assertIn("agent-memory search", text)
        self.assertIn("agent-memory put", text)
        self.assertIn("agent-memory mirror-file", text)
        self.assertIn("agent-memory copy", text)
        self.assertIn("agent-memory export-json", text)
        self.assertIn("agent-memory export-md", text)
        self.assertIn("Do not store", text)
        self.assertIn("advisory context", text)

    def test_claude_skill_template_contains_required_workflow(self) -> None:
        text = self.read_template("examples/claude-skill-template/agent-memory/SKILL.md")

        self.assertTrue(text.startswith("---\nname: agent-memory\n"))
        self.assertIn("description:", text)
        self.assertIn("agent-memory --help", text)
        self.assertIn("agent-memory status", text)
        self.assertIn("agent-memory search", text)
        self.assertIn("agent-memory put", text)
        self.assertIn("agent-memory mirror-file", text)
        self.assertIn("agent-memory copy", text)
        self.assertIn("agent-memory export-json", text)
        self.assertIn("agent-memory export-md", text)
        self.assertIn("Never store secrets", text)
        self.assertIn("advisory only", text)

    def test_skill_template_docs_reference_install_paths_and_test_prompts(self) -> None:
        text = self.read_template("docs/AGENT_MEMORY_SKILL_TEMPLATES.md")

        self.assertIn(".codex/skills/agent-memory/SKILL.md", text)
        self.assertIn(".claude/skills/agent-memory/SKILL.md", text)
        self.assertIn("Example Test Prompts", text)
        self.assertIn("agent-memory --help", text)
        self.assertIn("Safety Rules", text)


if __name__ == "__main__":
    unittest.main()