from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .database import inspect_database
from .service import MemoryService

SNAPSHOT_PATH = Path("docs") / "agent-memory.snapshot.json"
MARKDOWN_EXPORT_PATH = Path("docs") / "MEMORY.generated.md"
LIVE_DB_IGNORE_PATTERNS = (
    ".agent-memory/memory.db",
    ".agent-memory/memory.db-shm",
    ".agent-memory/memory.db-wal",
    ".agent-memory/*.tmp",
)


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    status: str
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class DoctorResult:
    project: str
    database_path: Path
    project_root: Path
    checks: tuple[DoctorCheck, ...]

    @property
    def failures(self) -> tuple[DoctorCheck, ...]:
        return tuple(check for check in self.checks if check.status == "fail")

    @property
    def warnings(self) -> tuple[DoctorCheck, ...]:
        return tuple(check for check in self.checks if check.status == "warn")

    @property
    def healthy(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "healthy": self.healthy,
            "project": self.project,
            "database": str(self.database_path),
            "project_root": str(self.project_root),
            "failure_count": len(self.failures),
            "warning_count": len(self.warnings),
            "checks": [check.to_dict() for check in self.checks],
            "failures": [check.to_dict() for check in self.failures],
            "warnings": [check.to_dict() for check in self.warnings],
        }


def run_doctor(*, database_path: Path, project_root: Path, project: str) -> DoctorResult:
    checks = [
        check_path_resolution(database_path, project_root),
        check_parent_writable(database_path),
    ]
    checks.extend(check_database(database_path, project))
    checks.extend(check_gitignore(project_root, database_path))
    checks.extend(check_tracked_exports(project_root))
    checks.append(check_snapshot_restore(project_root))
    return DoctorResult(project=project, database_path=database_path, project_root=project_root, checks=tuple(checks))


def pass_check(name: str, message: str, **details: Any) -> DoctorCheck:
    return DoctorCheck(name=name, status="pass", message=message, details=details)


def warn_check(name: str, message: str, **details: Any) -> DoctorCheck:
    return DoctorCheck(name=name, status="warn", message=message, details=details)


def fail_check(name: str, message: str, **details: Any) -> DoctorCheck:
    return DoctorCheck(name=name, status="fail", message=message, details=details)


def check_path_resolution(database_path: Path, project_root: Path) -> DoctorCheck:
    expected = (project_root / ".agent-memory" / "memory.db").resolve()
    if database_path.resolve() == expected:
        return pass_check("path_resolution", "Database path resolves to the project-local default.", expected=str(expected))
    return warn_check(
        "path_resolution",
        "Database path does not use the project-local default.",
        expected=str(expected),
        actual=str(database_path),
    )


def check_parent_writable(database_path: Path) -> DoctorCheck:
    parent = database_path.parent
    probe = parent / f"agent-memory-doctor-{uuid.uuid4().hex}.tmp"
    try:
        parent.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"doctor")
    except OSError as exc:
        return fail_check("database_parent_writable", "Database parent directory is not writable.", path=str(parent), error=str(exc))
    finally:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass
    return pass_check("database_parent_writable", "Database parent directory is writable.", path=str(parent))


def check_database(database_path: Path, project: str) -> list[DoctorCheck]:
    try:
        status = inspect_database(database_path, project)
    except Exception as exc:
        return [fail_check("database_readable", "Database could not be inspected.", database=str(database_path), error=str(exc))]

    checks: list[DoctorCheck] = []
    if not status.database_exists:
        checks.append(fail_check("database_exists", "Database does not exist.", database=str(database_path)))
        checks.append(fail_check("schema_version", "Schema version is unavailable because the database is missing."))
        checks.append(warn_check("wal_mode", "WAL mode cannot be checked because the database is missing."))
        checks.append(warn_check("fts_backend", "FTS backend cannot be checked because the database is missing."))
        return checks

    checks.append(pass_check("database_exists", "Database exists.", database=str(database_path)))
    if status.initialized and status.schema_version:
        checks.append(pass_check("schema_version", "Database schema is initialized.", schema_version=status.schema_version))
    else:
        checks.append(fail_check("schema_version", "Database exists but is not initialized.", schema_version=status.schema_version))

    if status.wal_enabled:
        checks.append(pass_check("wal_mode", "Database journal mode is WAL.", journal_mode=status.journal_mode))
    else:
        checks.append(warn_check("wal_mode", "Database journal mode is not WAL.", journal_mode=status.journal_mode))

    if status.search_backend in {"fts5", "like"}:
        severity = pass_check if status.search_backend == "fts5" else warn_check
        checks.append(severity("fts_backend", f"Search backend is {status.search_backend}.", search_backend=status.search_backend))
    else:
        checks.append(fail_check("fts_backend", "Search backend is unavailable.", search_backend=status.search_backend))

    checks.append(
        pass_check(
            "database_readable",
            "Database can be inspected read-only.",
            total_memory_count=status.total_memory_count,
            most_recent_update=status.most_recent_update,
        )
    )
    return checks


def check_gitignore(project_root: Path, database_path: Path) -> list[DoctorCheck]:
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        return [warn_check("live_db_ignored", ".gitignore is missing; live database files may be committed.", path=str(gitignore))]

    text = gitignore.read_text(encoding="utf-8")
    normalized = {line.strip().replace("\\", "/") for line in text.splitlines()}
    missing = [pattern for pattern in LIVE_DB_IGNORE_PATTERNS if pattern not in normalized]
    default_database = (project_root / ".agent-memory" / "memory.db").resolve()
    if database_path.resolve() != default_database:
        return [
            warn_check(
                "live_db_ignored",
                "Live database ignore rules are only checked for the project-local default path.",
                database=str(database_path),
                default_database=str(default_database),
            )
        ]
    if missing:
        return [warn_check("live_db_ignored", "Some live database ignore patterns are missing.", missing=missing)]
    return [pass_check("live_db_ignored", "Live SQLite database files are ignored by Git policy.", patterns=list(LIVE_DB_IGNORE_PATTERNS))]


def check_tracked_exports(project_root: Path) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    snapshot = project_root / SNAPSHOT_PATH
    markdown = project_root / MARKDOWN_EXPORT_PATH
    if snapshot.exists():
        checks.append(pass_check("snapshot_export_present", "JSON snapshot export exists.", path=str(snapshot), bytes=snapshot.stat().st_size))
    else:
        checks.append(warn_check("snapshot_export_present", "JSON snapshot export is missing.", path=str(snapshot)))
    if markdown.exists():
        checks.append(pass_check("markdown_export_present", "Markdown memory export exists.", path=str(markdown), bytes=markdown.stat().st_size))
    else:
        checks.append(warn_check("markdown_export_present", "Markdown memory export is missing.", path=str(markdown)))
    return checks


def check_snapshot_restore(project_root: Path) -> DoctorCheck:
    snapshot = project_root / SNAPSHOT_PATH
    if not snapshot.exists():
        return warn_check("snapshot_restore", "Snapshot restore was skipped because the JSON snapshot is missing.", path=str(snapshot))

    temp_root = project_root / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_db = temp_root / f"agent-memory-doctor-{uuid.uuid4().hex}.db"
    try:
        result = MemoryService(temp_db).import_json_snapshot(input_path=snapshot)
    except Exception as exc:
        return fail_check("snapshot_restore", "JSON snapshot could not be restored into a temporary database.", path=str(snapshot), error=str(exc))
    finally:
        cleanup_temp_database(temp_db)
    return pass_check(
        "snapshot_restore",
        "JSON snapshot restores into a temporary database.",
        path=str(snapshot),
        count=result["count"],
        inserted=result["inserted"],
        updated=result["updated"],
        unchanged=result["unchanged"],
        unkeyed_inserted=result["unkeyed_inserted"],
        mirrored_file_count=result.get("mirrored_file_count", 0),
        mirrored_files_inserted=result.get("mirrored_files_inserted", 0),
        mirrored_files_updated=result.get("mirrored_files_updated", 0),
        mirrored_files_unchanged=result.get("mirrored_files_unchanged", 0),
    )

def cleanup_temp_database(database_path: Path) -> None:
    for suffix in ("", "-shm", "-wal"):
        try:
            database_path.with_name(database_path.name + suffix).unlink(missing_ok=True)
        except OSError:
            pass
