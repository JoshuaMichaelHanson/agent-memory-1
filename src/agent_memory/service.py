from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from .database import connect_read_only, connect_writable, has_memories_fts, initialize_database
from .errors import DatabaseError, MemoryNotFoundError, ValidationError
from .models import Memory, MemoryInput, PutResult, content_sha256, memory_from_row, normalize_tags, serialize_tags

MAX_LIMIT = 100


class MemoryService:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def put(self, memory: MemoryInput) -> PutResult:
        memory = validate_memory_input(memory)

        try:
            initialize_database(self.database_path)
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

    def get_by_id(self, memory_id: int, *, touch: bool = True) -> Memory | None:
        if memory_id < 1:
            raise ValidationError("Memory ID must be a positive integer.")
        if not self.database_path.exists():
            return None

        try:
            if touch:
                with connect_writable(self.database_path) as connection:
                    with connection:
                        row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
                        if row is None:
                            return None
                        touch_memory(connection, memory_id)
                        return fetch_memory_by_id(connection, memory_id)

            with connect_read_only(self.database_path) as connection:
                row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
                return memory_from_row(row) if row is not None else None
        except ValidationError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Could not read memory from database: {self.database_path}") from exc

    def get_by_key(
        self,
        *,
        project: str,
        scope: str,
        kind: str,
        memory_key: str,
        touch: bool = True,
    ) -> Memory | None:
        project = project.strip()
        scope = scope.strip() or "project"
        kind = kind.strip() or "note"
        memory_key = memory_key.strip()
        if not project:
            raise ValidationError("Project is required for keyed lookup.")
        if not memory_key:
            raise ValidationError("Key is required for keyed lookup.")
        if not self.database_path.exists():
            return None

        try:
            if touch:
                with connect_writable(self.database_path) as connection:
                    with connection:
                        row = fetch_memory_key_row(connection, project, scope, kind, memory_key)
                        if row is None:
                            return None
                        memory_id = int(row["id"])
                        touch_memory(connection, memory_id)
                        return fetch_memory_by_id(connection, memory_id)

            with connect_read_only(self.database_path) as connection:
                row = fetch_memory_key_row(connection, project, scope, kind, memory_key)
                return memory_from_row(row) if row is not None else None
        except ValidationError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Could not read memory from database: {self.database_path}") from exc

    def search(
        self,
        *,
        project: str,
        query: str,
        limit: int = 10,
        scope: str | None = None,
        kind: str | None = None,
        tag: str | None = None,
        min_importance: int | None = None,
        touch: bool = True,
    ) -> list[dict[str, Any]]:
        project = validate_project(project)
        query = query.strip()
        if not query:
            raise ValidationError("Search query is required.")
        validate_limit(limit)
        validate_min_importance(min_importance)
        if not self.database_path.exists():
            return []

        try:
            connection_factory = connect_writable if touch else connect_read_only
            with connection_factory(self.database_path) as connection:
                with connection:
                    if has_memories_fts(connection):
                        results = search_fts(
                            connection,
                            project=project,
                            query=query,
                            limit=limit,
                            scope=scope,
                            kind=kind,
                            tag=tag,
                            min_importance=min_importance,
                        )
                    else:
                        results = search_like(
                            connection,
                            project=project,
                            query=query,
                            limit=limit,
                            scope=scope,
                            kind=kind,
                            tag=tag,
                            min_importance=min_importance,
                        )
                    if touch:
                        touch_search_results(connection, results)
                    return results
        except ValidationError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Could not search memories in database: {self.database_path}") from exc

    def recent(
        self,
        *,
        project: str,
        limit: int = 10,
        kind: str | None = None,
        min_importance: int | None = None,
    ) -> list[Memory]:
        project = validate_project(project)
        validate_limit(limit)
        validate_min_importance(min_importance)
        if not self.database_path.exists():
            return []

        clauses = ["project = ?"]
        parameters: list[object] = [project]
        if kind:
            clauses.append("kind = ?")
            parameters.append(kind.strip())
        if min_importance is not None:
            clauses.append("importance >= ?")
            parameters.append(min_importance)
        parameters.append(limit)

        try:
            with connect_read_only(self.database_path) as connection:
                rows = connection.execute(
                    f"""
                    SELECT * FROM memories
                    WHERE {' AND '.join(clauses)}
                    ORDER BY updated_at DESC, id DESC
                    LIMIT ?
                    """,
                    tuple(parameters),
                ).fetchall()
                return [memory_from_row(row) for row in rows]
        except Exception as exc:
            raise DatabaseError(f"Could not list recent memories from database: {self.database_path}") from exc


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


def validate_project(project: str) -> str:
    project = project.strip()
    if not project:
        raise ValidationError("Project is required.")
    return project


def validate_limit(limit: int) -> None:
    if limit < 1 or limit > MAX_LIMIT:
        raise ValidationError(f"Limit must be between 1 and {MAX_LIMIT}.")


def validate_min_importance(min_importance: int | None) -> None:
    if min_importance is not None and (min_importance < 1 or min_importance > 5):
        raise ValidationError("Minimum importance must be between 1 and 5.")


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
    row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if row is None:
        raise MemoryNotFoundError(f"Memory not found: {memory_id}")
    return memory_from_row(row)


def fetch_memory_key_row(connection, project: str, scope: str, kind: str, memory_key: str):
    return connection.execute(
        """
        SELECT * FROM memories
        WHERE project = ? AND scope = ? AND kind = ? AND memory_key = ?
        """,
        (project, scope, kind, memory_key),
    ).fetchone()


def search_fts(
    connection,
    *,
    project: str,
    query: str,
    limit: int,
    scope: str | None,
    kind: str | None,
    tag: str | None,
    min_importance: int | None,
) -> list[dict[str, Any]]:
    try:
        return execute_fts_search(
            connection,
            project=project,
            fts_query=query,
            limit=limit,
            scope=scope,
            kind=kind,
            tag=tag,
            min_importance=min_importance,
        )
    except sqlite3.OperationalError:
        tokenized_query = build_tokenized_fts_query(query)
        if not tokenized_query:
            return []
        return execute_fts_search(
            connection,
            project=project,
            fts_query=tokenized_query,
            limit=limit,
            scope=scope,
            kind=kind,
            tag=tag,
            min_importance=min_importance,
        )


def execute_fts_search(
    connection,
    *,
    project: str,
    fts_query: str,
    limit: int,
    scope: str | None,
    kind: str | None,
    tag: str | None,
    min_importance: int | None,
) -> list[dict[str, Any]]:
    clauses = ["m.project = ?", "memories_fts MATCH ?"]
    parameters: list[object] = [project, fts_query]
    append_filters(clauses, parameters, scope=scope, kind=kind, tag=tag, min_importance=min_importance)
    parameters.append(limit)
    rows = connection.execute(
        f"""
        SELECT m.*, bm25(memories_fts) AS score
        FROM memories_fts
        JOIN memories AS m ON m.id = memories_fts.rowid
        WHERE {' AND '.join(clauses)}
        ORDER BY m.importance DESC, score ASC, m.updated_at DESC, m.id DESC
        LIMIT ?
        """,
        tuple(parameters),
    ).fetchall()
    return rows_to_search_results(rows, "fts5")


def search_like(
    connection,
    *,
    project: str,
    query: str,
    limit: int,
    scope: str | None,
    kind: str | None,
    tag: str | None,
    min_importance: int | None,
) -> list[dict[str, Any]]:
    terms = split_query_terms(query)
    if not terms:
        return []
    clauses = ["project = ?"]
    parameters: list[object] = [project]
    for term in terms:
        clauses.append("(LOWER(content) LIKE ? ESCAPE '\\' OR LOWER(tags) LIKE ? ESCAPE '\\')")
        pattern = f"%{escape_like(term.lower())}%"
        parameters.extend([pattern, pattern])
    append_filters(clauses, parameters, scope=scope, kind=kind, tag=tag, min_importance=min_importance)
    parameters.append(limit)
    rows = connection.execute(
        f"""
        SELECT *, NULL AS score
        FROM memories
        WHERE {' AND '.join(clauses)}
        ORDER BY importance DESC, updated_at DESC, id DESC
        LIMIT ?
        """,
        tuple(parameters),
    ).fetchall()
    return rows_to_search_results(rows, "like")


def append_filters(
    clauses: list[str],
    parameters: list[object],
    *,
    scope: str | None,
    kind: str | None,
    tag: str | None,
    min_importance: int | None,
) -> None:
    if scope:
        clauses.append("scope = ?" if not clauses[0].startswith("m.") else "m.scope = ?")
        parameters.append(scope.strip())
    if kind:
        clauses.append("kind = ?" if not clauses[0].startswith("m.") else "m.kind = ?")
        parameters.append(kind.strip())
    if tag:
        normalized_tags = normalize_tags((tag,))
        if normalized_tags:
            clauses.append("(',' || tags || ',') LIKE ?" if not clauses[0].startswith("m.") else "(',' || m.tags || ',') LIKE ?")
            parameters.append(f"%,{normalized_tags[0]},%")
    if min_importance is not None:
        clauses.append("importance >= ?" if not clauses[0].startswith("m.") else "m.importance >= ?")
        parameters.append(min_importance)


def rows_to_search_results(rows, backend: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in rows:
        memory = memory_from_row(row)
        results.append(
            {
                "memory": memory.to_dict(),
                "score": row["score"],
                "search_backend": backend,
            }
        )
    return results


def touch_search_results(connection, results: list[dict[str, Any]]) -> None:
    ids = [int(result["memory"]["id"]) for result in results]
    for memory_id in ids:
        touch_memory(connection, memory_id)
    for result in results:
        memory = fetch_memory_by_id(connection, int(result["memory"]["id"]))
        result["memory"] = memory.to_dict()


def touch_memory(connection, memory_id: int) -> None:
    connection.execute(
        """
        UPDATE memories
        SET last_accessed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
            access_count = access_count + 1
        WHERE id = ?
        """,
        (memory_id,),
    )


def split_query_terms(query: str) -> list[str]:
    return re.findall(r"[\w]+", query, flags=re.UNICODE)


def build_tokenized_fts_query(query: str) -> str:
    terms = split_query_terms(query)
    return " ".join(f'"{term}"' for term in terms)


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def memory_matches_existing(row, memory: MemoryInput) -> bool:
    return (
        str(row["content"]) == memory.content
        and str(row["tags"]) == serialize_tags(memory.tags)
        and str(row["source_agent"]) == memory.source_agent
        and row["source_path"] == memory.source_path
        and int(row["importance"]) == memory.importance
        and str(row["content_sha256"]) == content_sha256(memory.content)
    )
