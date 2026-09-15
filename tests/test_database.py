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
        self.assertEqual(first.schema_version, "2")
        self.assertEqual(second.schema_version, "2")
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
        self.assertEqual(status.schema_version, "2")
        self.assertEqual(status.total_memory_count, 0)
        self.assertEqual(status.project, "demo")
        self.assertEqual(status.journal_mode, "wal")
        self.assertTrue(status.wal_enabled)
        self.assertEqual(status.search_backend, init_result.search_backend)

    def test_v1_migration_keeps_latest_mirror_and_backs_up_database(self) -> None:
        path = self.db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.executescript("""
                CREATE TABLE schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO schema_metadata VALUES ('schema_version', '1');
                CREATE TABLE mirrored_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, path TEXT NOT NULL,
                    content TEXT NOT NULL, content_sha256 TEXT NOT NULL,
                    source_agent TEXT NOT NULL DEFAULT 'unknown', created_at TEXT NOT NULL,
                    UNIQUE(project, path, content_sha256)
                );
                CREATE INDEX idx_mirrored_files_project_path ON mirrored_files(project, path);
                INSERT INTO mirrored_files VALUES (1, 'demo', 'AGENTS.md', 'old', 'old-hash', 'codex', '2025-01-01');
                INSERT INTO mirrored_files VALUES (2, 'demo', 'AGENTS.md', 'new', 'new-hash', 'codex', '2025-01-02');
            """)

        result = initialize_database(path)
        backups = list(path.parent.glob(f"{path.name}.schema-v1-*.bak"))
        self.assertEqual(len(backups), 1)
        with sqlite3.connect(path) as connection:
            rows = connection.execute("SELECT id, content FROM mirrored_files").fetchall()
        with sqlite3.connect(backups[0]) as connection:
            old_count = connection.execute("SELECT COUNT(*) FROM mirrored_files").fetchone()[0]

        self.assertEqual(result.schema_version, "2")
        self.assertEqual(rows, [(2, "new")])
        self.assertEqual(old_count, 2)
        with sqlite3.connect(path) as connection:
            connection.execute("INSERT INTO mirrored_files(project, path, content, content_sha256) VALUES ('demo', 'README.md', 'text', 'hash')")

    def test_v2_repairs_missing_mirror_timestamp_defaults(self) -> None:
        path = self.db_path()
        initialize_database(path)
        with sqlite3.connect(path) as connection:
            connection.executescript("""
                DROP TABLE mirrored_files;
                CREATE TABLE mirrored_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, path TEXT NOT NULL,
                    content TEXT NOT NULL, content_sha256 TEXT NOT NULL,
                    source_agent TEXT NOT NULL DEFAULT 'unknown',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(project, path)
                );
                INSERT INTO mirrored_files VALUES (1, 'demo', 'AGENTS.md', 'text', 'hash', 'codex', '2025-01-01', '2025-01-01');
            """)

        initialize_database(path)
        with sqlite3.connect(path) as connection:
            connection.execute("INSERT INTO mirrored_files(project, path, content, content_sha256) VALUES ('demo', 'README.md', 'text', 'hash')")
            count = connection.execute("SELECT COUNT(*) FROM mirrored_files").fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
