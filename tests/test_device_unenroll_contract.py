import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class DeviceUnenrollContractTests(unittest.TestCase):
    def test_skill_uses_public_self_unenrollment_command(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("device unenroll --yes", skill)
        self.assertIn("central_revoked=true", skill)
        self.assertIn("local_state_cleared=true", skill)
        self.assertIn("never delete Agent state files yourself", skill)

    def test_skill_preserves_browser_and_restored_data(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("browser profile/Cookies", skill)
        self.assertIn("restored files", skill)
        self.assertIn("central Secrets", skill)

    def test_cloud_and_external_targets_stay_connector_owned(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        security = (ROOT / "references" / "security-rules.md").read_text(encoding="utf-8")
        self.assertIn("Do not run self-unenrollment on a device-only cloud endpoint", skill)
        self.assertIn("externally supervised targets", security)
        self.assertIn("exact Device ID", security)


if __name__ == "__main__":
    unittest.main()
