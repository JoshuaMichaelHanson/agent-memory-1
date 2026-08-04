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
    def run_agent_memory(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "agent_memory", *args],
            cwd=REPO_ROOT,
            env=env,
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


if __name__ == "__main__":
    unittest.main()
