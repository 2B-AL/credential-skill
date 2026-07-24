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

    def test_target_permission_preparation_keeps_the_original_sync_job(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        browser = (ROOT / "references" / "browser-installation.md").read_text(encoding="utf-8")
        command_map = (ROOT / "references" / "agent-command-map.md").read_text(encoding="utf-8")
        self.assertIn("metadata-only `UPDATE_SITE_POLICY`", skill)
        self.assertIn("keeps the same Job active", skill)
        self.assertIn("let the same Job continue", browser)
        self.assertIn("only then runs Restore in the same Job", command_map)
        self.assertNotIn("with its restore task", skill)

    def test_cua_pair_auto_and_reset_stay_adapter_scoped(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        security = (ROOT / "references" / "security-rules.md").read_text(encoding="utf-8")
        troubleshooting = (ROOT / "references" / "troubleshooting.md").read_text(encoding="utf-8")
        self.assertIn("credential-agent pair-auto", skill)
        self.assertIn("credential-agent reset-e2e", skill)
        self.assertIn("Linux sandbox", skill)
        self.assertIn("one-time HPKE envelope", security)
        self.assertIn("private regular files", security)
        self.assertIn("INVOCATION_NOT_FOUND", troubleshooting)
        self.assertIn("pair_ready=true", troubleshooting)

    def test_cua_fast_path_uses_one_job_async_authorization_and_policy_bounded_network(self):
        script = (ROOT / "scripts" / "sync-my-cua.py").read_text(encoding="utf-8")
        self.assertIn('"pair-auto", "--keep-session"', script)
        self.assertIn('"create_sync_job"', script)
        self.assertIn('"authorize-begin"', script)
        self.assertIn('"network-ensure"', script)
        self.assertIn('"authorize-watch"', script)
        self.assertIn('"job", "wait", job_id', script)
        self.assertNotIn("browser sync --all", script)
        self.assertNotIn("pairing_code", script)
        self.assertNotIn("cookie", script.lower())


if __name__ == "__main__":
    unittest.main()
