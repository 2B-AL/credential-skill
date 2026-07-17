#!/usr/bin/env python3
"""Emit minimal, non-sensitive host facts needed by the Skill."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def normalized_arch() -> str:
    machine = platform.machine().lower()
    system = platform.system().lower()
    if system == "darwin":
        try:
            apple_silicon = subprocess.run(
                ["/usr/sbin/sysctl", "-n", "hw.optional.arm64"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout.strip()
            if apple_silicon == "1":
                machine = "arm64"
        except (OSError, subprocess.SubprocessError):
            pass
    if system in ("darwin", "linux") and machine != "arm64":
        try:
            native = subprocess.run(
                ["uname", "-m"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout.strip().lower()
            if native:
                machine = native
        except (OSError, subprocess.SubprocessError):
            pass
    return {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine, machine)


def chrome_path(goos: str) -> str:
    candidates: list[Path] = []
    if goos == "darwin":
        candidates = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    elif goos == "windows":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            if os.environ.get(variable):
                candidates.append(
                    Path(os.environ[variable]) / "Google" / "Chrome" / "Application" / "chrome.exe"
                )
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium"):
            found = shutil.which(name)
            if found:
                return str(Path(found).resolve())
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return ""


def agent_path(goos: str) -> Path:
    if goos == "windows":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "AL" / "CredentialAgent" / "credential-agent.exe" if local else Path()
    return Path.home() / ".local" / "bin" / "credential-agent"


def main() -> None:
    goos = platform.system().lower()
    goos = {"darwin": "darwin", "windows": "windows", "linux": "linux"}.get(goos, goos)
    agent = agent_path(goos)
    chrome = chrome_path(goos)
    output = {
        "schema_version": 1,
        "os": goos,
        "arch": normalized_arch(),
        "interactive": bool(sys.stdin.isatty() and sys.stdout.isatty()),
        "chrome": {"installed": bool(chrome), "executable": chrome or None},
        "agent": {
            "installed": bool(str(agent)) and agent.is_file(),
            "path": str(agent.resolve(strict=False)) if str(agent) else None,
        },
    }
    json.dump(output, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
