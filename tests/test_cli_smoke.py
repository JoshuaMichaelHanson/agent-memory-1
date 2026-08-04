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


if __name__ == "__main__":
    unittest.main()
