#!/usr/bin/env python3
"""Verify an al-credential-sync signed release manifest and local archive."""

import argparse
import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def canonical(manifest):
    unsigned = dict(manifest)
    unsigned.pop("signature", None)
    return json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--public-key", required=True)
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("skill") != "al-credential-sync" or "cua-target/v1" not in (manifest.get("adapter_protocols") or []):
        raise SystemExit("manifest identity is invalid")
    signature = base64.urlsafe_b64decode(str(manifest.get("signature")) + "=" * ((4 - len(str(manifest.get("signature"))) % 4) % 4))
    archive = Path(args.archive).read_bytes()
    if len(archive) != int(manifest.get("archive_size") or 0) or hashlib.sha256(archive).hexdigest() != manifest.get("archive_sha256"):
        raise SystemExit("archive integrity check failed")
    with tempfile.TemporaryDirectory() as tmp:
        message = Path(tmp) / "manifest.json"
        sig = Path(tmp) / "signature.bin"
        message.write_bytes(canonical(manifest))
        sig.write_bytes(signature)
        verified = subprocess.run(
            ["openssl", "pkeyutl", "-verify", "-pubin", "-rawin", "-inkey", args.public_key, "-in", str(message), "-sigfile", str(sig)],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    if not verified:
        raise SystemExit("manifest signature is invalid")
    print(json.dumps({"ok": True, "version": manifest.get("version"), "sha256": manifest.get("archive_sha256"), "size": len(archive)}))


if __name__ == "__main__":
    main()
