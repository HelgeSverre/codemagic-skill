"""Check that published artifacts run outside the developer's checkout."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_plugin", ROOT / "scripts/build_plugin.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class DistributionTests(unittest.TestCase):
    def test_plugin_archive_is_self_contained(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            archive_path = builder.build(temp)
            extracted = temp / "plugin with spaces"
            with ZipFile(archive_path) as archive:
                self.assertIn("plugin.json", archive.namelist())
                self.assertIn(".claude-plugin/plugin.json", archive.namelist())
                self.assertFalse(
                    any("__pycache__" in name or ".env" in name for name in archive.namelist())
                )
                archive.extractall(extracted)
            script = extracted / "skills/codemagic/scripts/codemagic_api.py"
            env = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith(("CODEMAGIC_", "CM_API_"))
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "start",
                    "--app",
                    "a" * 24,
                    "--workflow",
                    "mobile-build",
                    "--branch",
                    "feature/example",
                    "--dry-run",
                ],
                cwd=temp,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["body"]["branch"], "feature/example")
            self.assertFalse(payload["sent"])

    def test_standalone_skill_needs_no_repository_files(self):
        import shutil

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skill"
            shutil.copytree(
                ROOT / "skills/codemagic", target, ignore=shutil.ignore_patterns("__pycache__")
            )
            result = subprocess.run(
                [sys.executable, str(target / "scripts/codemagic_api.py"), "--version"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(result.stdout.strip(), "1.0.0")

    def test_environment_auth_on_all_platforms(self):
        from unittest.mock import patch

        import codemagic_api as cm

        with patch.dict(os.environ, {"CODEMAGIC_API_KEY": "synthetic-key"}, clear=True):
            self.assertEqual(cm.token_source(), ("synthetic-key", "CODEMAGIC_API_KEY"))


if __name__ == "__main__":
    unittest.main()
