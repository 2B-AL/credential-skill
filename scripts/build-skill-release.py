#!/usr/bin/env python3
"""Build a deterministic, externally signed al-credential-sync release."""

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import urllib.parse
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDES = {".git", ".idea", "__pycache__", "dist"}


def release_files(output=None):
    output = output.resolve() if output else None
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if path.resolve() == output or any(part in EXCLUDES for part in relative.parts) or path.is_symlink() or not path.is_file():
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        yield path, relative


def build_archive(output):
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative in release_files(output):
            info = zipfile.ZipInfo("al-credential-sync/" + relative.as_posix(), (2020, 1, 1, 0, 0, 0))
            executable = os.access(path, os.X_OK) or path.suffix in {".py", ".sh"}
            info.external_attr = (0o700 if executable else 0o600) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def canonical(manifest):
    return json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--archive-url", required=True)
    parser.add_argument("--private-key", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.version):
        raise SystemExit("version contains unsupported characters")
    if not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", args.source_commit):
        raise SystemExit("source commit must be a 40 or 64 character hexadecimal digest")
    archive_url = urllib.parse.urlsplit(args.archive_url)
    if archive_url.scheme != "https" or not archive_url.netloc or archive_url.username or archive_url.password:
        raise SystemExit("archive URL must use credential-free HTTPS")
    private_key = Path(args.private_key).expanduser().resolve()
    info = private_key.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_mode & 0o077:
        raise SystemExit("private key must be a 0600 non-symlink regular file")
    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / f"credential-skill-{args.version}.zip"
    build_archive(archive_path)
    archive_raw = archive_path.read_bytes()
    manifest = {
        "schema_version": 1,
        "skill": "al-credential-sync",
        "version": args.version,
        "adapter_protocols": ["cua-target/v1"],
        "archive_url": args.archive_url,
        "archive_size": len(archive_raw),
        "archive_sha256": hashlib.sha256(archive_raw).hexdigest(),
        "source_commit": args.source_commit,
    }
    with tempfile.TemporaryDirectory() as tmp:
        message = Path(tmp) / "manifest.json"
        signature = Path(tmp) / "signature.bin"
        message.write_bytes(canonical(manifest))
        subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private_key), "-in", str(message), "-out", str(signature)],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        manifest["signature"] = base64.urlsafe_b64encode(signature.read_bytes()).decode("ascii").rstrip("=")
    manifest_path = output / "latest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "archive": str(archive_path), "manifest": str(manifest_path), "sha256": manifest["archive_sha256"], "size": manifest["archive_size"]}))


if __name__ == "__main__":
    main()
