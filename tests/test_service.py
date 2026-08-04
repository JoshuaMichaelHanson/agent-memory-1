from __future__ import annotations

import sqlite3
import time
import unittest
import uuid
from pathlib import Path

from agent_memory.errors import ValidationError
from agent_memory.models import MemoryInput, content_sha256
from agent_memory.service import MemoryService


REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = REPO_ROOT / "tmp" / "tests"


class ServicePutTests(unittest.TestCase):
    def db_path(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        return TMP_ROOT / f"service-{uuid.uuid4().hex}" / "memory.db"

    def count_memories(self, path: Path) -> int:
        connection = sqlite3.connect(path)
        try:
            return int(connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
        finally:
            connection.close()

    def test_keyed_insert_update_and_unchanged(self) -> None:
        path = self.db_path()
        service = MemoryService(path)

        inserted = service.put(
            MemoryInput(
                project="demo",
                kind="decision",
                memory_key="database-choice",
                content="Use SQLite as canonical memory.",
                tags=("sqlite", "Architecture"),
                source_agent="codex",
                importance=5,
            )
        )
        unchanged = service.put(
            MemoryInput(
                project="demo",
                kind="decision",
                memory_key="database-choice",
                content="Use SQLite as canonical memory.",
                tags=("architecture", "sqlite"),
                source_agent="codex",
                importance=5,
            )
        )
        time.sleep(0.01)
        updated = service.put(
            MemoryInput(
                project="demo",
                kind="decision",
                memory_key="database-choice",
                content="Use SQLite as canonical memory and export Markdown only for inspection.",
                tags=("sqlite", "architecture"),
                source_agent="claude",
                importance=5,
            )
        )

        self.assertEqual(inserted.operation, "inserted")
        self.assertEqual(unchanged.operation, "unchanged")
        self.assertEqual(updated.operation, "updated")
        self.assertEqual(inserted.memory.id, unchanged.memory.id)
        self.assertEqual(inserted.memory.id, updated.memory.id)
        self.assertEqual(inserted.memory.created_at, updated.memory.created_at)
        self.assertEqual(unchanged.memory.updated_at, inserted.memory.updated_at)
        self.assertGreaterEqual(updated.memory.updated_at, inserted.memory.updated_at)
        self.assertEqual(updated.memory.tags, ("architecture", "sqlite"))
        self.assertEqual(updated.memory.source_agent, "claude")
        self.assertEqual(self.count_memories(path), 1)

    def test_unkeyed_puts_create_separate_rows(self) -> None:
        path = self.db_path()
        service = MemoryService(path)

        first = service.put(MemoryInput(project="demo", content="Journal note."))
        second = service.put(MemoryInput(project="demo", content="Journal note."))

        self.assertEqual(first.operation, "inserted")
        self.assertEqual(second.operation, "inserted")
        self.assertNotEqual(first.memory.id, second.memory.id)
        self.assertEqual(self.count_memories(path), 2)

    def test_validation_rejects_bad_importance_and_empty_content(self) -> None:
        service = MemoryService(self.db_path())

        with self.assertRaises(ValidationError):
            service.put(MemoryInput(project="demo", content="value", importance=6))

        with self.assertRaises(ValidationError):
            service.put(MemoryInput(project="demo", content=" \r\n\t "))

    def test_content_hash_normalizes_line_endings(self) -> None:
        path = self.db_path()
        service = MemoryService(path)

        result = service.put(MemoryInput(project="demo", content="one\r\ntwo"))

        self.assertEqual(result.memory.content_sha256, content_sha256("one\ntwo"))


if __name__ == "__main__":
    unittest.main()
