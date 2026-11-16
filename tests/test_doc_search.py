# machine=PC2
# SPDX-License-Identifier: MIT
"""Offline contract tests for the AMD documentation bridge."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/codex-vivado/scripts/amd_doc_search.py"
SPEC = importlib.util.spec_from_file_location("amd_doc_search", SCRIPT)
doc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doc)


class Response(io.BytesIO):
    def __init__(self, body=b"", status=200, content_type="application/json", session=None):
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Type": content_type}
        if session:
            self.headers["Mcp-Session-Id"] = session


class DocSearchTests(unittest.TestCase):
    def test_multiline_sse_skips_heartbeat_and_selects_id(self):
        payload = ': heartbeat\r\nevent: message\r\ndata: {"jsonrpc":"2.0",\r\ndata: "id":2,"result":{"ok":true}}\r\n\r\n'
        self.assertEqual(doc._result(doc._parse_sse(payload), 2, "test"), {"ok": True})
        self.assertIsNone(doc._pick(doc._parse_sse(payload), 1))

    def test_sse_final_event_without_blank_line(self):
        self.assertEqual(doc._parse_sse('data: {"id":3}'), [{"id": 3}])

    def test_invalid_sse_and_duplicate_id_fail(self):
        with self.assertRaises(doc.McpError):
            doc._parse_sse('data: {bad}\n\n')
        with self.assertRaises(doc.McpError):
            doc._pick([{"id": 1}, {"id": 1}], 1)
        self.assertIsNone(doc._pick([{"id": True}], 1))

    def test_json_rpc_error_preserves_server_detail(self):
        response = [{"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "family invalid"}}]
        with self.assertRaisesRegex(doc.McpError, "family invalid"):
            doc._result(response, 1, "tools/call")

    def test_tool_failure_preserves_full_result(self):
        result = {"isError": True, "content": [{"type": "text", "text": "specific search failure"}]}
        with self.assertRaises(doc.ToolError) as error:
            doc._check_tool_result(result)
        self.assertIs(error.exception.result, result)
        self.assertIn("specific search failure", str(error.exception))
        with self.assertRaises(doc.ToolError):
            doc._check_tool_result({"isError": False, "content": [{"type": "text", "text": "[ERROR] unavailable"}]})

    def test_malformed_results_and_missing_response_are_protocol_failures(self):
        for result in ({}, {"content": None}, {"content": [3]}):
            with self.subTest(result=result), self.assertRaises(doc.McpError):
                doc._check_tool_result(result)
        with self.assertRaisesRegex(doc.McpError, "no matching response"):
            doc._result([{"jsonrpc": "2.0", "id": 2, "result": {}}], 1, "tools/call")

    def test_json_init_negotiation_headers_and_untruncated_result(self):
        large = "official result " * 10000
        result = {"content": [{"type": "text", "text": large}], "structuredContent": {"version": "2023.1"}}
        replies = [Response(json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25", "serverInfo": {"name": "AMD test"}}}).encode(), session="test-session"), Response(status=202), Response(json.dumps({"jsonrpc": "2.0", "id": 2, "result": result}).encode())]
        with patch.object(doc.urllib.request, "urlopen", side_effect=replies) as mocked:
            bridge = doc.Bridge(timeout=5)
            self.assertEqual(bridge.initialize(), {"name": "AMD test"})
            self.assertEqual(bridge.call_doc_search({"query": "report_timing"}), result)
        request = mocked.call_args_list[2].args[0]
        self.assertEqual(request.get_header("Mcp-session-id"), "test-session")
        self.assertEqual(request.get_header("Mcp-protocol-version"), "2025-11-25")

    def test_sse_stops_at_matching_response_without_waiting_for_eof(self):
        body = b': ping\n\ndata: {"jsonrpc":"2.0","method":"notification"}\n\ndata: {"jsonrpc":"2.0","id":4,"result":{}}\n\n'
        response = Response(body, content_type="text/event-stream")
        original_readline = response.readline
        def read_non_eof():
            value = original_readline()
            if value == b"":
                self.fail("must return when the matching id arrives")
            return value
        with patch.object(response, "readline", side_effect=read_non_eof):
            with patch.object(doc.urllib.request, "urlopen", return_value=response):
                self.assertEqual(doc._result(doc.Bridge()._post({"id": 4}), 4, "test"), {})

    def test_notification_failure_is_not_silently_ignored(self):
        bridge = doc.Bridge()
        init = [{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": doc.PROTOCOL, "serverInfo": {}}}]
        with patch.object(bridge, "_post", side_effect=[init, doc.McpError("notification failed")]):
            with self.assertRaisesRegex(doc.McpError, "notification failed"):
                bridge.initialize()

    def test_invalid_args_fail_before_network(self):
        for args in (["q", "--limit", "0"], ["q", "--limit", "51"], ["q", "--alpha", "nan"], ["q", "--alpha", "1.01"], ["q", "--timeout", "121"], ["q", "--timeout", "inf"], [" " ]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with patch.object(doc.urllib.request, "urlopen") as mocked:
                    with self.assertRaises(SystemExit) as error:
                        doc.main(args)
                    self.assertEqual(error.exception.code, 2)
                    mocked.assert_not_called()

    def test_repeated_filters_preserved(self):
        ns = doc.make_parser().parse_args(["timing", "--version", "2023.1", "--version", "2026.1", "--family", "Kintex UltraScale", "--tool", "Vivado Design Suite"])
        self.assertEqual(doc.build_args(ns), {"query": "timing", "limit": 5, "alpha": .8, "version": ["2023.1", "2026.1"], "family": ["Kintex UltraScale"], "tool": ["Vivado Design Suite"]})

    def test_json_cli_outputs_complete_error_result_and_nonzero(self):
        result = {"isError": True, "content": [{"type": "text", "text": "full failure detail"}]}
        with patch.object(doc.Bridge, "initialize", return_value={}):
            with patch.object(doc.Bridge, "call_doc_search", side_effect=doc.ToolError("failure", result)):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(doc.main(["public query", "--json"]), 2)
        parsed = json.loads(output.getvalue())
        self.assertEqual(parsed["result"], result)
        self.assertEqual(parsed["machine"], "PC2")

    def test_json_cli_reports_network_failure_as_exit_one(self):
        output = io.StringIO()
        with patch.object(doc.urllib.request, "urlopen", side_effect=doc.urllib.error.URLError("network down")):
            with contextlib.redirect_stdout(output):
                self.assertEqual(doc.main(["public query", "--json"]), 1)
        self.assertIn("network down", json.loads(output.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()
