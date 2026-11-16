"""Render a machine-local Codex marketplace, never touch CODEX_HOME. machine=PC2."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-vivado"
sys.path.insert(0, str(PLUGIN / "scripts"))
from environment import ConfigError, probe_backend, validate_config


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def autodetect_python() -> str:
    # Do not launch Vivado or query hardware during discovery.
    candidates = [os.environ.get("CODEX_VIVADO_PYTHON"), "D:/vivado-mcp/codex/.venv/Scripts/python.exe", sys.executable]
    return next(str(Path(p).resolve()) for p in candidates if p and Path(p).is_file())


def autodetect_vivado() -> str:
    explicit = os.environ.get("VIVADO_PATH")
    candidates = [explicit, shutil.which("vivado.bat"), shutil.which("vivado")]
    for base in ("D:/Xilinx/Vivado", "C:/Xilinx/Vivado", "D:/AMD/Vivado", "C:/AMD/Vivado"):
        candidates.extend(str(p) for p in sorted(Path(base).glob("*/bin/vivado.bat"), reverse=True))
    for value in candidates:
        if value and Path(value).is_file():
            return str(Path(value).resolve())
    raise ConfigError("Vivado not found; pass --vivado with the executable path")


def render(config: dict, output: Path) -> dict:
    config = validate_config(config)
    # Keep generated files within the permitted, ignored output area.
    output = output.resolve()
    if not output.is_relative_to((ROOT / ".runtime").resolve()):
        raise ConfigError("Rendered marketplace must be inside this repository's .runtime directory")
    report = probe_backend(config)
    target = output / "plugins" / "codex-vivado"
    shutil.copytree(PLUGIN, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "environment.json", "config.local.json"))
    marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
    write_json(output / ".agents/plugins/marketplace.json", marketplace)
    write_json(target / "environment.json", config)
    mcp = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
    mcp["mcpServers"]["vivado"]["command"] = config["python"]
    write_json(target / ".mcp.json", mcp)
    for name in ("LICENSE", "NOTICE"):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, target / name)
    for key in ("work_dir", "temp_dir"):
        Path(config[key]).mkdir(parents=True, exist_ok=True)
    return {
        "machine": config["machine"], "marketplace": str(output),
        "plugin": str(target), "config": str(target / "environment.json"),
        "backend": report, "vivado_process_started": False,
        "install_commands": [
            f'codex plugin marketplace add "{output}" --json',
            "codex plugin add codex-vivado@codex-vivado-local --json",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=None)
    parser.add_argument("--vivado", default=None)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--work-dir", type=Path, default=ROOT / ".runtime/work")
    parser.add_argument("--temp-dir", type=Path, default=ROOT / ".runtime/tmp")
    parser.add_argument("--machine", default="PC2", help="Local evidence label, not hardware identity")
    parser.add_argument("--part", default="", help="Expected part only; not a hardware observation")
    parser.add_argument("--vivado-version", default="", help="Configured version, not measured by running Vivado")
    parser.add_argument("--output", type=Path, default=ROOT / ".runtime/marketplace")
    args = parser.parse_args(argv)
    try:
        vivado = args.vivado or autodetect_vivado()
        inferred = re.search(r"(?:^|[/\\])(20[0-9]{2}\.[0-9]+)(?:[/\\]|$)", vivado)
        config = {
            "schema_version": 1, "machine": args.machine,
            "python": args.python or autodetect_python(), "vivado_path": vivado,
            "vivado_version": args.vivado_version or (inferred.group(1) if inferred else "unknown"),
            "project_root": str(args.project_root.resolve()),
            "work_dir": str(args.work_dir.resolve()), "temp_dir": str(args.temp_dir.resolve()),
            "part": args.part,
        }
        print(json.dumps(render(config, args.output), ensure_ascii=False, indent=2))
        return 0
    except (ConfigError, OSError) as exc:
        print(f"[codex-vivado] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
