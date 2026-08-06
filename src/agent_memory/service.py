from __future__ import annotations

import gc
import json
import os
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .database import connect_read_only, connect_writable, has_memories_fts, initialize_database
from .errors import DatabaseError, FileOperationError, MemoryNotFoundError, ValidationError
from .markdown import render_memory_export
from .models import Memory, MemoryInput, PutResult, content_sha256, memory_from_row, normalize_content, normalize_tags, serialize_tags
from .security import validate_no_sensitive_content

MAX_LIMIT = 100
PROJECT_LOCAL_DATABASE_LABEL = ".agent-memory/memory.db"


def export_source_database_label(database_path: Path) -> str:
    if database_path.name == "memory.db" and database_path.parent.name == ".agent-memory":
        return PROJECT_LOCAL_DATABASE_LABEL
    return str(database_path)


class MemoryService:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def put(self, memory: MemoryInput, *, allow_sensitive: bool = False) -> PutResult:
        memory = validate_memory_input(memory)
        validate_no_sensitive_content(memory.content, location="memory content", allow_sensitive=allow_sensitive)

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

    def copy_memory(
        self,
        *,
        target_project: str,
        source_id: int | None = None,
        source_project: str | None = None,
        source_scope: str = "project",
        source_kind: str = "note",
        source_key: str | None = None,
        target_scope: str | None = None,
        target_kind: str | None = None,
        target_key: str | None = None,
        source_agent: str = "unknown",
        allow_sensitive: bool = False,
    ) -> dict[str, Any]:
        if source_id is not None and (source_project or source_key):
            raise ValidationError("Use either --id or keyed source lookup options, not both.")
        if source_id is None and (not source_project or not source_key):
            raise ValidationError("Copy requires --id or --from-project and --from-key.")

        if source_id is not None:
            source = self.get_by_id(source_id, touch=False)
        else:
            assert source_project is not None
            assert source_key is not None
            source = self.get_by_key(
                project=source_project,
                scope=source_scope,
                kind=source_kind,
                memory_key=source_key,
                touch=False,
            )
        if source is None:
            raise MemoryNotFoundError("No memory matched the supplied copy source.")

        target_project = validate_project(target_project)
        target_scope = (target_scope if target_scope is not None else source.scope).strip() or source.scope
        target_kind = (target_kind if target_kind is not None else source.kind).strip() or source.kind
        copied_key = target_key.strip() if target_key is not None else source.memory_key
        if copied_key is not None and not copied_key:
            copied_key = None
        if copied_key is None:
            raise ValidationError("Copying an unkeyed memory requires --to-key.")

        result = self.put(
            MemoryInput(
                project=target_project,
                scope=target_scope,
                kind=target_kind,
                memory_key=copied_key,
                content=source.content,
                tags=source.tags,
                source_agent=source_agent,
                source_path=source.source_path,
                importance=source.importance,
            ),
            allow_sensitive=allow_sensitive,
        )
        return {
            "operation": result.operation,
            "source_memory": source.to_dict(),
            "memory": result.memory.to_dict(),
        }

    def delete_by_id(self, memory_id: int) -> bool:
        if memory_id < 1:
            raise ValidationError("Memory ID must be a positive integer.")
        if not self.database_path.exists():
            return False

        try:
            with connect_writable(self.database_path) as connection:
                with connection:
                    cursor = connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                    return cursor.rowcount > 0
        except Exception as exc:
            raise DatabaseError(f"Could not delete memory from database: {self.database_path}") from exc

    def delete_by_key(self, *, project: str, scope: str, kind: str, memory_key: str) -> bool:
        project = validate_project(project)
        scope = scope.strip() or "project"
        kind = kind.strip() or "note"
        memory_key = memory_key.strip()
        if not memory_key:
            raise ValidationError("Key is required for keyed deletion.")
        if not self.database_path.exists():
            return False

        try:
            with connect_writable(self.database_path) as connection:
                with connection:
                    cursor = connection.execute(
                        """
                        DELETE FROM memories
                        WHERE project = ? AND scope = ? AND kind = ? AND memory_key = ?
                        """,
                        (project, scope, kind, memory_key),
                    )
                    return cursor.rowcount > 0
        except Exception as exc:
            raise DatabaseError(f"Could not delete memory from database: {self.database_path}") from exc

    def mirror_file(
        self,
        *,
        project: str,
        path: Path,
        source_agent: str = "unknown",
        project_root: Path | None = None,
        allow_sensitive: bool = False,
    ) -> dict[str, Any]:
        project = validate_project(project)
        source_agent = source_agent.strip() or "unknown"
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise FileOperationError(f"Could not read file to mirror: {path}") from exc
        except UnicodeError as exc:
            raise FileOperationError(f"File is not valid UTF-8: {path}") from exc

        normalized_content = normalize_content(content)
        validate_no_sensitive_content(normalized_content, location=f"mirrored file {path}", allow_sensitive=allow_sensitive)
        digest = content_sha256(normalized_content)
        stored_path = display_path(path, project_root)

        try:
            initialize_database(self.database_path)
            with connect_writable(self.database_path) as connection:
                with connection:
                    existing = connection.execute(
                        """
                        SELECT id FROM mirrored_files
                        WHERE project = ? AND path = ? AND content_sha256 = ?
                        """,
                        (project, stored_path, digest),
                    ).fetchone()
                    if existing is not None:
                        return {
                            "operation": "unchanged",
                            "project": project,
                            "path": stored_path,
                            "content_sha256": digest,
                            "revision_id": int(existing["id"]),
                        }
                    cursor = connection.execute(
                        """
                        INSERT INTO mirrored_files(project, path, content, content_sha256, source_agent)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (project, stored_path, normalized_content, digest, source_agent),
                    )
                    return {
                        "operation": "inserted",
                        "project": project,
                        "path": stored_path,
                        "content_sha256": digest,
                        "revision_id": int(cursor.lastrowid),
                    }
        except FileOperationError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Could not mirror file into database: {self.database_path}") from exc

    def export_markdown(
        self,
        *,
        project: str,
        output_path: Path,
        limit: int | None = None,
        min_importance: int | None = None,
    ) -> dict[str, Any]:
        project = validate_project(project)
        if limit is not None:
            validate_limit(limit)
        validate_min_importance(min_importance)
        if not self.database_path.exists():
            memories: list[Memory] = []
        else:
            clauses = ["project = ?"]
            parameters: list[object] = [project]
            if min_importance is not None:
                clauses.append("importance >= ?")
                parameters.append(min_importance)
            limit_clause = ""
            if limit is not None:
                limit_clause = "LIMIT ?"
                parameters.append(limit)
            try:
                with connect_read_only(self.database_path) as connection:
                    rows = connection.execute(
                        f"""
                        SELECT * FROM memories
                        WHERE {' AND '.join(clauses)}
                        ORDER BY kind ASC, importance DESC, updated_at DESC, COALESCE(memory_key, printf('%012d', id)) ASC
                        {limit_clause}
                        """,
                        tuple(parameters),
                    ).fetchall()
                    memories = [memory_from_row(row) for row in rows]
            except Exception as exc:
                raise DatabaseError(f"Could not export memories from database: {self.database_path}") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        markdown = render_memory_export(project=project, source_database=export_source_database_label(self.database_path), memories=memories)
        tmp_path = output_path.with_name(f"{output_path.name}.{os.getpid()}.tmp")
        try:
            tmp_path.write_text(markdown, encoding="utf-8")
            os.replace(tmp_path, output_path)
        except OSError as exc:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise FileOperationError(f"Could not write Markdown export: {output_path}") from exc
        return {
            "project": project,
            "output": str(output_path),
            "count": len(memories),
        }

    def export_json_snapshot(
        self,
        *,
        project: str,
        output_path: Path,
        limit: int | None = None,
        min_importance: int | None = None,
        verify: bool = False,
    ) -> dict[str, Any]:
        project = validate_project(project)
        if limit is not None:
            validate_limit(limit)
        validate_min_importance(min_importance)
        memories = select_memories_for_export(
            self.database_path,
            project=project,
            limit=limit,
            min_importance=min_importance,
        )
        mirrored_files = select_mirrored_files_for_export(self.database_path, project=project)
        snapshot = {
            "format": "agent-memory.snapshot.v1",
            "project": project,
            "source_database": export_source_database_label(self.database_path),
            "exported_at": current_utc_timestamp(),
            "memories": [memory.to_dict() for memory in memories],
            "mirrored_files": mirrored_files,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.with_name(f"{output_path.name}.{os.getpid()}.tmp")
        try:
            tmp_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp_path, output_path)
        except OSError as exc:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise FileOperationError(f"Could not write JSON snapshot: {output_path}") from exc

        result = {
            "project": project,
            "output": str(output_path),
            "format": snapshot["format"],
            "count": len(memories),
            "memory_count": len(memories),
            "mirrored_file_count": len(mirrored_files),
        }
        if verify:
            result["verification"] = verify_json_snapshot_restore(output_path)
        return result

    def import_json_snapshot(self, *, input_path: Path, allow_sensitive: bool = False, dry_run: bool = False) -> dict[str, Any]:
        validation = validate_json_snapshot(input_path=input_path, allow_sensitive=allow_sensitive)
        if validation["error_count"]:
            raise ValidationError(format_snapshot_validation_errors(validation["errors"]))

        snapshot = validation["snapshot"]
        memories_payload = snapshot["memories"]
        mirrored_files_payload = snapshot["mirrored_files"]
        counts = {"inserted": 0, "updated": 0, "unchanged": 0, "unkeyed_inserted": 0}
        mirrored_file_counts = {"mirrored_files_inserted": 0, "mirrored_files_unchanged": 0}

        if dry_run:
            counts, mirrored_file_counts = classify_snapshot_import(
                self.database_path,
                memories_payload=memories_payload,
                mirrored_files_payload=mirrored_files_payload,
            )
        else:
            try:
                initialize_database(self.database_path)
                with connect_writable(self.database_path) as connection:
                    with connection:
                        for item in memories_payload:
                            operation = import_memory_snapshot(connection, item)
                            counts[operation] += 1
                        for item in mirrored_files_payload:
                            operation = import_mirrored_file_snapshot(connection, item)
                            mirrored_file_counts[operation] += 1
            except ValidationError:
                raise
            except Exception as exc:
                raise DatabaseError(f"Could not import JSON snapshot into database: {self.database_path}") from exc

        return {
            "format": snapshot["format"],
            "project": snapshot.get("project"),
            "input": str(input_path),
            "dry_run": dry_run,
            "count": len(memories_payload),
            "memory_count": len(memories_payload),
            "mirrored_file_count": len(mirrored_files_payload),
            "validation": snapshot_validation_public_payload(validation),
            **counts,
            **mirrored_file_counts,
        }

def validate_json_snapshot(*, input_path: Path, allow_sensitive: bool = False) -> dict[str, Any]:
    try:
        raw_snapshot = json.loads(input_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FileOperationError(f"Could not read JSON snapshot: {input_path}") from exc
    except UnicodeError as exc:
        raise FileOperationError(f"Snapshot is not valid UTF-8: {input_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Snapshot is not valid JSON: {input_path}") from exc

    errors: list[str] = []
    warnings: list[str] = []
    memories_payload: list[Any] = []
    mirrored_files_payload: list[Any] = []
    unkeyed_memory_count = 0

    if not isinstance(raw_snapshot, dict):
        errors.append("Snapshot root must be an object.")
        snapshot: dict[str, Any] = {"format": None, "project": None, "memories": [], "mirrored_files": []}
    else:
        snapshot = dict(raw_snapshot)
        if snapshot.get("format") != "agent-memory.snapshot.v1":
            errors.append("Snapshot format must be agent-memory.snapshot.v1.")

        raw_memories = snapshot.get("memories")
        if isinstance(raw_memories, list):
            memories_payload = raw_memories
        else:
            errors.append("Snapshot must contain a memories array.")

        raw_mirrored_files = snapshot.get("mirrored_files", [])
        if isinstance(raw_mirrored_files, list):
            mirrored_files_payload = raw_mirrored_files
        else:
            errors.append("Snapshot mirrored_files must be an array when supplied.")

    for index, item in enumerate(memories_payload):
        try:
            memory, _, _, _, _ = memory_input_from_snapshot(item)
        except ValidationError as exc:
            errors.append(f"memories[{index}]: {exc}")
            continue
        try:
            validate_no_sensitive_content(memory.content, location=f"JSON snapshot memories[{index}] content", allow_sensitive=allow_sensitive)
        except ValidationError as exc:
            errors.append(f"memories[{index}]: {exc}")
        if memory.memory_key is None:
            unkeyed_memory_count += 1

    for index, item in enumerate(mirrored_files_payload):
        try:
            mirrored_file = mirrored_file_from_snapshot(item)
        except ValidationError as exc:
            errors.append(f"mirrored_files[{index}]: {exc}")
            continue
        try:
            validate_no_sensitive_content(
                mirrored_file["content"],
                location=f"JSON snapshot mirrored_files[{index}] content",
                allow_sensitive=allow_sensitive,
            )
        except ValidationError as exc:
            errors.append(f"mirrored_files[{index}]: {exc}")

    if unkeyed_memory_count:
        noun = "memory" if unkeyed_memory_count == 1 else "memories"
        warnings.append(
            f"Snapshot contains {unkeyed_memory_count} unkeyed {noun}; repeated real imports create new rows. Use stable keys for shared durable memory."
        )

    snapshot["memories"] = memories_payload
    snapshot["mirrored_files"] = mirrored_files_payload
    return {
        "snapshot": snapshot,
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "memory_count": len(memories_payload),
        "mirrored_file_count": len(mirrored_files_payload),
        "unkeyed_memory_count": unkeyed_memory_count,
    }


def snapshot_validation_public_payload(validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": validation["error_count"] == 0,
        "error_count": validation["error_count"],
        "warning_count": validation["warning_count"],
        "errors": validation["errors"],
        "warnings": validation["warnings"],
        "memory_count": validation["memory_count"],
        "mirrored_file_count": validation["mirrored_file_count"],
        "unkeyed_memory_count": validation["unkeyed_memory_count"],
    }


def format_snapshot_validation_errors(errors: list[str]) -> str:
    return f"Snapshot validation failed with {len(errors)} error(s): " + " | ".join(errors)


def classify_snapshot_import(
    database_path: Path,
    *,
    memories_payload: list[Any],
    mirrored_files_payload: list[Any],
) -> tuple[dict[str, int], dict[str, int]]:
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "unkeyed_inserted": 0}
    mirrored_file_counts = {"mirrored_files_inserted": 0, "mirrored_files_unchanged": 0}
    if not database_path.exists():
        return classify_snapshot_against_empty_database(memories_payload, mirrored_files_payload)

    try:
        with connect_read_only(database_path) as connection:
            memories_available = table_exists_for_connection(connection, "memories")
            mirrored_files_available = table_exists_for_connection(connection, "mirrored_files")
            if not memories_available and not mirrored_files_available:
                return classify_snapshot_against_empty_database(memories_payload, mirrored_files_payload)

            for item in memories_payload:
                memory, _, _, _, _ = memory_input_from_snapshot(item)
                if memory.memory_key is None:
                    counts["unkeyed_inserted"] += 1
                elif not memories_available:
                    counts["inserted"] += 1
                else:
                    existing = fetch_memory_key_row(connection, memory.project, memory.scope, memory.kind, memory.memory_key)
                    if existing is None:
                        counts["inserted"] += 1
                    elif memory_matches_existing(existing, memory):
                        counts["unchanged"] += 1
                    else:
                        counts["updated"] += 1

            for item in mirrored_files_payload:
                mirrored_file = mirrored_file_from_snapshot(item)
                if not mirrored_files_available:
                    mirrored_file_counts["mirrored_files_inserted"] += 1
                    continue
                existing = connection.execute(
                    """
                    SELECT id FROM mirrored_files
                    WHERE project = ? AND path = ? AND content_sha256 = ?
                    """,
                    (mirrored_file["project"], mirrored_file["path"], mirrored_file["content_sha256"]),
                ).fetchone()
                operation = "mirrored_files_unchanged" if existing is not None else "mirrored_files_inserted"
                mirrored_file_counts[operation] += 1
    except ValidationError:
        raise
    except Exception as exc:
        raise DatabaseError(f"Could not dry-run JSON snapshot import against database: {database_path}") from exc
    return counts, mirrored_file_counts


def classify_snapshot_against_empty_database(
    memories_payload: list[Any],
    mirrored_files_payload: list[Any],
) -> tuple[dict[str, int], dict[str, int]]:
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "unkeyed_inserted": 0}
    for item in memories_payload:
        memory, _, _, _, _ = memory_input_from_snapshot(item)
        if memory.memory_key is None:
            counts["unkeyed_inserted"] += 1
        else:
            counts["inserted"] += 1
    return counts, {"mirrored_files_inserted": len(mirrored_files_payload), "mirrored_files_unchanged": 0}


def table_exists_for_connection(connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'virtual table') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def verify_json_snapshot_restore(snapshot_path: Path) -> dict[str, Any]:
    temp_db = snapshot_path.with_name(f"{snapshot_path.name}.{os.getpid()}.verify.db")
    cleanup_sqlite_database(temp_db)
    try:
        result = MemoryService(temp_db).import_json_snapshot(input_path=snapshot_path)
    finally:
        cleanup_sqlite_database(temp_db)
    return {
        "ok": True,
        "memory_count": result["memory_count"],
        "mirrored_file_count": result["mirrored_file_count"],
        "inserted": result["inserted"],
        "updated": result["updated"],
        "unchanged": result["unchanged"],
        "unkeyed_inserted": result["unkeyed_inserted"],
        "mirrored_files_inserted": result["mirrored_files_inserted"],
        "mirrored_files_unchanged": result["mirrored_files_unchanged"],
    }


def cleanup_sqlite_database(database_path: Path) -> None:
    gc.collect()
    for suffix in ("", "-shm", "-wal"):
        try:
            database_path.with_name(database_path.name + suffix).unlink(missing_ok=True)
        except OSError:
            pass

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
        results.append({"memory": memory.to_dict(), "score": row["score"], "search_backend": backend})
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


def display_path(path: Path, project_root: Path | None) -> str:
    resolved = path.resolve()
    if project_root is not None:
        try:
            return str(resolved.relative_to(project_root.resolve()))
        except ValueError:
            pass
    return str(path)


def select_memories_for_export(
    database_path: Path,
    *,
    project: str,
    limit: int | None = None,
    min_importance: int | None = None,
) -> list[Memory]:
    if not database_path.exists():
        return []
    clauses = ["project = ?"]
    parameters: list[object] = [project]
    if min_importance is not None:
        clauses.append("importance >= ?")
        parameters.append(min_importance)
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT ?"
        parameters.append(limit)
    with connect_read_only(database_path) as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM memories
            WHERE {' AND '.join(clauses)}
            ORDER BY kind ASC, importance DESC, updated_at DESC, COALESCE(memory_key, printf('%012d', id)) ASC
            {limit_clause}
            """,
            tuple(parameters),
        ).fetchall()
        return [memory_from_row(row) for row in rows]




def select_mirrored_files_for_export(database_path: Path, *, project: str) -> list[dict[str, Any]]:
    if not database_path.exists():
        return []
    with connect_read_only(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, project, path, content, content_sha256, source_agent, created_at
            FROM mirrored_files
            WHERE project = ?
            ORDER BY path ASC, created_at ASC, id ASC
            """,
            (project,),
        ).fetchall()
        return [mirrored_file_row_to_dict(row) for row in rows]


def mirrored_file_row_to_dict(row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "project": str(row["project"]),
        "path": str(row["path"]),
        "content": str(row["content"]),
        "content_sha256": str(row["content_sha256"]),
        "source_agent": str(row["source_agent"]),
        "created_at": str(row["created_at"]),
    }


def mirrored_file_from_snapshot(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValidationError("Each snapshot mirrored file must be an object.")
    project = str(item.get("project", "")).strip()
    path = str(item.get("path", "")).strip()
    content = normalize_content(str(item.get("content", "")))
    source_agent = str(item.get("source_agent", "unknown")).strip() or "unknown"
    created_at = str(item.get("created_at") or current_utc_timestamp())
    if not project:
        raise ValidationError("Snapshot mirrored file project is required.")
    if not path:
        raise ValidationError("Snapshot mirrored file path is required.")
    expected_hash = item.get("content_sha256")
    digest = content_sha256(content)
    if expected_hash is not None and str(expected_hash) != digest:
        raise ValidationError(f"Snapshot mirrored file hash mismatch for {path}.")
    return {
        "project": project,
        "path": path,
        "content": content,
        "content_sha256": digest,
        "source_agent": source_agent,
        "created_at": created_at,
    }


def import_mirrored_file_snapshot(connection, item: Any) -> str:
    mirrored_file = mirrored_file_from_snapshot(item)
    existing = connection.execute(
        """
        SELECT id FROM mirrored_files
        WHERE project = ? AND path = ? AND content_sha256 = ?
        """,
        (mirrored_file["project"], mirrored_file["path"], mirrored_file["content_sha256"]),
    ).fetchone()
    if existing is not None:
        return "mirrored_files_unchanged"
    connection.execute(
        """
        INSERT INTO mirrored_files(project, path, content, content_sha256, source_agent, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            mirrored_file["project"],
            mirrored_file["path"],
            mirrored_file["content"],
            mirrored_file["content_sha256"],
            mirrored_file["source_agent"],
            mirrored_file["created_at"],
        ),
    )
    return "mirrored_files_inserted"

def import_memory_snapshot(connection, item: Any) -> str:
    memory, created_at, updated_at, last_accessed_at, access_count = memory_input_from_snapshot(item)
    if memory.memory_key is None:
        insert_memory_snapshot(connection, memory, created_at, updated_at, last_accessed_at, access_count)
        return "unkeyed_inserted"

    existing = fetch_memory_key_row(connection, memory.project, memory.scope, memory.kind, memory.memory_key)
    if existing is None:
        insert_memory_snapshot(connection, memory, created_at, updated_at, last_accessed_at, access_count)
        return "inserted"
    if memory_matches_existing(existing, memory):
        return "unchanged"

    connection.execute(
        """
        UPDATE memories
        SET content = ?,
            tags = ?,
            source_agent = ?,
            source_path = ?,
            importance = ?,
            content_sha256 = ?,
            updated_at = ?,
            last_accessed_at = ?,
            access_count = ?
        WHERE id = ?
        """,
        (
            memory.content,
            serialize_tags(memory.tags),
            memory.source_agent,
            memory.source_path,
            memory.importance,
            content_sha256(memory.content),
            updated_at,
            last_accessed_at,
            access_count,
            int(existing["id"]),
        ),
    )
    return "updated"


def memory_input_from_snapshot(item: Any) -> tuple[MemoryInput, str, str, str | None, int]:
    if not isinstance(item, dict):
        raise ValidationError("Each snapshot memory must be an object.")
    tags = item.get("tags", [])
    if not isinstance(tags, list):
        raise ValidationError("Snapshot memory tags must be an array.")
    try:
        importance = int(item.get("importance", 3))
        access_count = int(item.get("access_count", 0) or 0)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Snapshot memory importance and access_count must be integers.") from exc

    memory = validate_memory_input(
        MemoryInput(
            project=str(item.get("project", "")),
            scope=str(item.get("scope", "project")),
            kind=str(item.get("kind", "note")),
            memory_key=item.get("memory_key"),
            content=str(item.get("content", "")),
            tags=tuple(str(tag) for tag in tags),
            source_agent=str(item.get("source_agent", "unknown")),
            source_path=item.get("source_path"),
            importance=importance,
        )
    )
    expected_hash = item.get("content_sha256")
    if expected_hash is not None and str(expected_hash) != content_sha256(memory.content):
        raise ValidationError(f"Snapshot memory hash mismatch for {memory.kind}/{memory.memory_key or 'unkeyed'}.")

    now = current_utc_timestamp()
    created_at = str(item.get("created_at") or now)
    updated_at = str(item.get("updated_at") or created_at)
    last_accessed_raw = item.get("last_accessed_at")
    last_accessed_at = str(last_accessed_raw) if last_accessed_raw else None
    return memory, created_at, updated_at, last_accessed_at, max(access_count, 0)


def insert_memory_snapshot(
    connection,
    memory: MemoryInput,
    created_at: str,
    updated_at: str,
    last_accessed_at: str | None,
    access_count: int,
) -> int:
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
            content_sha256,
            created_at,
            updated_at,
            last_accessed_at,
            access_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            created_at,
            updated_at,
            last_accessed_at,
            access_count,
        ),
    )
    return int(cursor.lastrowid)


def current_utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def memory_matches_existing(row, memory: MemoryInput) -> bool:
    return (
        str(row["content"]) == memory.content
        and str(row["tags"]) == serialize_tags(memory.tags)
        and str(row["source_agent"]) == memory.source_agent
        and row["source_path"] == memory.source_path
        and int(row["importance"]) == memory.importance
        and str(row["content_sha256"]) == content_sha256(memory.content)
    )
