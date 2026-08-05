from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .config import resolve_config
from .database import initialize_database, inspect_database
from .doctor import run_doctor
from .errors import AgentMemoryError, FileOperationError, MemoryNotFoundError, ValidationError
from .models import Memory, MemoryInput
from .service import MemoryService

SUCCESS = 0
GENERAL_ERROR = 1
USAGE_ERROR = 2


class JsonHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-memory",
        description="Store and retrieve durable AI-agent memory in SQLite.",
        formatter_class=JsonHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"agent-memory {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    init_parser = subparsers.add_parser("init", help="Initialize the memory database.", formatter_class=JsonHelpFormatter)
    add_common_options(init_parser)
    init_parser.set_defaults(handler=handle_init)

    status_parser = subparsers.add_parser(
        "status",
        help="Show memory database status without mutating it.",
        formatter_class=JsonHelpFormatter,
    )
    add_common_options(status_parser)
    status_parser.add_argument(
        "--project",
        default=None,
        help="Project name to report status for. Defaults to the resolved project root name.",
    )
    status_parser.set_defaults(handler=handle_status)
    doctor_parser = subparsers.add_parser("doctor", help="Diagnose memory database and export setup.", formatter_class=JsonHelpFormatter)
    add_common_options(doctor_parser)
    doctor_parser.add_argument(
        "--project",
        default=None,
        help="Project name to diagnose. Defaults to the resolved project root name.",
    )
    doctor_parser.set_defaults(handler=handle_doctor)
    put_parser = subparsers.add_parser(
        "put",
        help="Store a memory, updating an existing keyed memory when one matches.",
        formatter_class=JsonHelpFormatter,
    )
    add_common_options(put_parser)
    put_parser.add_argument("--project", required=True, help="Project name for this memory.")
    put_parser.add_argument("--scope", default="project", help="Memory scope.")
    put_parser.add_argument("--kind", default="note", help="Memory kind.")
    put_parser.add_argument("--key", dest="memory_key", default=None, help="Stable key for keyed upserts.")
    put_parser.add_argument("--tag", action="append", default=[], help="Tag to apply. May be repeated.")
    put_parser.add_argument("--tags", default=None, help="Comma-separated tags to apply.")
    put_parser.add_argument("--importance", type=int, default=3, help="Importance from 1 to 5.")
    put_parser.add_argument("--agent", dest="source_agent", default="unknown", help="Agent or user writing the memory.")
    put_parser.add_argument("--source-path", default=None, help="Optional source path for this memory.")
    put_parser.add_argument("--allow-sensitive", action="store_true", help="Allow content that matches best-effort sensitive-value patterns.")
    content_group = put_parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument("--content", default=None, help="Memory content text.")
    content_group.add_argument("--content-file", type=Path, default=None, help="Read memory content from a UTF-8 file.")
    content_group.add_argument("--stdin", action="store_true", help="Read memory content from stdin.")
    put_parser.set_defaults(handler=handle_put)

    get_parser = subparsers.add_parser("get", help="Retrieve a memory by ID or compound key.", formatter_class=JsonHelpFormatter)
    add_common_options(get_parser)
    get_parser.add_argument("--id", dest="memory_id", type=int, default=None, help="Memory ID to retrieve.")
    get_parser.add_argument("--project", default=None, help="Project for keyed lookup.")
    get_parser.add_argument("--scope", default="project", help="Scope for keyed lookup.")
    get_parser.add_argument("--kind", default="note", help="Kind for keyed lookup.")
    get_parser.add_argument("--key", dest="memory_key", default=None, help="Memory key for keyed lookup.")
    get_parser.add_argument("--no-touch", action="store_true", help="Do not update access metadata.")
    get_parser.set_defaults(handler=handle_get)

    recent_parser = subparsers.add_parser("recent", help="List recently updated memories.", formatter_class=JsonHelpFormatter)
    add_common_options(recent_parser)
    recent_parser.add_argument("--project", required=True, help="Project to list memories for.")
    recent_parser.add_argument("--kind", default=None, help="Optional kind filter.")
    recent_parser.add_argument("--min-importance", type=int, default=None, help="Minimum importance from 1 to 5.")
    recent_parser.add_argument("--limit", type=int, default=10, help="Maximum records to return, from 1 to 100.")
    recent_parser.set_defaults(handler=handle_recent)

    search_parser = subparsers.add_parser("search", help="Search memories by content and tags.", formatter_class=JsonHelpFormatter)
    add_common_options(search_parser)
    search_parser.add_argument("query", help="Search query text.")
    search_parser.add_argument("--project", required=True, help="Project to search.")
    search_parser.add_argument("--scope", default=None, help="Optional scope filter.")
    search_parser.add_argument("--kind", default=None, help="Optional kind filter.")
    search_parser.add_argument("--tag", default=None, help="Optional exact tag filter.")
    search_parser.add_argument("--min-importance", type=int, default=None, help="Minimum importance from 1 to 5.")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum records to return, from 1 to 100.")
    search_parser.add_argument("--no-touch", action="store_true", help="Do not update access metadata.")
    search_parser.set_defaults(handler=handle_search)

    delete_parser = subparsers.add_parser("delete", help="Delete a memory by ID or compound key.", formatter_class=JsonHelpFormatter)
    add_common_options(delete_parser)
    delete_parser.add_argument("--id", dest="memory_id", type=int, default=None, help="Memory ID to delete.")
    delete_parser.add_argument("--project", default=None, help="Project for keyed deletion.")
    delete_parser.add_argument("--scope", default="project", help="Scope for keyed deletion.")
    delete_parser.add_argument("--kind", default="note", help="Kind for keyed deletion.")
    delete_parser.add_argument("--key", dest="memory_key", default=None, help="Memory key for keyed deletion.")
    delete_parser.add_argument("--yes", action="store_true", help="Delete without interactive confirmation.")
    delete_parser.set_defaults(handler=handle_delete)

    mirror_parser = subparsers.add_parser("mirror-file", help="Mirror one UTF-8 file revision into SQLite.", formatter_class=JsonHelpFormatter)
    add_common_options(mirror_parser)
    mirror_parser.add_argument("path", type=Path, help="File to mirror.")
    mirror_parser.add_argument("--project", required=True, help="Project name for the mirrored file.")
    mirror_parser.add_argument("--agent", dest="source_agent", default="unknown", help="Agent or user mirroring the file.")
    mirror_parser.add_argument("--allow-sensitive", action="store_true", help="Allow file content that matches best-effort sensitive-value patterns.")
    mirror_parser.set_defaults(handler=handle_mirror_file)

    export_parser = subparsers.add_parser("export-md", help="Export memories to generated Markdown.", formatter_class=JsonHelpFormatter)
    add_common_options(export_parser)
    export_parser.add_argument("--project", required=True, help="Project to export.")
    export_parser.add_argument("--output", type=Path, required=True, help="Markdown output path.")
    export_parser.add_argument("--limit", type=int, default=None, help="Optional maximum memories to export.")
    export_parser.add_argument("--min-importance", type=int, default=None, help="Minimum importance from 1 to 5.")
    export_parser.set_defaults(handler=handle_export_md)
    export_json_parser = subparsers.add_parser("export-json", help="Export memories to a restorable JSON snapshot.", formatter_class=JsonHelpFormatter)
    add_common_options(export_json_parser)
    export_json_parser.add_argument("--project", required=True, help="Project to export.")
    export_json_parser.add_argument("--output", type=Path, required=True, help="JSON snapshot output path.")
    export_json_parser.add_argument("--limit", type=int, default=None, help="Optional maximum memories to export.")
    export_json_parser.add_argument("--min-importance", type=int, default=None, help="Minimum importance from 1 to 5.")
    export_json_parser.set_defaults(handler=handle_export_json)

    import_json_parser = subparsers.add_parser("import-json", help="Import memories from a JSON snapshot.", formatter_class=JsonHelpFormatter)
    add_common_options(import_json_parser)
    import_json_parser.add_argument("path", type=Path, help="JSON snapshot to import.")
    import_json_parser.add_argument("--allow-sensitive", action="store_true", help="Allow snapshot content that matches best-effort sensitive-value patterns.")
    import_json_parser.set_defaults(handler=handle_import_json)
    return parser


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=None, help="Path to the SQLite memory database.")
    parser.add_argument("--json", action="store_true", help="Write a single machine-readable JSON object to stdout.")
    parser.add_argument("--debug", action="store_true", help="Show debug details for unexpected errors.")


def handle_init(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    result = initialize_database(config.database_path)
    payload = result.to_dict()
    payload["command"] = "init"
    payload["database_source"] = config.source
    payload["project_root"] = str(config.project_root)

    if args.json:
        write_json(payload)
    else:
        print(f"Database: {result.database_path}")
        print(f"Schema version: {result.schema_version}")
        print(f"Search backend: {result.search_backend}")
        print(f"FTS5 available: {'yes' if result.fts5_available else 'no'}")
        print(f"Journal mode: {result.journal_mode}")
    return SUCCESS


def handle_status(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    project = args.project or config.project_root.name
    result = inspect_database(config.database_path, project)
    payload = result.to_dict()
    payload["command"] = "status"
    payload["database_source"] = config.source
    payload["project_root"] = str(config.project_root)

    if args.json:
        write_json(payload)
    else:
        print(f"Database: {result.database_path}")
        print(f"Exists: {'yes' if result.database_exists else 'no'}")
        print(f"Initialized: {'yes' if result.initialized else 'no'}")
        print(f"Schema version: {result.schema_version or 'unknown'}")
        print(f"Project: {result.project}")
        print(f"Total memories: {result.total_memory_count if result.total_memory_count is not None else 'unknown'}")
        print(f"Search backend: {result.search_backend}")
        print(f"Journal mode: {result.journal_mode or 'unknown'}")
        print(f"Most recent update: {result.most_recent_update or 'none'}")
    return SUCCESS


def handle_doctor(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    project = args.project or config.project_root.name
    result = run_doctor(database_path=config.database_path, project_root=config.project_root, project=project)
    payload = result.to_dict()
    payload["command"] = "doctor"
    payload["database_source"] = config.source

    if args.json:
        write_json(payload)
    else:
        print(f"Healthy: {'yes' if result.healthy else 'no'}")
        print(f"Failures: {len(result.failures)}")
        print(f"Warnings: {len(result.warnings)}")
        for check in result.checks:
            print(f"[{check.status}] {check.name}: {check.message}")
    return SUCCESS

def handle_put(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    memory_input = MemoryInput(
        project=args.project,
        scope=args.scope,
        kind=args.kind,
        memory_key=args.memory_key,
        content=read_content(args),
        tags=collect_tags(args),
        source_agent=args.source_agent,
        source_path=args.source_path,
        importance=args.importance,
    )
    result = MemoryService(config.database_path).put(memory_input, allow_sensitive=args.allow_sensitive)
    payload = with_context(result.to_dict(), "put", config)

    if args.json:
        write_json(payload)
    else:
        memory = result.memory
        identifier = memory.memory_key or str(memory.id)
        print(f"{result.operation.capitalize()} memory {memory.id}: {memory.kind}/{identifier}")
    return SUCCESS


def handle_get(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    service = MemoryService(config.database_path)
    touch = not args.no_touch

    if args.memory_id is not None:
        if args.project or args.memory_key:
            raise ValidationError("Use either --id or keyed lookup options, not both.")
        memory = service.get_by_id(args.memory_id, touch=touch)
    else:
        if not args.project or not args.memory_key:
            raise ValidationError("Keyed lookup requires --project and --key when --id is not supplied.")
        memory = service.get_by_key(
            project=args.project,
            scope=args.scope,
            kind=args.kind,
            memory_key=args.memory_key,
            touch=touch,
        )

    if memory is None:
        raise MemoryNotFoundError("No memory matched the supplied lookup.")

    payload = with_context({"memory": memory.to_dict()}, "get", config)
    if args.json:
        write_json(payload)
    else:
        print_memory(memory)
    return SUCCESS


def handle_search(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    results = MemoryService(config.database_path).search(
        project=args.project,
        query=args.query,
        scope=args.scope,
        kind=args.kind,
        tag=args.tag,
        min_importance=args.min_importance,
        limit=args.limit,
        touch=not args.no_touch,
    )
    payload = with_context(
        {
            "project": args.project,
            "query": args.query,
            "count": len(results),
            "results": results,
        },
        "search",
        config,
    )

    if args.json:
        write_json(payload)
    else:
        if not results:
            print("No memories found.")
        for index, result in enumerate(results):
            if index:
                print()
                print("---")
                print()
            print_search_result(result)
    return SUCCESS

def handle_recent(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    memories = MemoryService(config.database_path).recent(
        project=args.project,
        kind=args.kind,
        min_importance=args.min_importance,
        limit=args.limit,
    )
    payload = with_context(
        {
            "project": args.project,
            "count": len(memories),
            "memories": [memory.to_dict() for memory in memories],
        },
        "recent",
        config,
    )

    if args.json:
        write_json(payload)
    else:
        if not memories:
            print("No memories found.")
        for index, memory in enumerate(memories):
            if index:
                print()
            print_memory_summary(memory)
    return SUCCESS


def handle_delete(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    require_delete_confirmation(args)
    service = MemoryService(config.database_path)

    if args.memory_id is not None:
        if args.project or args.memory_key:
            raise ValidationError("Use either --id or keyed deletion options, not both.")
        deleted = service.delete_by_id(args.memory_id)
        lookup = {"id": args.memory_id}
    else:
        if not args.project or not args.memory_key:
            raise ValidationError("Keyed deletion requires --project and --key when --id is not supplied.")
        deleted = service.delete_by_key(project=args.project, scope=args.scope, kind=args.kind, memory_key=args.memory_key)
        lookup = {"project": args.project, "scope": args.scope, "kind": args.kind, "memory_key": args.memory_key}

    if not deleted:
        raise MemoryNotFoundError("No memory matched the supplied deletion target.")

    payload = with_context({"deleted": True, "lookup": lookup}, "delete", config)
    if args.json:
        write_json(payload)
    else:
        print("Deleted memory.")
    return SUCCESS


def handle_mirror_file(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    result = MemoryService(config.database_path).mirror_file(
        project=args.project,
        path=args.path,
        source_agent=args.source_agent,
        project_root=config.project_root,
        allow_sensitive=args.allow_sensitive,
    )
    payload = with_context(result, "mirror-file", config)
    if args.json:
        write_json(payload)
    else:
        print(f"{result['operation'].capitalize()} mirrored file {result['revision_id']}: {result['path']}")
    return SUCCESS


def handle_export_md(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    result = MemoryService(config.database_path).export_markdown(
        project=args.project,
        output_path=args.output,
        limit=args.limit,
        min_importance=args.min_importance,
    )
    payload = with_context(result, "export-md", config)
    if args.json:
        write_json(payload)
    else:
        print(f"Exported {result['count']} memories to {result['output']}")
    return SUCCESS


def handle_export_json(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    result = MemoryService(config.database_path).export_json_snapshot(
        project=args.project,
        output_path=args.output,
        limit=args.limit,
        min_importance=args.min_importance,
    )
    payload = with_context(result, "export-json", config)
    if args.json:
        write_json(payload)
    else:
        print(f"Exported {result['count']} memories to {result['output']}")
    return SUCCESS


def handle_import_json(args: argparse.Namespace) -> int:
    config = resolve_config(args.db)
    result = MemoryService(config.database_path).import_json_snapshot(input_path=args.path, allow_sensitive=args.allow_sensitive)
    payload = with_context(result, "import-json", config)
    if args.json:
        write_json(payload)
    else:
        print(
            "Imported {count} memories from {input}: {inserted} inserted, {updated} updated, {unchanged} unchanged, {unkeyed_inserted} unkeyed inserted".format(
                **result
            )
        )
    return SUCCESS

def require_delete_confirmation(args: argparse.Namespace) -> None:
    if args.yes:
        return
    if args.json:
        raise ValidationError("Delete requires --yes when --json is used.")
    if not sys.stdin.isatty():
        raise ValidationError("Delete requires --yes when not running in an interactive terminal.")
    response = input("Delete matching memory? [y/N] ")
    if response.strip().lower() not in {"y", "yes"}:
        raise ValidationError("Delete cancelled.")

def read_content(args: argparse.Namespace) -> str:
    if args.content is not None:
        return args.content
    if args.content_file is not None:
        try:
            return args.content_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise FileOperationError(f"Could not read content file: {args.content_file}") from exc
        except UnicodeError as exc:
            raise FileOperationError(f"Content file is not valid UTF-8: {args.content_file}") from exc
    if args.stdin:
        return sys.stdin.read()
    raise ValidationError("Exactly one content source is required.")


def collect_tags(args: argparse.Namespace) -> tuple[str, ...]:
    tags: list[str] = list(args.tag or [])
    if args.tags:
        tags.extend(args.tags.split(","))
    return tuple(tags)


def with_context(payload: dict[str, Any], command: str, config) -> dict[str, Any]:
    payload["ok"] = True
    payload["command"] = command
    payload["database"] = str(config.database_path)
    payload["database_source"] = config.source
    payload["project_root"] = str(config.project_root)
    return payload


def print_memory(memory: Memory) -> None:
    print_memory_summary(memory)
    print()
    print(memory.content)


def print_search_result(result: dict[str, Any]) -> None:
    memory_payload = result["memory"]
    memory = Memory(**memory_payload)
    print_memory_summary(memory)
    if result.get("score") is not None:
        print(f"Score: {result['score']}")
    print()
    print(memory.content)

def print_memory_summary(memory: Memory) -> None:
    identifier = memory.memory_key or str(memory.id)
    tags = ", ".join(memory.tags) if memory.tags else "none"
    print(f"[{memory.id}] {memory.kind}/{identifier}")
    print(f"Project: {memory.project}")
    print(f"Importance: {memory.importance}")
    print(f"Updated: {memory.updated_at}")
    print(f"Accessed: {memory.last_accessed_at or 'never'} ({memory.access_count})")
    print(f"Tags: {tags}")


def handle_not_implemented(args: argparse.Namespace) -> int:
    message = f"The '{args.command}' command is not implemented yet. See docs/BACKLOG.md for the phase plan."
    if args.json:
        write_json({"ok": False, "error": {"code": "NOT_IMPLEMENTED", "message": message}})
    else:
        print(f"agent-memory: {message}", file=sys.stderr)
    return GENERAL_ERROR


def write_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help(sys.stderr)
        return USAGE_ERROR

    try:
        return int(handler(args))
    except AgentMemoryError as exc:
        return write_error(args, exc.code, str(exc), exc.exit_code)
    except Exception as exc:  # pragma: no cover - temporary safety until all app exceptions exist.
        if getattr(args, "debug", False):
            raise
        return write_error(args, "UNEXPECTED_ERROR", str(exc), GENERAL_ERROR)


def write_error(args: argparse.Namespace, code: str, message: str, exit_code: int) -> int:
    if getattr(args, "json", False):
        write_json({"ok": False, "error": {"code": code, "message": message}})
    else:
        print(f"agent-memory: {message}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
