import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LocalLifecycleContractTest(unittest.TestCase):
    def test_skill_uses_guided_first_install_background_reload_and_full_uninstall(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        browser = (ROOT / "references" / "browser-installation.md").read_text(encoding="utf-8")
        security = (ROOT / "references" / "security-rules.md").read_text(encoding="utf-8")
        mac_assist = (ROOT / "scripts" / "browser-assist-macos.sh").read_text(encoding="utf-8")
        self.assertIn("browser activate", skill)
        self.assertIn("RELOAD_SELF", browser)
        self.assertIn("BROWSER_INSTALL_USER_ACTION_REQUIRED", skill)
        self.assertNotIn("browser install-auto", skill)
        self.assertNotIn("browser install-auto", browser)
        self.assertNotIn("visible-auto-install", skill)
        self.assertNotIn("Accessibility permission for installation", browser)
        self.assertIn('open -R "$DIRECTORY/manifest.json"', mac_assist)
        self.assertNotIn("osascript", mac_assist)
        self.assertIn("credential-agent uninstall --yes", skill)
        self.assertIn("Chrome Profile/Cookies", security)
        self.assertNotIn("rm -rf", skill)


if __name__ == "__main__":
    unittest.main()
