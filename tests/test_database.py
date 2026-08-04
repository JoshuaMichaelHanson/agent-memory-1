from __future__ import annotations

import sqlite3
import unittest
import uuid
from pathlib import Path

from agent_memory.database import initialize_database, inspect_database


REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = REPO_ROOT / "tmp" / "tests"


class DatabaseTests(unittest.TestCase):
    def db_path(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        return TMP_ROOT / f"phase2-{uuid.uuid4().hex}" / "memory.db"

    def test_initialize_is_idempotent_and_reports_schema(self) -> None:
        path = self.db_path()

        first = initialize_database(path)
        second = initialize_database(path)

        self.assertTrue(path.exists())
        self.assertEqual(first.schema_version, "1")
        self.assertEqual(second.schema_version, "1")
        self.assertIn(second.search_backend, {"fts5", "like"})
        self.assertEqual(second.journal_mode.lower(), "wal")

    def test_writable_connection_pragmas_are_configured(self) -> None:
        path = self.db_path()
        initialize_database(path)

        connection = sqlite3.connect(path)
        try:
            busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
            foreign_keys_before = connection.execute("PRAGMA foreign_keys").fetchone()[0]
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            connection.close()

        self.assertGreaterEqual(busy_timeout, 0)
        self.assertEqual(foreign_keys_before, 0)
        self.assertEqual(journal_mode.lower(), "wal")

        from agent_memory.database import connect_writable

        writable = connect_writable(path)
        try:
            self.assertEqual(writable.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
            self.assertEqual(writable.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(writable.execute("PRAGMA synchronous").fetchone()[0], 1)
        finally:
            writable.close()

    def test_status_does_not_create_missing_database(self) -> None:
        path = self.db_path()

        status = inspect_database(path, "demo")

        self.assertFalse(path.exists())
        self.assertFalse(status.database_exists)
        self.assertFalse(status.initialized)
        self.assertEqual(status.search_backend, "unavailable")

    def test_status_reports_initialized_database(self) -> None:
        path = self.db_path()
        init_result = initialize_database(path)

        status = inspect_database(path, "demo")

        self.assertTrue(status.database_exists)
        self.assertTrue(status.initialized)
        self.assertEqual(status.schema_version, "1")
        self.assertEqual(status.total_memory_count, 0)
        self.assertEqual(status.project, "demo")
        self.assertEqual(status.journal_mode, "wal")
        self.assertTrue(status.wal_enabled)
        self.assertEqual(status.search_backend, init_result.search_backend)


if __name__ == "__main__":
    unittest.main()
