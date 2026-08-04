from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .config import resolve_config
from .database import DatabaseError, initialize_database, inspect_database

SUCCESS = 0
GENERAL_ERROR = 1
USAGE_ERROR = 2
DATABASE_ERROR = 3


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

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize the memory database.",
        formatter_class=JsonHelpFormatter,
    )
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

    for command in ("put", "get", "search", "recent", "delete", "mirror-file", "export-md"):
        command_parser = subparsers.add_parser(
            command,
            help=f"{command} command placeholder. Implementation arrives in a later phase.",
            formatter_class=JsonHelpFormatter,
        )
        add_common_options(command_parser)
        command_parser.set_defaults(handler=handle_not_implemented)

    return parser


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to the SQLite memory database.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write a single machine-readable JSON object to stdout.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug details for unexpected errors.",
    )


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


def handle_not_implemented(args: argparse.Namespace) -> int:
    message = f"The '{args.command}' command is not implemented yet. See docs/BACKLOG.md for the phase plan."
    if args.json:
        write_json(
            {
                "ok": False,
                "error": {
                    "code": "NOT_IMPLEMENTED",
                    "message": message,
                },
            }
        )
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
    except DatabaseError as exc:
        return write_error(args, "DATABASE_ERROR", str(exc), DATABASE_ERROR)
    except Exception as exc:  # pragma: no cover - temporary safety until app exceptions exist.
        if getattr(args, "debug", False):
            raise
        return write_error(args, "UNEXPECTED_ERROR", str(exc), GENERAL_ERROR)


def write_error(args: argparse.Namespace, code: str, message: str, exit_code: int) -> int:
    if getattr(args, "json", False):
        write_json(
            {
                "ok": False,
                "error": {
                    "code": code,
                    "message": message,
                },
            }
        )
    else:
        print(f"agent-memory: {message}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
