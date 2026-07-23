import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class CuaConnectorContractTests(unittest.TestCase):
    def test_skill_routes_development_my_cua_through_connector(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("credential-browser ensure", skill)
        self.assertIn("authenticated CDP", skill)
        self.assertIn("UIA only for the Chrome-owned native folder picker", skill)
        self.assertIn("generic Linux/macOS unpacked workflow", skill)
        self.assertNotIn("`managed_store`: unmanaged Windows CUA", skill)

    def test_browser_reference_forbids_screenshot_success_path(self):
        reference = (ROOT / "references" / "browser-installation.md").read_text(encoding="utf-8")
        self.assertIn("my-cua Connector-owned unpacked automation", reference)
        self.assertIn("Never use screenshots", reference)
        self.assertIn("do not fall back to extension-page UIA", reference)

    def test_command_map_keeps_store_mode_explicit(self):
        command_map = (ROOT / "references" / "agent-command-map.md").read_text(encoding="utf-8")
        self.assertIn("Only a target explicitly configured for a published Store item", command_map)
        self.assertIn("credential-browser ensure", command_map)
        self.assertNotIn("# Unmanaged Windows CUA", command_map)


if __name__ == "__main__":
    unittest.main()
