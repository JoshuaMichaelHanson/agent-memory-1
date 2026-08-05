from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from agent_memory.errors import ValidationError
from agent_memory.instructions import SECTION_BEGIN, SECTION_END, build_agent_instructions_payload, install_agent_instructions, replace_or_append_section


REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = REPO_ROOT / "tmp" / "tests"


class InstructionTests(unittest.TestCase):
    def output_path(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        return TMP_ROOT / f"instructions-{uuid.uuid4().hex}" / "AGENTS.md"

    def test_instruction_payload_contains_marked_section_and_commands(self) -> None:
        payload = build_agent_instructions_payload("demo")

        self.assertEqual(payload["format"], "agent-memory.instructions.v1")
        self.assertEqual(payload["project"], "demo")
        self.assertIn(SECTION_BEGIN, payload["section"])
        self.assertIn(SECTION_END, payload["section"])
        self.assertIn("agent-memory search", payload["section"])
        self.assertIn("agent-memory export-json", payload["section"])
        self.assertIn("agent-memory copy", payload["section"])
        self.assertIn("agent-memory --help", payload["section"])
        self.assertIn("agent-memory <command> --help", payload["section"])
        self.assertIn("search", {command["name"] for command in payload["commands"]})
        self.assertIn("copy", {command["name"] for command in payload["commands"]})

    def test_install_instructions_inserts_updates_and_becomes_unchanged(self) -> None:
        output = self.output_path()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("# Project Agents\n\nExisting guidance.\n", encoding="utf-8")

        inserted = install_agent_instructions(output_path=output, project="demo")
        updated = install_agent_instructions(output_path=output, project="demo-renamed")
        unchanged = install_agent_instructions(output_path=output, project="demo-renamed")
        text = output.read_text(encoding="utf-8")

        self.assertEqual(inserted.operation, "inserted")
        self.assertEqual(updated.operation, "updated")
        self.assertEqual(unchanged.operation, "unchanged")
        self.assertEqual(text.count(SECTION_BEGIN), 1)
        self.assertEqual(text.count(SECTION_END), 1)
        self.assertIn("Existing guidance.", text)
        self.assertIn("Project name: `demo-renamed`", text)
        self.assertNotIn("Project name: `demo`", text)

    def test_replace_or_append_rejects_incomplete_managed_section(self) -> None:
        with self.assertRaises(ValidationError):
            replace_or_append_section("# Agents\n\n" + SECTION_BEGIN + "\n", "section")


if __name__ == "__main__":
    unittest.main()