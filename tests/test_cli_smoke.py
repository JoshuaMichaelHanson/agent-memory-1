from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
TMP_ROOT = REPO_ROOT / "tmp" / "tests"


class CliSmokeTests(unittest.TestCase):
    def run_agent_memory(self, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "agent_memory", *args],
            cwd=REPO_ROOT,
            env=env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def db_path(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        return TMP_ROOT / f"cli-{uuid.uuid4().hex}" / "memory.db"

    def test_module_help_exits_zero(self) -> None:
        result = self.run_agent_memory("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("agent-memory", result.stdout)
        self.assertIn("status", result.stdout)

    def test_status_json_before_database_initialization(self) -> None:
        db_path = self.db_path()
        result = self.run_agent_memory("status", "--json", "--db", str(db_path))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "status")
        self.assertFalse(payload["database_exists"])
        self.assertFalse(payload["initialized"])
        self.assertEqual(payload["database"], str(db_path.resolve()))
        self.assertEqual(payload["database_source"], "cli")

    def test_init_json_creates_database_and_status_reports_it(self) -> None:
        db_path = self.db_path()

        init_result = self.run_agent_memory("init", "--json", "--db", str(db_path))
        self.assertEqual(init_result.returncode, 0, init_result.stderr)
        init_payload = json.loads(init_result.stdout)
        self.assertTrue(init_payload["ok"])
        self.assertEqual(init_payload["command"], "init")
        self.assertEqual(init_payload["schema_version"], "1")
        self.assertTrue(db_path.exists())
        self.assertIn(init_payload["search_backend"], {"fts5", "like"})

        status_result = self.run_agent_memory(
            "status",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
        )
        self.assertEqual(status_result.returncode, 0, status_result.stderr)
        status_payload = json.loads(status_result.stdout)
        self.assertTrue(status_payload["initialized"])
        self.assertEqual(status_payload["schema_version"], "1")
        self.assertEqual(status_payload["project"], "demo")
        self.assertEqual(status_payload["total_memory_count"], 0)
        self.assertTrue(status_payload["wal_enabled"])

    def test_put_json_inserts_keyed_memory(self) -> None:
        db_path = self.db_path()

        result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--kind",
            "decision",
            "--key",
            "database-choice",
            "--content",
            "Use SQLite as the canonical agent memory store.",
            "--tag",
            "SQLite",
            "--tag",
            "architecture",
            "--importance",
            "5",
            "--agent",
            "codex",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["operation"], "inserted")
        self.assertEqual(payload["memory"]["memory_key"], "database-choice")
        self.assertEqual(payload["memory"]["tags"], ["architecture", "sqlite"])
        self.assertEqual(payload["memory"]["importance"], 5)

    def test_put_supports_content_file_and_stdin(self) -> None:
        db_path = self.db_path()
        content_file = db_path.parent / "memory-note.md"
        content_file.parent.mkdir(parents=True, exist_ok=True)
        content_file.write_text("From file", encoding="utf-8")

        file_result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--content-file",
            str(content_file),
        )
        self.assertEqual(file_result.returncode, 0, file_result.stderr)
        self.assertEqual(json.loads(file_result.stdout)["memory"]["content"], "From file")

        stdin_result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--stdin",
            input_text="From stdin",
        )
        self.assertEqual(stdin_result.returncode, 0, stdin_result.stderr)
        self.assertEqual(json.loads(stdin_result.stdout)["memory"]["content"], "From stdin")

    def test_put_validation_errors_are_json(self) -> None:
        result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(self.db_path()),
            "--project",
            "demo",
            "--content",
            "   ",
        )

        self.assertEqual(result.returncode, 5)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_put_rejects_multiple_content_sources(self) -> None:
        result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(self.db_path()),
            "--project",
            "demo",
            "--content",
            "content",
            "--stdin",
        )

        self.assertEqual(result.returncode, 2)

    def test_get_json_by_id_key_and_no_touch(self) -> None:
        db_path = self.db_path()
        put_result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--kind",
            "command",
            "--key",
            "run-tests",
            "--content",
            "Run pytest.",
        )
        self.assertEqual(put_result.returncode, 0, put_result.stderr)
        memory_id = json.loads(put_result.stdout)["memory"]["id"]

        get_result = self.run_agent_memory("get", "--json", "--db", str(db_path), "--id", str(memory_id))
        self.assertEqual(get_result.returncode, 0, get_result.stderr)
        touched = json.loads(get_result.stdout)["memory"]
        self.assertEqual(touched["id"], memory_id)
        self.assertEqual(touched["access_count"], 1)
        self.assertIsNotNone(touched["last_accessed_at"])

        key_result = self.run_agent_memory(
            "get",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--kind",
            "command",
            "--key",
            "run-tests",
            "--no-touch",
        )
        self.assertEqual(key_result.returncode, 0, key_result.stderr)
        inspected = json.loads(key_result.stdout)["memory"]
        self.assertEqual(inspected["id"], memory_id)
        self.assertEqual(inspected["access_count"], 1)
        self.assertEqual(inspected["last_accessed_at"], touched["last_accessed_at"])

    def test_get_missing_returns_not_found_json(self) -> None:
        result = self.run_agent_memory("get", "--json", "--db", str(self.db_path()), "--id", "999")

        self.assertEqual(result.returncode, 4)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "MEMORY_NOT_FOUND")

    def test_recent_json_filters_project_kind_importance_and_limit(self) -> None:
        db_path = self.db_path()
        writes = [
            ("demo", "note", "Low", "2"),
            ("demo", "command", "Command", "4"),
            ("demo", "note", "High", "5"),
            ("other", "note", "Other", "5"),
        ]
        for project, kind, content, importance in writes:
            result = self.run_agent_memory(
                "put",
                "--json",
                "--db",
                str(db_path),
                "--project",
                project,
                "--kind",
                kind,
                "--content",
                content,
                "--importance",
                importance,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        result = self.run_agent_memory(
            "recent",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--kind",
            "note",
            "--min-importance",
            "3",
            "--limit",
            "5",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "recent")
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["memories"][0]["content"], "High")
    def test_search_json_returns_matching_results_and_touches_by_default(self) -> None:
        db_path = self.db_path()
        put_result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--kind",
            "decision",
            "--key",
            "querydsl-projection-style",
            "--content",
            "Prefer constructor projections for QueryDSL DTO results.",
            "--tag",
            "querydsl",
            "--tag",
            "dto",
            "--importance",
            "5",
        )
        self.assertEqual(put_result.returncode, 0, put_result.stderr)

        result = self.run_agent_memory(
            "search",
            "QueryDSL DTO",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--kind",
            "decision",
            "--tag",
            "dto",
            "--min-importance",
            "4",
            "--limit",
            "5",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "search")
        self.assertEqual(payload["count"], 1)
        memory = payload["results"][0]["memory"]
        self.assertEqual(memory["memory_key"], "querydsl-projection-style")
        self.assertEqual(memory["access_count"], 1)
        self.assertIn(payload["results"][0]["search_backend"], {"fts5", "like"})

    def test_search_no_touch_and_no_results(self) -> None:
        db_path = self.db_path()
        put_result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--content",
            "Search no touch content.",
        )
        self.assertEqual(put_result.returncode, 0, put_result.stderr)

        result = self.run_agent_memory(
            "search",
            "touch",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--no-touch",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["results"][0]["memory"]["access_count"], 0)

        missing = self.run_agent_memory(
            "search",
            "absent",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
        )
        self.assertEqual(missing.returncode, 0, missing.stderr)
        self.assertEqual(json.loads(missing.stdout)["count"], 0)

    def test_search_malformed_query_is_json_success(self) -> None:
        db_path = self.db_path()
        put_result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--content",
            "Malformed query recovery content.",
        )
        self.assertEqual(put_result.returncode, 0, put_result.stderr)

        result = self.run_agent_memory(
            "search",
            '"Malformed',
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["count"], 1)
    def test_delete_json_by_id_and_missing(self) -> None:
        db_path = self.db_path()
        put_result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--content",
            "Delete me.",
        )
        self.assertEqual(put_result.returncode, 0, put_result.stderr)
        memory_id = json.loads(put_result.stdout)["memory"]["id"]

        delete_result = self.run_agent_memory("delete", "--json", "--yes", "--db", str(db_path), "--id", str(memory_id))
        self.assertEqual(delete_result.returncode, 0, delete_result.stderr)
        self.assertTrue(json.loads(delete_result.stdout)["deleted"])

        missing = self.run_agent_memory("delete", "--json", "--yes", "--db", str(db_path), "--id", str(memory_id))
        self.assertEqual(missing.returncode, 4)
        self.assertEqual(json.loads(missing.stdout)["error"]["code"], "MEMORY_NOT_FOUND")

    def test_delete_requires_yes_when_noninteractive(self) -> None:
        result = self.run_agent_memory("delete", "--json", "--db", str(self.db_path()), "--id", "1")

        self.assertEqual(result.returncode, 5)
        self.assertEqual(json.loads(result.stdout)["error"]["code"], "VALIDATION_ERROR")

    def test_mirror_file_json_inserted_and_unchanged(self) -> None:
        db_path = self.db_path()
        source = db_path.parent / "memory-note.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("Mirror content", encoding="utf-8")

        first = self.run_agent_memory(
            "mirror-file",
            str(source),
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--agent",
            "codex",
        )
        second = self.run_agent_memory(
            "mirror-file",
            str(source),
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--agent",
            "codex",
        )

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(first.stdout)["operation"], "inserted")
        self.assertEqual(json.loads(second.stdout)["operation"], "unchanged")

    def test_export_md_json_writes_generated_file(self) -> None:
        db_path = self.db_path()
        output = db_path.parent / "MEMORY.generated.md"
        put_result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--kind",
            "decision",
            "--key",
            "database-choice",
            "--content",
            "Use SQLite as canonical memory.",
            "--importance",
            "5",
        )
        self.assertEqual(put_result.returncode, 0, put_result.stderr)

        export_result = self.run_agent_memory(
            "export-md",
            "--json",
            "--db",
            str(db_path),
            "--project",
            "demo",
            "--output",
            str(output),
            "--min-importance",
            "4",
        )

        self.assertEqual(export_result.returncode, 0, export_result.stderr)
        payload = json.loads(export_result.stdout)
        self.assertEqual(payload["count"], 1)
        text = output.read_text(encoding="utf-8")
        self.assertIn("<!-- GENERATED FILE. DO NOT EDIT DIRECTLY. -->", text)
        self.assertIn("### database-choice", text)


    def test_export_json_and_import_json_restore_keyed_memories(self) -> None:
        source_db = self.db_path()
        target_db = self.db_path()
        snapshot = source_db.parent / "agent-memory.snapshot.json"
        put_result = self.run_agent_memory(
            "put",
            "--json",
            "--db",
            str(source_db),
            "--project",
            "demo",
            "--kind",
            "decision",
            "--key",
            "database-choice",
            "--content",
            "Use SQLite as canonical memory.",
            "--importance",
            "5",
        )
        self.assertEqual(put_result.returncode, 0, put_result.stderr)

        export_result = self.run_agent_memory(
            "export-json",
            "--json",
            "--db",
            str(source_db),
            "--project",
            "demo",
            "--output",
            str(snapshot),
        )
        self.assertEqual(export_result.returncode, 0, export_result.stderr)
        self.assertEqual(json.loads(export_result.stdout)["count"], 1)

        import_result = self.run_agent_memory("import-json", str(snapshot), "--json", "--db", str(target_db))
        self.assertEqual(import_result.returncode, 0, import_result.stderr)
        import_payload = json.loads(import_result.stdout)
        self.assertEqual(import_payload["inserted"], 1)

        search_result = self.run_agent_memory(
            "search",
            "SQLite canonical",
            "--json",
            "--db",
            str(target_db),
            "--project",
            "demo",
        )
        self.assertEqual(search_result.returncode, 0, search_result.stderr)
        self.assertEqual(json.loads(search_result.stdout)["count"], 1)
if __name__ == "__main__":
    unittest.main()
