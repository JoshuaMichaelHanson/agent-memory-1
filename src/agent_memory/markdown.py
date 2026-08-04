from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from .models import Memory


def render_memory_export(*, project: str, source_database: Path, memories: list[Memory]) -> str:
    lines: list[str] = [
        "<!-- GENERATED FILE. DO NOT EDIT DIRECTLY. -->",
        f"<!-- Source: {source_database} -->",
        "",
        f"# Agent Memory: {project}",
        "",
        f"Generated: {datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')}",
        "",
    ]

    grouped: dict[str, list[Memory]] = defaultdict(list)
    for memory in memories:
        grouped[memory.kind].append(memory)

    for kind in sorted(grouped):
        lines.append(f"## {title_for_kind(kind)}")
        lines.append("")
        for memory in sorted(grouped[kind], key=memory_sort_key):
            lines.extend(render_memory(memory))
            lines.append("")

    if not memories:
        lines.append("No memories matched the export criteria.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def memory_sort_key(memory: Memory) -> tuple[int, str, str]:
    key = memory.memory_key or f"{memory.id:012d}"
    return (-memory.importance, reverse_timestamp(memory.updated_at), key)


def reverse_timestamp(timestamp: str) -> str:
    # ISO 8601 UTC timestamps sort lexically; invert codepoints for descending order inside tuple sorting.
    return "".join(chr(0x10FFFF - ord(character)) for character in timestamp)


def render_memory(memory: Memory) -> list[str]:
    title = memory.memory_key or f"memory-{memory.id}"
    tags = ", ".join(memory.tags) if memory.tags else "none"
    return [
        f"### {escape_heading(title)}",
        "",
        f"- ID: {memory.id}",
        f"- Importance: {memory.importance}",
        f"- Scope: {memory.scope}",
        f"- Updated: {memory.updated_at}",
        f"- Tags: {tags}",
        "",
        memory.content,
    ]


def title_for_kind(kind: str) -> str:
    text = kind.replace("-", " ").replace("_", " ").strip() or "Note"
    return text.title()


def escape_heading(value: str) -> str:
    return value.replace("\n", " ").strip() or "untitled"
