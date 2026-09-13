import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("response_guard", Path(__file__).with_name("response_guard.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def text(value, **extra):
    return {"isError": False, "content": [{"type": "text", "text": value}], **extra}


class ResponseGuardTests(unittest.TestCase):
    def test_known_missing_module_with_false_iserror(self):
        self.assertEqual(module.classify_response("get_addon_status", text("Error checking addon status: No module named blender_mcp.config"))["status"], "FAILED")

    def test_safe_mode_rejection(self):
        self.assertEqual(module.classify_response("execute_blender_code", text("Rejected by safe mode: blocked"))["status"], "FAILED")

    def test_transport_error(self):
        self.assertEqual(module.classify_response("get_scene_info", text("something", isError=True))["status"], "FAILED")

    def test_json_error(self):
        self.assertEqual(module.classify_response("get_scene_info", text('{"error":"disconnected"}'))["status"], "FAILED")

    def test_structured_error(self):
        self.assertEqual(module.classify_response("get_scene_info", text("ok", structuredContent={"success": False}))["status"], "FAILED")

    def test_valid_scene(self):
        self.assertEqual(module.classify_response("get_scene_info", text('{"objects":[]}'))["status"], "PASSED")

    def test_valid_execution(self):
        self.assertEqual(module.classify_response("execute_blender_code", text("Code executed successfully: completed"))["status"], "PASSED")

    def test_valid_screenshot(self):
        self.assertEqual(module.classify_response("get_viewport_screenshot", {"content": [{"type": "image", "local_image": "frame.png"}]})["status"], "PASSED")

    def test_fake_screenshot_text(self):
        self.assertEqual(module.classify_response("get_viewport_screenshot", text("screenshot created"))["status"], "FAILED")

    def test_empty_content(self):
        self.assertEqual(module.classify_response("get_scene_info", {"content": []})["status"], "FAILED")

    def test_false_json_success(self):
        self.assertEqual(module.classify_response("get_scene_info", text('{"success":false}'))["status"], "FAILED")

    def test_unknown_block_not_auto_accepted(self):
        self.assertEqual(module.classify_response("get_scene_info", {"content": [{"type": "resource"}]})["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
