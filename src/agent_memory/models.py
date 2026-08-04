from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class Memory:
    id: int
    project: str
    scope: str
    kind: str
    memory_key: str | None
    content: str
    tags: tuple[str, ...]
    source_agent: str
    source_path: str | None
    importance: int
    content_sha256: str
    created_at: str
    updated_at: str
    last_accessed_at: str | None
    access_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project": self.project,
            "scope": self.scope,
            "kind": self.kind,
            "memory_key": self.memory_key,
            "content": self.content,
            "tags": list(self.tags),
            "source_agent": self.source_agent,
            "source_path": self.source_path,
            "importance": self.importance,
            "content_sha256": self.content_sha256,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
        }


@dataclass(frozen=True, slots=True)
class MemoryInput:
    project: str
    scope: str = "project"
    kind: str = "note"
    memory_key: str | None = None
    content: str = ""
    tags: tuple[str, ...] = ()
    source_agent: str = "unknown"
    source_path: str | None = None
    importance: int = 3

    def normalized(self) -> "MemoryInput":
        return MemoryInput(
            project=self.project.strip(),
            scope=self.scope.strip() or "project",
            kind=self.kind.strip() or "note",
            memory_key=normalize_optional_text(self.memory_key),
            content=normalize_content(self.content),
            tags=normalize_tags(self.tags),
            source_agent=self.source_agent.strip() or "unknown",
            source_path=normalize_optional_text(self.source_path),
            importance=self.importance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "scope": self.scope,
            "kind": self.kind,
            "memory_key": self.memory_key,
            "content": self.content,
            "tags": list(self.tags),
            "source_agent": self.source_agent,
            "source_path": self.source_path,
            "importance": self.importance,
        }


@dataclass(frozen=True, slots=True)
class PutResult:
    operation: str
    memory: Memory

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "memory": self.memory.to_dict(),
        }


def memory_from_row(row: Any) -> Memory:
    return Memory(
        id=int(row["id"]),
        project=str(row["project"]),
        scope=str(row["scope"]),
        kind=str(row["kind"]),
        memory_key=row["memory_key"],
        content=str(row["content"]),
        tags=parse_stored_tags(str(row["tags"])),
        source_agent=str(row["source_agent"]),
        source_path=row["source_path"],
        importance=int(row["importance"]),
        content_sha256=str(row["content_sha256"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        last_accessed_at=row["last_accessed_at"],
        access_count=int(row["access_count"]),
    )


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_content(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def content_sha256(content: str) -> str:
    normalized = normalize_content(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_tags(tags: Iterable[str]) -> tuple[str, ...]:
    normalized: set[str] = set()
    for tag in tags:
        tag_text = tag.strip().lower()
        if not tag_text:
            continue
        parts = [part.strip().lower() for part in tag_text.split(",")]
        normalized.update(part for part in parts if part)
    return tuple(sorted(normalized))


def serialize_tags(tags: Iterable[str]) -> str:
    return ",".join(normalize_tags(tags))


def parse_stored_tags(tags: str) -> tuple[str, ...]:
    return normalize_tags(tags.split(","))
