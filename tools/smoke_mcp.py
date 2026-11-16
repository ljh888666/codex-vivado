"""Check real stdio MCP initialize/list/offline parsing; no Vivado. machine=PC2."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_tool_result(result) -> list[str]:
    texts = [block.text for block in result.content if block.type == "text"]
    failed = getattr(result, "is_error", getattr(result, "isError", False))
    if failed or any(line.lstrip().startswith("[ERROR]") for text in texts for line in text.splitlines()):
        raise RuntimeError("MCP tool failed: " + "\n".join(texts))
    return texts


async def check(plugin: Path) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    settings = json.loads((plugin / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["vivado"]
    env = dict(os.environ)
    env.update(settings.get("env", {}))
    params = StdioServerParameters(
        command=settings["command"], args=settings["args"],
        cwd=str(plugin), env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            initialized = await client.initialize()
            tools = await client.list_tools()
            names = sorted(tool.name for tool in tools.tools)
            required = {"start_session", "list_sessions", "parse_xpr", "run_tcl", "xdc_lint"}
            if not required.issubset(names):
                raise RuntimeError("Backend is missing required tool names")
            # list_sessions creates no session. parse_xpr is offline by schema.
            before = check_tool_result(await client.call_tool("list_sessions", {}))
            fixture = ROOT / "tests/fixtures/minimal.xpr"
            parsed = check_tool_result(await client.call_tool("parse_xpr", {"file_path": str(fixture)}))
            if not any("xcku060-ffva1156-2-i" in value for value in parsed):
                raise RuntimeError("Offline parser failed to return fixture part")
            after = check_tool_result(await client.call_tool("list_sessions", {}))
            if before != after:
                raise RuntimeError("Session inventory changed during offline smoke check")
            return {
                "machine": "PC2", "status": "PASS",
                "server": getattr(initialized, "server_info", getattr(initialized, "serverInfo", None)).model_dump(),
                "tool_count": len(names), "tools": names,
                "list_sessions_before": before, "list_sessions_after": after,
                "offline_parse_xpr": parsed, "vivado_process_started": False,
                "scope": "Real MCP transport plus fixture parse; no synthesis/programming/ILA calls",
            }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-dir", type=Path, default=ROOT / ".runtime/marketplace/plugins/codex-vivado")
    args = parser.parse_args()
    try:
        result = asyncio.run(asyncio.wait_for(check(args.plugin_dir.resolve()), timeout=60))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        def detail(error):
            nested = getattr(error, "exceptions", None)
            return "; ".join(detail(item) for item in nested) if nested else f"{type(error).__name__}: {error}"
        print(json.dumps({"machine": "PC2", "status": "FAIL", "error": detail(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
