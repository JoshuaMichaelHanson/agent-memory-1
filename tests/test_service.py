from __future__ import annotations

import json
import sqlite3
import time
import unittest
import uuid
from pathlib import Path

from agent_memory.errors import ValidationError
from agent_memory.models import MemoryInput, content_sha256
from agent_memory.service import MemoryService


REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = REPO_ROOT / "tmp" / "tests"


class ServicePutTests(unittest.TestCase):
    def db_path(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        return TMP_ROOT / f"service-{uuid.uuid4().hex}" / "memory.db"

    def count_memories(self, path: Path) -> int:
        connection = sqlite3.connect(path)
        try:
            return int(connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
        finally:
            connection.close()

    def test_keyed_insert_update_and_unchanged(self) -> None:
        path = self.db_path()
        service = MemoryService(path)

        inserted = service.put(
            MemoryInput(
                project="demo",
                kind="decision",
                memory_key="database-choice",
                content="Use SQLite as canonical memory.",
                tags=("sqlite", "Architecture"),
                source_agent="codex",
                importance=5,
            )
        )
        unchanged = service.put(
            MemoryInput(
                project="demo",
                kind="decision",
                memory_key="database-choice",
                content="Use SQLite as canonical memory.",
                tags=("architecture", "sqlite"),
                source_agent="codex",
                importance=5,
            )
        )
        time.sleep(0.01)
        updated = service.put(
            MemoryInput(
                project="demo",
                kind="decision",
                memory_key="database-choice",
                content="Use SQLite as canonical memory and export Markdown only for inspection.",
                tags=("sqlite", "architecture"),
                source_agent="claude",
                importance=5,
            )
        )

        self.assertEqual(inserted.operation, "inserted")
        self.assertEqual(unchanged.operation, "unchanged")
        self.assertEqual(updated.operation, "updated")
        self.assertEqual(inserted.memory.id, unchanged.memory.id)
        self.assertEqual(inserted.memory.id, updated.memory.id)
        self.assertEqual(inserted.memory.created_at, updated.memory.created_at)
        self.assertEqual(unchanged.memory.updated_at, inserted.memory.updated_at)
        self.assertGreaterEqual(updated.memory.updated_at, inserted.memory.updated_at)
        self.assertEqual(updated.memory.tags, ("architecture", "sqlite"))
        self.assertEqual(updated.memory.source_agent, "claude")
        self.assertEqual(self.count_memories(path), 1)

    def test_unkeyed_puts_create_separate_rows(self) -> None:
        path = self.db_path()
        service = MemoryService(path)

        first = service.put(MemoryInput(project="demo", content="Journal note."))
        second = service.put(MemoryInput(project="demo", content="Journal note."))

        self.assertEqual(first.operation, "inserted")
        self.assertEqual(second.operation, "inserted")
        self.assertNotEqual(first.memory.id, second.memory.id)
        self.assertEqual(self.count_memories(path), 2)

    def test_validation_rejects_bad_importance_and_empty_content(self) -> None:
        service = MemoryService(self.db_path())

        with self.assertRaises(ValidationError):
            service.put(MemoryInput(project="demo", content="value", importance=6))

        with self.assertRaises(ValidationError):
            service.put(MemoryInput(project="demo", content=" \r\n\t "))

    def test_content_hash_normalizes_line_endings(self) -> None:
        path = self.db_path()
        service = MemoryService(path)

        result = service.put(MemoryInput(project="demo", content="one\r\ntwo"))

        self.assertEqual(result.memory.content_sha256, content_sha256("one\ntwo"))

    def test_get_by_id_touches_by_default_and_no_touch_preserves_metadata(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        inserted = service.put(MemoryInput(project="demo", kind="decision", memory_key="lookup", content="Lookup me."))

        touched = service.get_by_id(inserted.memory.id)
        self.assertIsNotNone(touched)
        assert touched is not None
        self.assertEqual(touched.access_count, 1)
        self.assertIsNotNone(touched.last_accessed_at)

        inspected = service.get_by_id(inserted.memory.id, touch=False)
        self.assertIsNotNone(inspected)
        assert inspected is not None
        self.assertEqual(inspected.access_count, 1)
        self.assertEqual(inspected.last_accessed_at, touched.last_accessed_at)

    def test_get_by_key_and_missing_record_behavior(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        inserted = service.put(
            MemoryInput(project="demo", scope="project", kind="command", memory_key="run-tests", content="Run pytest.")
        )

        found = service.get_by_key(project="demo", scope="project", kind="command", memory_key="run-tests", touch=False)
        missing = service.get_by_key(project="demo", scope="project", kind="command", memory_key="missing", touch=False)

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.id, inserted.memory.id)
        self.assertIsNone(missing)

    def test_recent_filters_and_ordering(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        low = service.put(MemoryInput(project="demo", kind="note", content="Low", importance=2))
        time.sleep(0.01)
        command = service.put(MemoryInput(project="demo", kind="command", content="Command", importance=4))
        time.sleep(0.01)
        high = service.put(MemoryInput(project="demo", kind="note", content="High", importance=5))
        service.put(MemoryInput(project="other", kind="note", content="Other", importance=5))

        recent = service.recent(project="demo", limit=10)
        important_notes = service.recent(project="demo", kind="note", min_importance=3, limit=10)
        limited = service.recent(project="demo", limit=1)

        self.assertEqual([memory.id for memory in recent], [high.memory.id, command.memory.id, low.memory.id])
        self.assertEqual([memory.id for memory in important_notes], [high.memory.id])
        self.assertEqual([memory.id for memory in limited], [high.memory.id])

    def test_recent_missing_database_returns_empty_list(self) -> None:
        self.assertEqual(MemoryService(self.db_path()).recent(project="demo"), [])

    def test_search_finds_content_and_tags_with_filters(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        low = service.put(MemoryInput(project="demo", kind="note", content="QueryDSL low note", tags=("jpa",), importance=2))
        decision = service.put(
            MemoryInput(
                project="demo",
                scope="project",
                kind="decision",
                memory_key="querydsl-projection-style",
                content="Prefer constructor projections for QueryDSL DTO results.",
                tags=("QueryDSL", "DTO", "JPA"),
                importance=5,
            )
        )
        service.put(MemoryInput(project="other", kind="decision", content="QueryDSL from another project", importance=5))
        service.put(MemoryInput(project="demo", scope="global", kind="decision", content="QueryDSL DTO global scope", tags=("dto",), importance=5))

        results = service.search(
            project="demo",
            query="QueryDSL DTO",
            kind="decision",
            scope="project",
            tag="dto",
            min_importance=4,
            limit=10,
            touch=False,
        )

        self.assertEqual([result["memory"]["id"] for result in results], [decision.memory.id])
        self.assertEqual(results[0]["memory"]["tags"], ["dto", "jpa", "querydsl"])
        self.assertIn(results[0]["search_backend"], {"fts5", "like"})
        self.assertNotEqual(results[0]["memory"]["id"], low.memory.id)

    def test_search_orders_by_importance_before_rank_or_recency(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        low = service.put(MemoryInput(project="demo", content="canonical sqlite sqlite sqlite", importance=2))
        time.sleep(0.01)
        high = service.put(MemoryInput(project="demo", content="canonical sqlite", importance=5))

        results = service.search(project="demo", query="canonical sqlite", limit=10, touch=False)
        limited = service.search(project="demo", query="canonical sqlite", limit=1, touch=False)

        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0]["memory"]["id"], high.memory.id)
        self.assertEqual(results[1]["memory"]["id"], low.memory.id)
        self.assertEqual([result["memory"]["id"] for result in limited], [high.memory.id])

    def test_search_touch_and_no_touch_behavior(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        inserted = service.put(MemoryInput(project="demo", content="touch searchable memory", importance=4))

        touched = service.search(project="demo", query="searchable", touch=True)
        inspected = service.search(project="demo", query="searchable", touch=False)

        self.assertEqual(touched[0]["memory"]["id"], inserted.memory.id)
        self.assertEqual(touched[0]["memory"]["access_count"], 1)
        self.assertEqual(inspected[0]["memory"]["access_count"], 1)

    def test_search_malformed_fts_query_does_not_crash(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        inserted = service.put(MemoryInput(project="demo", content="Malformed query fallback memory", importance=4))

        results = service.search(project="demo", query='"Malformed', limit=10, touch=False)

        self.assertEqual([result["memory"]["id"] for result in results], [inserted.memory.id])

    def test_search_like_fallback_can_be_used_without_fts(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        inserted = service.put(MemoryInput(project="demo", content="LIKE fallback content", tags=("fallback",), importance=4))

        import agent_memory.service as service_module

        original = service_module.has_memories_fts
        service_module.has_memories_fts = lambda connection: False
        try:
            results = service.search(project="demo", query="fallback content", tag="fallback", limit=10, touch=False)
        finally:
            service_module.has_memories_fts = original

        self.assertEqual([result["memory"]["id"] for result in results], [inserted.memory.id])
        self.assertEqual(results[0]["search_backend"], "like")
        self.assertIsNone(results[0]["score"])

    def test_search_handles_unicode_content(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        inserted = service.put(MemoryInput(project="demo", content="Unicode cafe memory: cafe deja vu", tags=("unicode",)))

        results = service.search(project="demo", query="cafe deja", limit=10, touch=False)

        self.assertEqual([result["memory"]["id"] for result in results], [inserted.memory.id])

    def test_delete_by_id_and_key(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        by_id = service.put(MemoryInput(project="demo", content="Delete by id."))
        by_key = service.put(MemoryInput(project="demo", kind="command", memory_key="delete-key", content="Delete by key."))

        self.assertTrue(service.delete_by_id(by_id.memory.id))
        self.assertFalse(service.delete_by_id(by_id.memory.id))
        self.assertTrue(service.delete_by_key(project="demo", scope="project", kind="command", memory_key="delete-key"))
        self.assertIsNone(service.get_by_id(by_key.memory.id, touch=False))

    def test_mirror_file_inserts_unchanged_and_changed_revisions(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        source = path.parent / "AGENTS.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("First revision\r\n", encoding="utf-8")

        first = service.mirror_file(project="demo", path=source, source_agent="codex", project_root=path.parent)
        unchanged = service.mirror_file(project="demo", path=source, source_agent="codex", project_root=path.parent)
        source.write_text("Second revision\n", encoding="utf-8")
        changed = service.mirror_file(project="demo", path=source, source_agent="codex", project_root=path.parent)

        self.assertEqual(first["operation"], "inserted")
        self.assertEqual(unchanged["operation"], "unchanged")
        self.assertEqual(changed["operation"], "inserted")
        self.assertEqual(first["path"], "AGENTS.md")
        self.assertEqual(first["revision_id"], unchanged["revision_id"])
        self.assertNotEqual(first["revision_id"], changed["revision_id"])

    def test_mirror_file_missing_raises_file_error(self) -> None:
        from agent_memory.errors import FileOperationError

        service = MemoryService(self.db_path())

        with self.assertRaises(FileOperationError):
            service.mirror_file(project="demo", path=Path("missing-file.md"))

    def test_export_markdown_writes_generated_file(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        service.put(
            MemoryInput(
                project="demo",
                kind="decision",
                memory_key="sqlite-canonical",
                content="SQLite is canonical.",
                tags=("sqlite", "architecture"),
                importance=5,
            )
        )
        service.put(MemoryInput(project="demo", kind="note", content="Low value note.", importance=2))
        output = path.parent / "MEMORY.generated.md"

        result = service.export_markdown(project="demo", output_path=output, min_importance=3)
        text = output.read_text(encoding="utf-8")

        self.assertEqual(result["count"], 1)
        self.assertIn("<!-- GENERATED FILE. DO NOT EDIT DIRECTLY. -->", text)
        self.assertIn("# Agent Memory: demo", text)
        self.assertIn("## Decision", text)
        self.assertIn("### sqlite-canonical", text)
        self.assertIn("SQLite is canonical.", text)
        self.assertNotIn("Low value note.", text)


    def test_json_snapshot_export_and_import_are_idempotent_for_keyed_memories(self) -> None:
        source_path = self.db_path()
        source = MemoryService(source_path)
        source.put(
            MemoryInput(
                project="demo",
                kind="decision",
                memory_key="database-choice",
                content="Use SQLite as canonical memory.",
                tags=("sqlite", "architecture"),
                importance=5,
                source_agent="codex",
            )
        )
        source.put(MemoryInput(project="other", kind="note", memory_key="other", content="Do not export."))
        snapshot = source_path.parent / "agent-memory.snapshot.json"

        export_result = source.export_json_snapshot(project="demo", output_path=snapshot)
        payload = json.loads(snapshot.read_text(encoding="utf-8"))
        target_path = self.db_path()
        target = MemoryService(target_path)
        first_import = target.import_json_snapshot(input_path=snapshot)
        second_import = target.import_json_snapshot(input_path=snapshot)
        restored = target.get_by_key(project="demo", scope="project", kind="decision", memory_key="database-choice", touch=False)

        self.assertEqual(export_result["count"], 1)
        self.assertEqual(payload["format"], "agent-memory.snapshot.v1")
        self.assertEqual(first_import["inserted"], 1)
        self.assertEqual(second_import["unchanged"], 1)
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.content, "Use SQLite as canonical memory.")
        self.assertEqual(restored.tags, ("architecture", "sqlite"))

    def test_secret_guardrail_blocks_put_unless_explicitly_allowed(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        memory = MemoryInput(project="demo", content="password=not-a-real-test-secret")

        with self.assertRaises(ValidationError):
            service.put(memory)

        result = service.put(memory, allow_sensitive=True)

        self.assertEqual(result.operation, "inserted")
        self.assertEqual(result.memory.content, "password=not-a-real-test-secret")

    def test_secret_guardrail_blocks_mirror_file_unless_explicitly_allowed(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        source = path.parent / "secrets.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("token=not-a-real-test-token", encoding="utf-8")

        with self.assertRaises(ValidationError):
            service.mirror_file(project="demo", path=source, project_root=path.parent)

        result = service.mirror_file(project="demo", path=source, project_root=path.parent, allow_sensitive=True)

        self.assertEqual(result["operation"], "inserted")

    def test_secret_guardrail_blocks_json_import_before_mutation(self) -> None:
        path = self.db_path()
        service = MemoryService(path)
        snapshot = path.parent / "snapshot.json"
        secret_content = "api_key=not-a-real-test-secret"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(
            json.dumps(
                {
                    "format": "agent-memory.snapshot.v1",
                    "project": "demo",
                    "memories": [
                        {
                            "project": "demo",
                            "kind": "note",
                            "memory_key": "secret-note",
                            "content": secret_content,
                            "tags": [],
                            "source_agent": "test",
                            "source_path": None,
                            "importance": 3,
                            "content_sha256": content_sha256(secret_content),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaises(ValidationError):
            service.import_json_snapshot(input_path=snapshot)

        self.assertFalse(path.exists())
        result = service.import_json_snapshot(input_path=snapshot, allow_sensitive=True)

        self.assertEqual(result["inserted"], 1)
if __name__ == "__main__":
    unittest.main()
