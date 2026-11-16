#!/usr/bin/env python3
# machine=PC2
# SPDX-License-Identifier: MIT
# Adapted from dsh-vivado/skills/amd-doc-search/doc_search.py.
# Copyright (c) 2026 chemmy-11. See the repository LICENSE and NOTICE.
"""Search AMD public documentation using its hosted MCP service (stdlib only).

Queries are sent to https://ross.amd.com/mcp/doc-search. Do not submit private
design details. Version/family filters are hints: verify each returned block.
Exit codes: 0 success, 1 HTTP/protocol/network failure, 2 argument/tool failure.
"""
from __future__ import annotations

import argparse
import http.client
import json
import math
import socket
import sys
import time
import urllib.error
import urllib.request

URL = "https://ross.amd.com/mcp/doc-search"
PROTOCOL = "2025-06-18"
TOOL = "vivado_doc_search"


class McpError(RuntimeError):
    """The HTTP exchange or JSON-RPC response did not succeed."""


class ToolError(McpError):
    """The server returned a tool failure; keep the complete result."""

    def __init__(self, reason: str, result: dict) -> None:
        self.result = result
        super().__init__(reason + ": " + json.dumps(result, ensure_ascii=False))


def _messages(value: object) -> list[dict]:
    messages = value if isinstance(value, list) else [value]
    if not messages or any(not isinstance(item, dict) for item in messages):
        raise McpError("response must contain JSON-RPC objects")
    return messages


def _decode_json(payload: str) -> list[dict]:
    try:
        return _messages(json.loads(payload))
    except json.JSONDecodeError as exc:
        raise McpError(f"invalid JSON response: {exc}") from exc


def _parse_sse(payload: str) -> list[dict]:
    """Decode SSE data fields, including multiline JSON and final events."""
    messages: list[dict] = []
    fields: list[str] = []
    for line in payload.replace("\r\n", "\n").replace("\r", "\n").split("\n") + [""]:
        if line == "":
            if fields:
                messages.extend(_decode_json("\n".join(fields)))
                fields = []
        elif line.startswith("data:"):
            value = line[5:]
            fields.append(value[1:] if value.startswith(" ") else value)
        elif line == "data":
            fields.append("")
    return messages


def _pick(messages: list[dict] | None, message_id: int) -> dict | None:
    matches = [message for message in messages or []
               if type(message.get("id")) is type(message_id) and message.get("id") == message_id]
    if len(matches) > 1:
        raise McpError(f"duplicate response id {message_id}")
    return matches[0] if matches else None


def _result(messages: list[dict], message_id: int, method: str) -> dict:
    response = _pick(messages, message_id)
    if response is None:
        raise McpError(f"no matching response for {method}, id={message_id}")
    if response.get("jsonrpc") != "2.0":
        raise McpError(f"invalid JSON-RPC version for {method}")
    if "error" in response:
        raise McpError(f"{method}: " + json.dumps(response["error"], ensure_ascii=False))
    if not isinstance(response.get("result"), dict):
        raise McpError(f"missing object result for {method}")
    return response["result"]


def _texts(result: dict) -> list[str]:
    return [item["text"] for item in result.get("content", [])
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)]


def _check_tool_result(result: dict) -> dict:
    if result.get("isError"):
        raise ToolError("server returned isError=true", result)
    if not isinstance(result.get("content"), list):
        raise McpError("tool result omitted content array")
    if any(not isinstance(item, dict) for item in result["content"]):
        raise McpError("tool result contains a non-object content block")
    # Some bridges return transport success with an explicit textual error.
    if any(text.lstrip().startswith("[ERROR]") for text in _texts(result)):
        raise ToolError("server returned an explicit [ERROR] text", result)
    return result


class Bridge:
    def __init__(self, url: str = URL, timeout: float = 60) -> None:
        if not math.isfinite(timeout) or not 1 <= timeout <= 120:
            raise ValueError("timeout must be between 1 and 120 seconds")
        self.url = url
        self.timeout = timeout
        self.session_id: str | None = None
        self.protocol = PROTOCOL
        self.server_info: dict = {}
        self._id = 0

    def _post(self, payload: dict) -> list[dict]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Accept-Encoding": "identity",
            "MCP-Protocol-Version": self.protocol,
            "User-Agent": "codex-vivado-doc-search/0.1.0",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(
            self.url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers, method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.headers.get("Mcp-Session-Id"):
                    self.session_id = response.headers["Mcp-Session-Id"]
                if response.status in (202, 204) and "id" not in payload:
                    return []
                if "text/event-stream" in response.headers.get("Content-Type", "").lower():
                    messages: list[dict] = []
                    event: list[str] = []
                    while True:
                        if time.monotonic() - started > self.timeout:
                            raise McpError("SSE response exceeded timeout")
                        raw = response.readline()
                        if raw:
                            event.append(raw.decode("utf-8"))
                        if not raw or raw in (b"\n", b"\r\n"):
                            messages.extend(_parse_sse("".join(event)))
                            event = []
                            if "id" in payload and _pick(messages, payload["id"]) is not None:
                                return messages
                            if not raw:
                                return messages
                raw = response.read()
                if not raw:
                    return []
                return _decode_json(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise McpError(f"HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, socket.timeout, OSError, UnicodeError) as exc:
            raise McpError(f"network/encoding error: {exc}") from exc

    def initialize(self) -> dict:
        self._id += 1
        result = _result(self._post({
            "jsonrpc": "2.0", "id": self._id, "method": "initialize",
            "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                       "clientInfo": {"name": "codex-vivado-doc-search", "version": "0.1.0"}},
        }), self._id, "initialize")
        if not isinstance(result.get("protocolVersion"), str):
            raise McpError("initialize omitted protocolVersion")
        if not isinstance(result.get("serverInfo"), dict):
            raise McpError("initialize omitted serverInfo")
        self.protocol = result["protocolVersion"]
        self.server_info = result["serverInfo"]
        notification_messages = self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        for message in notification_messages:
            if "error" in message:
                raise McpError("initialized notification failed: " + json.dumps(message["error"], ensure_ascii=False))
        return self.server_info

    def call_doc_search(self, arguments: dict) -> dict:
        self._id += 1
        result = _result(self._post({
            "jsonrpc": "2.0", "id": self._id, "method": "tools/call",
            "params": {"name": TOOL, "arguments": arguments},
        }), self._id, "tools/call")
        return _check_tool_result(result)


def _bounded_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer between 1 and 50") from exc
    if not 1 <= number <= 50:
        raise argparse.ArgumentTypeError("must be between 1 and 50")
    return number


def _bounded_float(lower: float, upper: float):
    def parse(value: str) -> float:
        try:
            number = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"must be a number between {lower} and {upper}") from exc
        if not math.isfinite(number) or not lower <= number <= upper:
            raise argparse.ArgumentTypeError(f"must be between {lower} and {upper}")
        return number
    return parse


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="public documentation query; sent to AMD")
    parser.add_argument("--version", action="append", help="version hint, repeatable")
    parser.add_argument("--family", action="append", help="device family hint, repeatable")
    parser.add_argument("--tool", action="append", help="tool hint, repeatable")
    parser.add_argument("--limit", type=_bounded_int, default=5)
    parser.add_argument("--alpha", type=_bounded_float(0, 1), default=0.8)
    parser.add_argument("--timeout", type=_bounded_float(1, 120), default=60, help="HTTP timeout seconds (1..120)")
    parser.add_argument("--json", action="store_true", help="emit full tool result as JSON")
    return parser


def build_args(namespace: argparse.Namespace) -> dict:
    result = {"query": namespace.query, "limit": namespace.limit, "alpha": namespace.alpha}
    for key in ("version", "family", "tool"):
        value = getattr(namespace, key)
        if value:
            result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    namespace = parser.parse_args(argv)
    if not namespace.query.strip():
        parser.error("query must not be empty")
    bridge = Bridge(timeout=namespace.timeout)
    started = time.monotonic()
    try:
        bridge.initialize()
        result = bridge.call_doc_search(build_args(namespace))
    except ToolError as exc:
        if namespace.json:
            print(json.dumps({"machine": "PC2", "server": bridge.server_info, "result": exc.result,
                              "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[doc_search] TOOL_ERROR: {exc}", file=sys.stderr)
        return 2
    except McpError as exc:
        if namespace.json:
            print(json.dumps({"machine": "PC2", "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[doc_search] FAILED: {exc}", file=sys.stderr)
        return 1
    if namespace.json:
        print(json.dumps({"machine": "PC2", "server": bridge.server_info, "result": result},
                         ensure_ascii=False, indent=2))
    else:
        for index, block in enumerate(_texts(result), 1):
            print(f"--- result block {index} ---\n{block}\n")
        if not _texts(result):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"[doc_search] machine=PC2 server={bridge.server_info.get('name', '?')} "
              f"elapsed={time.monotonic() - started:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
