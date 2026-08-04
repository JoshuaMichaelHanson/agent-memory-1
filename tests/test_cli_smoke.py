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

    def test_module_help_exits_zero(self) -> None:
        result = self.run_agent_memory("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("agent-memory", result.stdout)
        self.assertIn("status", result.stdout)

    def test_status_json_before_database_initialization(self) -> None:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        db_path = TMP_ROOT / f"missing-{uuid.uuid4().hex}.db"
        result = self.run_agent_memory("status", "--json", "--db", str(db_path))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "status")
        self.assertFalse(payload["database_exists"])
        self.assertFalse(payload["initialized"])
        self.assertEqual(payload["database"], str(db_path))


if __name__ == "__main__":
    unittest.main()
