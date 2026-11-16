"""stdio-transparent launcher for external vivado-mcp. machine=PC2.

Only the Python MCP server starts here. Vivado starts only on a tool request.
Diagnostics go to stderr; stdout is reserved for MCP JSON-RPC.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from environment import ConfigError, backend_environment, load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default = os.environ.get("CODEX_VIVADO_CONFIG", str(Path(__file__).resolve().parents[1] / "environment.json"))
    parser.add_argument("--config", type=Path, default=Path(default))
    parser.add_argument("--check", action="store_true", help="Validate configuration only; no backend or Vivado")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config.resolve())
        if args.check:
            print(json.dumps({"machine": config["machine"], "config_valid": True}))
            return 0
        for key in ("work_dir", "temp_dir"):
            Path(config[key]).mkdir(parents=True, exist_ok=True)
        # Inherit raw stdin/stdout/stderr, never decode or wrap MCP traffic.
        # -I prevents a project module named vivado_mcp.py from shadowing the
        # explicitly configured interpreter's installed package.
        return subprocess.call(
            [config["python"], "-I", "-B", "-X", "utf8", "-m", "vivado_mcp"],
            cwd=config["work_dir"], env=backend_environment(config),
        )
    except (ConfigError, OSError) as exc:
        print(f"[codex-vivado] {exc}. Run tools/configure.py first.", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
