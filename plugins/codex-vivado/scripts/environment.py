"""Shared local configuration, machine=PC2. No Vivado process is started."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


class ConfigError(ValueError):
    pass


PATH_KEYS = ("python", "vivado_path", "project_root", "work_dir", "temp_dir")


def validate_config(config: dict, *, check_paths: bool = True) -> dict:
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ConfigError("Expected a configuration object with schema_version=1")
    allowed = {"schema_version", "machine", "vivado_version", "part", *PATH_KEYS}
    if set(config) - allowed:
        raise ConfigError("Unknown configuration keys: " + ", ".join(sorted(set(config) - allowed)))
    for key in ("machine", *PATH_KEYS):
        value = config.get(key)
        if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
            raise ConfigError(f"{key} must be a nonempty string without control characters")
    result = dict(config)
    for key in PATH_KEYS:
        value = config[key]
        if not value.isascii():
            raise ConfigError(f"{key} must use an ASCII path: {value!r}")
        path = Path(value).expanduser()
        if not path.is_absolute():
            raise ConfigError(f"{key} must be an absolute path")
        result[key] = str(path.resolve())
    if check_paths:
        for key in ("python", "vivado_path"):
            if not Path(result[key]).is_file():
                raise ConfigError(f"{key} file does not exist: {result[key]}")
        if not Path(result["project_root"]).is_dir():
            raise ConfigError("project_root directory does not exist")
        for key in ("work_dir", "temp_dir"):
            if Path(result[key]).exists() and not Path(result[key]).is_dir():
                raise ConfigError(f"{key} must be a directory")
    return result


def load_config(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8-sig") as stream:
            return validate_config(json.load(stream))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Cannot read config {path}: {exc}") from exc


def backend_environment(config: dict) -> dict:
    env = dict(os.environ)
    # Respect the chosen interpreter's site-packages; inherited overrides can
    # silently import a different backend. Do not modify the installed backend.
    for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
        env.pop(key, None)
    env.update({
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
        "VIVADO_PATH": config["vivado_path"],
        "TEMP": config["temp_dir"], "TMP": config["temp_dir"],
        "CODEX_VIVADO_MACHINE": config["machine"],
    })
    return env


BACKEND_PROBE = """
import asyncio, importlib.metadata as metadata, json, sys
from vivado_mcp.server import mcp
import vivado_mcp
tools = asyncio.run(mcp.list_tools())
print(json.dumps({
    'python': sys.executable, 'python_version': list(sys.version_info[:3]),
    'backend_version': metadata.version('vivado-mcp'),
    'mcp_version': metadata.version('mcp'), 'backend_file': vivado_mcp.__file__,
    'tool_count': len(tools), 'tools': sorted(t.name for t in tools)
}))
"""


def probe_backend(config: dict) -> dict:
    """Import and list registrations only; no lifespan, sessions or tool calls."""
    try:
        result = subprocess.run(
            [config["python"], "-I", "-B", "-X", "utf8", "-c", BACKEND_PROBE],
            env=backend_environment(config), capture_output=True, text=True,
            encoding="utf-8", timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConfigError(f"Backend import probe failed: {exc}") from exc
    if result.returncode:
        raise ConfigError(f"Backend import failed (exit {result.returncode}): {result.stderr.strip()}")
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ConfigError("Backend import did not return clean JSON: " + result.stdout) from exc
    if report.get("python_version", []) < [3, 10]:
        raise ConfigError("vivado-mcp requires Python >=3.10")
    required = {"start_session", "list_sessions", "run_tcl", "parse_xpr", "xdc_lint"}
    if not required.issubset(report.get("tools", [])):
        raise ConfigError("Backend is missing expected workflow tools")
    return report
