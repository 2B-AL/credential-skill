import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BEIJING_ARTIFACT_BASE = "https://al-artifacts-bj.tos-cn-beijing.volces.com"


def load_script(module_name, relative_path):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ArtifactOriginTests(unittest.TestCase):
    def test_bootstraps_default_to_beijing(self):
        bootstrap = load_script("bootstrap_agent", "scripts/bootstrap-agent.py")
        self.assertEqual(bootstrap.DEFAULT_ARTIFACT_BASE, BEIJING_ARTIFACT_BASE)

        windows_bootstrap = (ROOT / "scripts/bootstrap-agent-windows.ps1").read_text()
        self.assertIn(
            f'[string]$ArtifactBaseURL = "{BEIJING_ARTIFACT_BASE}"',
            windows_bootstrap,
        )

    def test_browser_prepare_uses_beijing_artifacts(self):
        prepare_source = load_script("prepare_source", "scripts/prepare-source.py")
        command = prepare_source.browser_prepare_command(Path("/safe/credential-agent"))
        self.assertEqual(prepare_source.DEFAULT_ARTIFACT_BASE, BEIJING_ARTIFACT_BASE)
        self.assertEqual(
            command,
            [
                "/safe/credential-agent",
                "browser",
                "prepare",
                "--artifact-base-url",
                BEIJING_ARTIFACT_BASE,
                "--output",
                "json",
            ],
        )


if __name__ == "__main__":
    unittest.main()
