"""Read-only environment doctor. Imports MCP registrations, never Vivado. machine=PC2."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/codex-vivado/scripts"))
from environment import ConfigError, load_config, probe_backend


def inspect(config_path: Path) -> dict:
    config = load_config(config_path)
    plugin = config_path.resolve().parent
    manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    mcp_config = json.loads((plugin / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["vivado"]
    skills = sorted(path.parent.name for path in (plugin / "skills").glob("*/SKILL.md"))
    if manifest["name"] != "codex-vivado" or not skills:
        raise ConfigError("Plugin manifest or skills missing")
    if mcp_config.get("tool_timeout_sec", 0) < 1800:
        raise ConfigError("MCP tool timeout must allow long project commands")
    if Path(mcp_config["command"]).resolve() != Path(config["python"]).resolve():
        raise ConfigError("Rendered MCP interpreter differs from environment.json")
    return {
        "machine": config["machine"], "status": "PASS",
        "configured_vivado_version": config.get("vivado_version", "unknown"),
        "configured_part": config.get("part", ""),
        "vivado_version_measured": False, "hardware_identity_measured": False,
        "vivado_executable": config["vivado_path"], "skills": skills,
        "backend": probe_backend(config),
        "vivado_process_started": False,
        "scope": "Configuration, files and Python MCP registrations only; not timing or hardware validation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / ".runtime/marketplace/plugins/codex-vivado/environment.json")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.config), ensure_ascii=False, indent=2))
        return 0
    except (ConfigError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"machine": "PC2", "status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
