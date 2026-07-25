import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillReleaseTests(unittest.TestCase):
    def test_release_is_deterministic_and_signature_verifies(self):
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            private_key = temp / "private.pem"
            public_key = temp / "public.pem"
            subprocess.run(
                ["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(private_key)],
                check=True,
                capture_output=True,
            )
            private_key.chmod(0o600)
            subprocess.run(
                ["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)],
                check=True,
                capture_output=True,
            )
            digests = []
            for index in (1, 2):
                output = temp / f"release-{index}"
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "build-skill-release.py"),
                        "--version", "1.2.3",
                        "--source-commit", "a" * 40,
                        "--archive-url", "https://release.example/credential-skill-1.2.3.zip",
                        "--private-key", str(private_key),
                        "--output-dir", str(output),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                result = json.loads(completed.stdout)
                archive = Path(result["archive"])
                digests.append(hashlib.sha256(archive.read_bytes()).hexdigest())
                verified = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "verify-skill-release.py"),
                        "--manifest", str(output / "latest.json"),
                        "--archive", str(archive),
                        "--public-key", str(public_key),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertTrue(json.loads(verified.stdout)["ok"])
            self.assertEqual(digests[0], digests[1])


if __name__ == "__main__":
    unittest.main()
