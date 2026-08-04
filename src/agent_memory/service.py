from __future__ import annotations

from pathlib import Path

from .database import connect_writable, initialize_database
from .errors import DatabaseError, ValidationError
from .models import Memory, MemoryInput, PutResult, content_sha256, memory_from_row, serialize_tags


class MemoryService:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def put(self, memory: MemoryInput) -> PutResult:
        memory = validate_memory_input(memory)
        initialize_database(self.database_path)

        try:
            with connect_writable(self.database_path) as connection:
                with connection:
                    if memory.memory_key is None:
                        memory_id = insert_memory(connection, memory)
                        return PutResult("inserted", fetch_memory_by_id(connection, memory_id))

                    existing = connection.execute(
                        """
                        SELECT * FROM memories
                        WHERE project = ? AND scope = ? AND kind = ? AND memory_key = ?
                        """,
                        (memory.project, memory.scope, memory.kind, memory.memory_key),
                    ).fetchone()

                    if existing is None:
                        memory_id = insert_memory(connection, memory)
                        return PutResult("inserted", fetch_memory_by_id(connection, memory_id))

                    if memory_matches_existing(existing, memory):
                        return PutResult("unchanged", memory_from_row(existing))

                    connection.execute(
                        """
                        UPDATE memories
                        SET content = ?,
                            tags = ?,
                            source_agent = ?,
                            source_path = ?,
                            importance = ?,
                            content_sha256 = ?,
                            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE id = ?
                        """,
                        (
                            memory.content,
                            serialize_tags(memory.tags),
                            memory.source_agent,
                            memory.source_path,
                            memory.importance,
                            content_sha256(memory.content),
                            int(existing["id"]),
                        ),
                    )
                    return PutResult("updated", fetch_memory_by_id(connection, int(existing["id"])))
        except ValidationError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Could not write memory to database: {self.database_path}") from exc


def validate_memory_input(memory: MemoryInput) -> MemoryInput:
    normalized = memory.normalized()
    if not normalized.project:
        raise ValidationError("Project is required.")
    if not normalized.scope:
        raise ValidationError("Scope is required.")
    if not normalized.kind:
        raise ValidationError("Kind is required.")
    if not normalized.content.strip():
        raise ValidationError("Content is required.")
    if normalized.importance < 1 or normalized.importance > 5:
        raise ValidationError("Importance must be between 1 and 5.")
    return normalized


def insert_memory(connection, memory: MemoryInput) -> int:
    cursor = connection.execute(
        """
        INSERT INTO memories(
            project,
            scope,
            kind,
            memory_key,
            content,
            tags,
            source_agent,
            source_path,
            importance,
            content_sha256
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            memory.project,
            memory.scope,
            memory.kind,
            memory.memory_key,
            memory.content,
            serialize_tags(memory.tags),
            memory.source_agent,
            memory.source_path,
            memory.importance,
            content_sha256(memory.content),
        ),
    )
    return int(cursor.lastrowid)


def fetch_memory_by_id(connection, memory_id: int) -> Memory:
    row = connection.execute(
        "SELECT * FROM memories WHERE id = ?",
        (memory_id,),
    ).fetchone()
    if row is None:
        raise DatabaseError(f"Inserted memory could not be read back: {memory_id}")
    return memory_from_row(row)


def memory_matches_existing(row, memory: MemoryInput) -> bool:
    return (
        str(row["content"]) == memory.content
        and str(row["tags"]) == serialize_tags(memory.tags)
        and str(row["source_agent"]) == memory.source_agent
        and row["source_path"] == memory.source_path
        and int(row["importance"]) == memory.importance
        and str(row["content_sha256"]) == content_sha256(memory.content)
    )
