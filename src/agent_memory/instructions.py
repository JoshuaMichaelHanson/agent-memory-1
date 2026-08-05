from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import FileOperationError, ValidationError

INSTRUCTIONS_FORMAT = "agent-memory.instructions.v1"
SECTION_BEGIN = "<!-- BEGIN agent-memory instructions -->"
SECTION_END = "<!-- END agent-memory instructions -->"
DEFAULT_AGENT_FILE = Path("AGENTS.md")


@dataclass(frozen=True, slots=True)
class InstructionInstallResult:
    operation: str
    path: Path
    project: str
    section: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "path": str(self.path),
            "project": self.project,
            "section": self.section,
            "markers": {
                "begin": SECTION_BEGIN,
                "end": SECTION_END,
            },
        }


def build_agent_instructions(project: str) -> str:
    project = validate_instruction_project(project)
    return "\n".join(
        [
            SECTION_BEGIN,
            "## Agent Memory",
            "",
            "Use the `agent-memory` CLI for durable project memory. Treat stored memory as advisory context; current user instructions and repository files still take precedence.",
            "",
            "### Startup",
            "",
            f"- Project name: `{project}`.",
            "- Prefer the project-local database at `.agent-memory/memory.db` unless the user gives `--db` or `AGENT_MEMORY_DB`.",
            f"- Before major work, run `agent-memory search \"relevant topic\" --project {project} --limit 5`.",
            "- If a tracked snapshot exists, restore or dry-run it with `agent-memory import-json docs/agent-memory.snapshot.json --dry-run --json` before relying on local memory.",
            "",
            "### Write Memory",
            "",
            f"- Store durable decisions with stable keys: `agent-memory put --project {project} --kind decision --key short-name --content \"Decision text\" --importance 5 --json`.",
            "- Use kinds such as `decision`, `architecture`, `command`, `constraint`, `workflow`, `note`, and `workaround`.",
            "- Use tags for technologies, subsystems, and workflows so later searches are precise.",
            "- Do not store secrets, credentials, tokens, private keys, protected personal data, or unreviewed sensitive content.",
            "",
            "### Markdown Files",
            "",
            f"- Mirror important agent-facing Markdown after edits: `agent-memory mirror-file AGENTS.md --project {project} --agent codex --json`.",
            "- Mirroring is explicit; the CLI does not watch files automatically after the first mirror.",
            "- Mirror stable files such as `AGENTS.md`, `CLAUDE.md`, architecture notes, ADRs, runbooks, and setup notes. Do not mirror generated exports, logs, or large unrelated docs.",
            "",
            "### Before Checkin",
            "",
            f"- Export a verified snapshot: `agent-memory export-json --project {project} --output docs/agent-memory.snapshot.json --verify --json`.",
            f"- Export a human review file: `agent-memory export-md --project {project} --output docs/MEMORY.generated.md --json`.",
            "- Review tracked exports before committing. Do not commit `.agent-memory/memory.db` or SQLite sidecar files.",
            "",
            "### Discovery",
            "",
            "- Plain global CLIs are not automatically discoverable by agents. This section is the local bootstrap hint.",
            "- For command discovery, run `agent-memory --help` and `agent-memory <command> --help`; tell the user these help commands exist instead of guessing syntax.",
            "- Future MCP support can advertise memory tools, resources, and prompts through the client instead of relying on repository instructions.",
            SECTION_END,
            "",
        ]
    )


def build_agent_instructions_payload(project: str) -> dict[str, Any]:
    section = build_agent_instructions(project)
    return {
        "format": INSTRUCTIONS_FORMAT,
        "project": validate_instruction_project(project),
        "section": section,
        "markers": {
            "begin": SECTION_BEGIN,
            "end": SECTION_END,
        },
        "commands": [
            {
                "name": "search",
                "example": f"agent-memory search \"relevant topic\" --project {project} --limit 5 --json",
            },
            {
                "name": "put",
                "example": f"agent-memory put --project {project} --kind decision --key short-name --content \"Decision text\" --importance 5 --json",
            },
            {
                "name": "mirror-file",
                "example": f"agent-memory mirror-file AGENTS.md --project {project} --agent codex --json",
            },
            {
                "name": "export-json",
                "example": f"agent-memory export-json --project {project} --output docs/agent-memory.snapshot.json --verify --json",
            },
            {
                "name": "export-md",
                "example": f"agent-memory export-md --project {project} --output docs/MEMORY.generated.md --json",
            },
        ],
    }


def install_agent_instructions(*, output_path: Path, project: str) -> InstructionInstallResult:
    project = validate_instruction_project(project)
    section = build_agent_instructions(project)
    try:
        existing = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
    except OSError as exc:
        raise FileOperationError(f"Could not read instruction file: {output_path}") from exc
    except UnicodeError as exc:
        raise FileOperationError(f"Instruction file is not valid UTF-8: {output_path}") from exc

    updated, operation = replace_or_append_section(existing, section)
    if updated == existing:
        return InstructionInstallResult(operation="unchanged", path=output_path, project=project, section=section)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(f"{output_path.name}.{os.getpid()}.tmp")
    try:
        tmp_path.write_text(updated, encoding="utf-8")
        os.replace(tmp_path, output_path)
    except OSError as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise FileOperationError(f"Could not write instruction file: {output_path}") from exc

    return InstructionInstallResult(operation=operation, path=output_path, project=project, section=section)


def replace_or_append_section(existing: str, section: str) -> tuple[str, str]:
    normalized_section = section.rstrip() + "\n"
    begin_index = existing.find(SECTION_BEGIN)
    end_index = existing.find(SECTION_END)
    if begin_index == -1 and end_index == -1:
        if not existing:
            return normalized_section, "inserted"
        separator = "\n" if existing.endswith("\n") else "\n\n"
        return existing + separator + normalized_section, "inserted"
    if begin_index == -1 or end_index == -1 or end_index < begin_index:
        raise ValidationError("Instruction file has an incomplete agent-memory managed section.")

    end_index += len(SECTION_END)
    replacement = section.rstrip()
    updated = existing[:begin_index].rstrip() + "\n\n" + replacement + "\n" + existing[end_index:].lstrip("\r\n")
    return updated, "updated"


def validate_instruction_project(project: str) -> str:
    project = project.strip()
    if not project:
        raise ValidationError("Project is required for agent instructions.")
    return project