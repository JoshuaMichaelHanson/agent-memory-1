from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_memory.config import ENV_DATABASE_PATH, resolve_config


REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = REPO_ROOT / "tmp" / "tests"


class ConfigTests(unittest.TestCase):
    def unique_dir(self, name: str) -> Path:
        path = TMP_ROOT / name / self.id().replace(".", "-")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_cli_db_overrides_environment(self) -> None:
        cwd = self.unique_dir("config-cli")
        cli_path = cwd / "cli.db"
        env_path = cwd / "env.db"

        with patch.dict(os.environ, {ENV_DATABASE_PATH: str(env_path)}):
            config = resolve_config(cli_path, cwd=cwd)

        self.assertEqual(config.database_path, cli_path.resolve())
        self.assertEqual(config.source, "cli")

    def test_environment_overrides_default_path(self) -> None:
        cwd = self.unique_dir("config-env")
        env_path = cwd / "env.db"

        with patch.dict(os.environ, {ENV_DATABASE_PATH: str(env_path)}):
            config = resolve_config(cwd=cwd)

        self.assertEqual(config.database_path, env_path.resolve())
        self.assertEqual(config.source, "environment")

    def test_default_path_is_project_local(self) -> None:
        cwd = self.unique_dir("config-default")

        with patch.dict(os.environ, {}, clear=True):
            config = resolve_config(cwd=cwd)

        self.assertEqual(config.database_path, (cwd / ".agent-memory" / "memory.db").resolve())
        self.assertEqual(config.project_root, cwd.resolve())
        self.assertEqual(config.source, "default")


if __name__ == "__main__":
    unittest.main()
