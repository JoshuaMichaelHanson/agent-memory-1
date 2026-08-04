from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__

SUCCESS = 0
GENERAL_ERROR = 1
USAGE_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-memory",
        description="Store and retrieve durable AI-agent memory in SQLite.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"agent-memory {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    status_parser = subparsers.add_parser(
        "status",
        help="Show memory database status without mutating it.",
    )
    add_common_options(status_parser)
    status_parser.set_defaults(handler=handle_status)

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize the memory database. Implementation arrives in Phase 2.",
    )
    add_common_options(init_parser)
    init_parser.set_defaults(handler=handle_not_implemented)

    for command in ("put", "get", "search", "recent", "delete", "mirror-file", "export-md"):
        command_parser = subparsers.add_parser(
            command,
            help=f"{command} command placeholder. Implementation arrives in a later phase.",
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


def handle_status(args: argparse.Namespace) -> int:
    database = args.db
    exists = database.exists() if database is not None else False
    payload: dict[str, Any] = {
        "ok": True,
        "command": "status",
        "database": str(database) if database is not None else None,
        "database_exists": exists,
        "initialized": False,
        "message": "Database status is limited until Phase 2 implements configuration and schema inspection.",
    }

    if args.json:
        write_json(payload)
    else:
        if database is None:
            print("Database: not resolved yet")
        else:
            print(f"Database: {database}")
            print(f"Exists: {'yes' if exists else 'no'}")
        print("Initialized: unknown until Phase 2")
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
    except Exception as exc:  # pragma: no cover - temporary safety until app exceptions exist.
        if getattr(args, "debug", False):
            raise
        if getattr(args, "json", False):
            write_json(
                {
                    "ok": False,
                    "error": {
                        "code": "UNEXPECTED_ERROR",
                        "message": str(exc),
                    },
                }
            )
        else:
            print(f"agent-memory: {exc}", file=sys.stderr)
        return GENERAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
