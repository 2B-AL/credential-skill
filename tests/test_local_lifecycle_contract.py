import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LocalLifecycleContractTest(unittest.TestCase):
    def test_skill_uses_agent_owned_mac_install_and_full_uninstall(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        browser = (ROOT / "references" / "browser-installation.md").read_text(encoding="utf-8")
        security = (ROOT / "references" / "security-rules.md").read_text(encoding="utf-8")
        self.assertIn("browser install-auto", skill)
        self.assertIn("visible-auto-install", browser)
        self.assertIn("credential-agent uninstall --yes", skill)
        self.assertIn("Chrome Profile/Cookies", security)
        self.assertNotIn("rm -rf", skill)


if __name__ == "__main__":
    unittest.main()
