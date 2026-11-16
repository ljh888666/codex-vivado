"""Install/list in an isolated CODEX_HOME below .runtime only. machine=PC2.

This tests native marketplace/plugin parsing and copied package files. It does
not invoke a model, attach to the running app, or start a Vivado session.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(codex: str, args: list[str], env: dict) -> dict:
    result = subprocess.run([codex, *args], env=env, capture_output=True, text=True, encoding="utf-8", timeout=45)
    if result.returncode:
        raise RuntimeError(f"codex {' '.join(args)}: exit={result.returncode} {result.stderr.strip()} {result.stdout.strip()}")
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marketplace", type=Path, default=ROOT / ".runtime/marketplace")
    parser.add_argument("--home", type=Path, default=ROOT / ".runtime/native-home")
    args = parser.parse_args()
    try:
        home = args.home.resolve()
        if not home.is_relative_to((ROOT / ".runtime").resolve()):
            raise ValueError("Test CODEX_HOME must be inside .runtime")
        home.mkdir(parents=True, exist_ok=True)
        codex = shutil.which("codex")
        if not codex:
            raise ValueError("codex executable not found")
        env = dict(os.environ)
        env["CODEX_HOME"] = str(home)
        market = run(codex, ["plugin", "marketplace", "add", str(args.marketplace.resolve()), "--json"], env)
        installed = run(codex, ["plugin", "add", "codex-vivado@codex-vivado-local", "--json"], env)
        inventory = run(codex, ["plugin", "list", "--marketplace", "codex-vivado-local", "--json"], env)
        if not any(p.get("enabled") and p.get("name") == "codex-vivado" for p in inventory["installed"]):
            raise RuntimeError("Native CLI did not list the enabled plugin")
        path = Path(installed["installedPath"])
        for required in (".codex-plugin/plugin.json", ".mcp.json", "environment.json", "scripts/launch_mcp.py", "scripts/amd_doc_search.py"):
            if not (path / required).is_file():
                raise RuntimeError(f"Installed package missing {required}")
        skills = sorted(p.parent.name for p in (path / "skills").glob("*/SKILL.md"))
        if len(skills) != 4:
            raise RuntimeError(f"Expected 4 skills, found {skills}")
        loaded_mcp = run(codex, ["mcp", "get", "vivado", "--json"], env)
        if not loaded_mcp.get("enabled"):
            raise RuntimeError("Native Codex loader did not enable plugin MCP")
        print(json.dumps({"machine": "PC2", "status": "PASS", "home": str(home), "marketplace": market, "install": installed, "skills": skills, "inventory": inventory, "loaded_mcp": loaded_mcp, "vivado_process_started": False}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"machine": "PC2", "status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
