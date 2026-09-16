from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from .errors import DatabaseError

SCHEMA_VERSION = "2"

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    tags,
    content='memories',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS memories_after_insert
AFTER INSERT ON memories
BEGIN
    INSERT INTO memories_fts(rowid, content, tags)
    VALUES (new.id, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_after_delete
AFTER DELETE ON memories
BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, tags)
    VALUES ('delete', old.id, old.content, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_after_update
AFTER UPDATE ON memories
BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, tags)
    VALUES ('delete', old.id, old.content, old.tags);

    INSERT INTO memories_fts(rowid, content, tags)
    VALUES (new.id, new.content, new.tags);
END;
"""


@dataclass(frozen=True, slots=True)
class InitializeResult:
    database_path: Path
    schema_version: str | None
    fts5_available: bool
    search_backend: str
    journal_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "database": str(self.database_path),
            "schema_version": self.schema_version,
            "fts5_available": self.fts5_available,
            "search_backend": self.search_backend,
            "journal_mode": self.journal_mode,
        }


@dataclass(frozen=True, slots=True)
class StatusResult:
    database_path: Path
    database_exists: bool
    schema_version: str | None
    project: str
    total_memory_count: int | None
    search_backend: str
    journal_mode: str | None
    wal_enabled: bool | None
    most_recent_update: str | None
    initialized: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "database": str(self.database_path),
            "database_exists": self.database_exists,
            "schema_version": self.schema_version,
            "project": self.project,
            "total_memory_count": self.total_memory_count,
            "search_backend": self.search_backend,
            "journal_mode": self.journal_mode,
            "wal_enabled": self.wal_enabled,
            "most_recent_update": self.most_recent_update,
            "initialized": self.initialized,
        }


def initialize_database(database_path: Path) -> InitializeResult:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect_writable(database_path) as connection:
        existing_version = get_schema_version(connection)
        if existing_version == "1":
            back_up_database(connection, database_path, "schema-v1")
            migrate_v1_to_v2(connection)
        elif existing_version == SCHEMA_VERSION and mirror_timestamp_defaults_missing(connection):
            back_up_database(connection, database_path, "schema-v2-repair")
            repair_v2_mirror_defaults(connection)
        elif existing_version not in (None, SCHEMA_VERSION):
            raise DatabaseError(f"Unsupported database schema version: {existing_version}")
        schema_text = read_schema_text()
        with connection:
            connection.executescript(schema_text)
            fts5_available = detect_fts5(connection)
            if fts5_available:
                connection.executescript(FTS_SCHEMA)
        schema_version = get_schema_version(connection)
        journal_mode = get_journal_mode(connection)
        search_backend = "fts5" if has_memories_fts(connection) else "like"

    return InitializeResult(
        database_path=database_path,
        schema_version=schema_version,
        fts5_available=fts5_available,
        search_backend=search_backend,
        journal_mode=journal_mode,
    )


def back_up_database(connection: sqlite3.Connection, database_path: Path, label: str) -> Path:
    backup_path = database_path.with_name(f"{database_path.name}.{label}-{uuid.uuid4().hex}.bak")
    try:
        with sqlite3.connect(backup_path) as backup:
            connection.backup(backup)
    except sqlite3.Error as exc:
        backup_path.unlink(missing_ok=True)
        raise DatabaseError(f"Could not back up database before schema migration: {database_path}") from exc
    return backup_path


def migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
    """Keep the newest stored mirror for each path; retain the full v1 DB in a backup."""
    try:
        with connection:
            connection.execute(
                """CREATE TABLE mirrored_files_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    source_agent TEXT NOT NULL DEFAULT 'unknown',
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    UNIQUE(project, path)
                )"""
            )
            connection.execute(
                """INSERT INTO mirrored_files_v2
                   (id, project, path, content, content_sha256, source_agent, created_at, updated_at)
                   SELECT old.id, old.project, old.path, old.content, old.content_sha256,
                          old.source_agent, old.created_at, old.created_at
                   FROM mirrored_files AS old
                   WHERE old.id = (
                       SELECT MAX(newer.id) FROM mirrored_files AS newer
                       WHERE newer.project = old.project AND newer.path = old.path
                   )"""
            )
            connection.execute("DROP TABLE mirrored_files")
            connection.execute("ALTER TABLE mirrored_files_v2 RENAME TO mirrored_files")
            connection.execute("CREATE INDEX idx_mirrored_files_project_path ON mirrored_files(project, path)")
            connection.execute("UPDATE schema_metadata SET value = ? WHERE key = 'schema_version'", (SCHEMA_VERSION,))
    except sqlite3.Error as exc:
        raise DatabaseError("Could not migrate database schema from 1 to 2; the original database backup remains available.") from exc


def mirror_timestamp_defaults_missing(connection: sqlite3.Connection) -> bool:
    columns = {row["name"]: row["dflt_value"] for row in connection.execute("PRAGMA table_info(mirrored_files)")}
    return any(name in columns and columns[name] is None for name in ("created_at", "updated_at"))


def repair_v2_mirror_defaults(connection: sqlite3.Connection) -> None:
    """Repair databases migrated by an early version 2 build without defaults."""
    try:
        with connection:
            connection.execute(
                """CREATE TABLE mirrored_files_fixed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL, path TEXT NOT NULL, content TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL, source_agent TEXT NOT NULL DEFAULT 'unknown',
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    UNIQUE(project, path)
                )"""
            )
            connection.execute(
                """INSERT INTO mirrored_files_fixed
                   (id, project, path, content, content_sha256, source_agent, created_at, updated_at)
                   SELECT id, project, path, content, content_sha256, source_agent, created_at, updated_at
                   FROM mirrored_files"""
            )
            connection.execute("DROP TABLE mirrored_files")
            connection.execute("ALTER TABLE mirrored_files_fixed RENAME TO mirrored_files")
            connection.execute("CREATE INDEX idx_mirrored_files_project_path ON mirrored_files(project, path)")
    except sqlite3.Error as exc:
        raise DatabaseError("Could not repair mirrored file timestamp defaults; the original database backup remains available.") from exc


def inspect_database(database_path: Path, project: str) -> StatusResult:
    if not database_path.exists():
        return StatusResult(
            database_path=database_path,
            database_exists=False,
            schema_version=None,
            project=project,
            total_memory_count=None,
            search_backend="unavailable",
            journal_mode=None,
            wal_enabled=None,
            most_recent_update=None,
            initialized=False,
        )

    try:
        connection = connect_read_only(database_path)
    except sqlite3.Error as exc:
        raise DatabaseError(f"Could not open database for status: {database_path}") from exc

    with connection:
        schema_version = get_schema_version(connection)
        initialized = schema_version is not None and table_exists(connection, "memories")
        journal_mode = get_journal_mode(connection)
        search_backend = "fts5" if has_memories_fts(connection) else "like"
        total_memory_count = count_memories(connection) if initialized else None
        most_recent_update = get_most_recent_update(connection) if initialized else None

    return StatusResult(
        database_path=database_path,
        database_exists=True,
        schema_version=schema_version,
        project=project,
        total_memory_count=total_memory_count,
        search_backend=search_backend,
        journal_mode=journal_mode,
        wal_enabled=(journal_mode.lower() == "wal") if journal_mode else None,
        most_recent_update=most_recent_update,
        initialized=initialized,
    )


def connect_writable(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    apply_writable_pragmas(connection)
    return connection


def connect_read_only(database_path: Path) -> sqlite3.Connection:
    uri = database_path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def apply_writable_pragmas(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA synchronous = NORMAL")


def read_schema_text() -> str:
    return resources.files("agent_memory").joinpath("schema.sql").read_text(encoding="utf-8")


def detect_fts5(connection: sqlite3.Connection) -> bool:
    try:
        connection.execute("CREATE VIRTUAL TABLE temp.__agent_memory_fts5_probe USING fts5(content)")
        connection.execute("DROP TABLE temp.__agent_memory_fts5_probe")
        return True
    except sqlite3.Error:
        return False


def get_schema_version(connection: sqlite3.Connection) -> str | None:
    if not table_exists(connection, "schema_metadata"):
        return None
    row = connection.execute(
        "SELECT value FROM schema_metadata WHERE key = ?",
        ("schema_version",),
    ).fetchone()
    if row is None:
        return None
    return str(row["value"])


def get_journal_mode(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA journal_mode").fetchone()
    return str(row[0]) if row is not None else "unknown"


def has_memories_fts(connection: sqlite3.Connection) -> bool:
    return table_exists(connection, "memories_fts")


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'virtual table') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def count_memories(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COUNT(*) FROM memories").fetchone()
    return int(row[0])


def get_most_recent_update(connection: sqlite3.Connection) -> str | None:
    row = connection.execute("SELECT MAX(updated_at) FROM memories").fetchone()
    if row is None or row[0] is None:
        return None
    return str(row[0])
