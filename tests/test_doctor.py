from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from agent_memory.doctor import run_doctor
from agent_memory.models import MemoryInput
from agent_memory.service import MemoryService


REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = REPO_ROOT / "tmp" / "tests"
GITIGNORE_TEXT = """.agent-memory/memory.db
.agent-memory/memory.db-shm
.agent-memory/memory.db-wal
.agent-memory/*.tmp
"""


class DoctorTests(unittest.TestCase):
    def project_root(self) -> Path:
        root = TMP_ROOT / f"doctor-{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def create_healthy_project(self) -> tuple[Path, Path]:
        root = self.project_root()
        (root / ".gitignore").write_text(GITIGNORE_TEXT, encoding="utf-8")
        db_path = root / ".agent-memory" / "memory.db"
        service = MemoryService(db_path)
        service.put(MemoryInput(project="demo", kind="decision", memory_key="database-choice", content="Use SQLite."))
        service.export_json_snapshot(project="demo", output_path=root / "docs" / "agent-memory.snapshot.json")
        service.export_markdown(project="demo", output_path=root / "docs" / "MEMORY.generated.md")
        return root, db_path

    def test_doctor_reports_healthy_project(self) -> None:
        root, db_path = self.create_healthy_project()

        result = run_doctor(database_path=db_path, project_root=root, project="demo")
        payload = result.to_dict()

        self.assertTrue(result.healthy)
        self.assertEqual(payload["failure_count"], 0)
        self.assertEqual(payload["warning_count"], 0)
        self.assertIn("snapshot_restore", {check.name for check in result.checks})

    def test_doctor_reports_missing_database_and_exports(self) -> None:
        root = self.project_root()
        db_path = root / ".agent-memory" / "memory.db"

        result = run_doctor(database_path=db_path, project_root=root, project="demo")
        failure_names = {check.name for check in result.failures}
        warning_names = {check.name for check in result.warnings}

        self.assertFalse(result.healthy)
        self.assertIn("database_exists", failure_names)
        self.assertIn("schema_version", failure_names)
        self.assertIn("live_db_ignored", warning_names)
        self.assertIn("snapshot_export_present", warning_names)
        self.assertIn("markdown_export_present", warning_names)
        self.assertIn("snapshot_restore", warning_names)


if __name__ == "__main__":
    unittest.main()
