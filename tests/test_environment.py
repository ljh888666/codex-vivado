"""Configuration, launch and isolation invariants; machine=PC2."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/codex-vivado/scripts"))
import environment
import launch_mcp
sys.path.insert(0, str(ROOT / "tools"))
import configure


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        area = ROOT / ".runtime/test-temp"
        area.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=area)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        executable = self.root / "fake vivado.bat"
        executable.touch()
        self.config = {
            "schema_version": 1, "machine": "PC2", "python": sys.executable,
            "vivado_path": str(executable), "project_root": str(self.root),
            "work_dir": str(self.root / "work"), "temp_dir": str(self.root / "tmp"),
        }

    def test_ascii_space_paths_are_supported(self):
        self.assertEqual(environment.validate_config(self.config)["machine"], "PC2")

    def test_non_ascii_rejected_before_launch(self):
        self.config["work_dir"] = str(self.root / "工程")
        with self.assertRaisesRegex(environment.ConfigError, "ASCII"):
            environment.validate_config(self.config)

    def test_missing_interpreter_rejected(self):
        self.config["python"] = str(self.root / "missing.exe")
        with self.assertRaisesRegex(environment.ConfigError, "does not exist"):
            environment.validate_config(self.config)

    def test_relative_work_path_rejected(self):
        self.config["work_dir"] = "relative/work"
        with self.assertRaisesRegex(environment.ConfigError, "absolute"):
            environment.validate_config(self.config)

    def test_unknown_fields_rejected(self):
        self.config["secret_token"] = "do not persist unknown fields"
        with self.assertRaisesRegex(environment.ConfigError, "Unknown"):
            environment.validate_config(self.config)

    def test_backend_environment_ignores_import_overrides(self):
        with patch.dict(os.environ, {"PYTHONPATH": "wrong backend", "PYTHONHOME": "wrong home"}):
            env = environment.backend_environment(self.config)
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("PYTHONHOME", env)
        self.assertEqual(env["VIVADO_PATH"], self.config["vivado_path"])
        self.assertEqual(env["PYTHONNOUSERSITE"], "1")

    def config_file(self):
        path = self.root / "environment.json"
        path.write_text(json.dumps(self.config), encoding="utf-8")
        return path

    def test_launcher_check_never_starts_backend(self):
        with patch("launch_mcp.subprocess.call") as call, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(launch_mcp.main(["--config", str(self.config_file()), "--check"]), 0)
        call.assert_not_called()
        self.assertTrue(json.loads(output.getvalue())["config_valid"])

    def test_launcher_preserves_mcp_stdio_and_exit_code(self):
        with patch("launch_mcp.subprocess.call", return_value=7) as call:
            self.assertEqual(launch_mcp.main(["--config", str(self.config_file())]), 7)
        args, kwargs = call.call_args
        self.assertEqual(args[0][-2:], ["-m", "vivado_mcp"])
        self.assertIn("-I", args[0])
        self.assertNotIn("stdout", kwargs)
        self.assertNotIn("stdin", kwargs)
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["cwd"], self.config["work_dir"])

    def test_bad_config_returns_nonzero_without_stdout(self):
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launch_mcp.main(["--config", str(self.root / "missing.json")]), 2)
        self.assertEqual(output.getvalue(), "")

    def test_renderer_cannot_write_outside_runtime(self):
        with self.assertRaisesRegex(environment.ConfigError, ".runtime"):
            configure.render(self.config, ROOT / "unexpected-marketplace")

    def test_renderer_uses_selected_interpreter_and_preserves_other_files(self):
        destination = self.root / "marketplace"
        sentinel = destination / "user-file.txt"
        destination.mkdir()
        sentinel.write_text("keep", encoding="utf-8")
        with patch("configure.probe_backend", return_value={"tool_count": 32}):
            report = configure.render(self.config, destination)
        mcp = json.loads((Path(report["plugin"]) / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(mcp["mcpServers"]["vivado"]["command"], str(Path(sys.executable).resolve()))
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
