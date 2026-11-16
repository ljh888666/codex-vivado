"""False-success and SDK field compatibility checks. machine=PC2."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from smoke_mcp import check_tool_result


class SmokeTests(unittest.TestCase):
    def test_snake_case_sdk_error_is_failure(self):
        result = SimpleNamespace(is_error=True, content=[SimpleNamespace(type="text", text="broken")])
        with self.assertRaisesRegex(RuntimeError, "broken"):
            check_tool_result(result)

    def test_legacy_sdk_error_is_failure(self):
        result = SimpleNamespace(isError=True, content=[SimpleNamespace(type="text", text="broken")])
        with self.assertRaises(RuntimeError):
            check_tool_result(result)

    def test_transport_success_with_error_text_is_failure(self):
        result = SimpleNamespace(is_error=False, content=[SimpleNamespace(type="text", text="details\n [ERROR] no project")])
        with self.assertRaisesRegex(RuntimeError, "no project"):
            check_tool_result(result)

    def test_success_keeps_full_text(self):
        payload = "all evidence " * 2000
        result = SimpleNamespace(is_error=False, content=[SimpleNamespace(type="text", text=payload)])
        self.assertEqual(check_tool_result(result), [payload])


if __name__ == "__main__":
    unittest.main()
