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
from typing import Optional


LINUX_CHROMIUM_EXECUTABLES = {
    "chrome",
    "chromium",
    "google-chrome",
    "google-chrome-stable",
}


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
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chrome"):
            found = shutil.which(name)
            if found:
                return str(Path(found).resolve())
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return ""


def running_linux_chromium(
    proc: Path = Path("/proc"),
    current_uid: int | None = None,
    system: str | None = None,
    ps_output: str | None = None,
) -> tuple[str, list[str]]:
    """Return only non-sensitive facts from the current user's browser argv."""

    if (system or platform.system()).lower() != "linux":
        return "", []
    if current_uid is None:
        current_uid = os.geteuid()
    executable = ""
    user_data_dirs: set[str] = set()

    def observe(arguments: list[str], candidate: str = "") -> None:
        nonlocal executable
        if not arguments or Path(arguments[0]).name not in LINUX_CHROMIUM_EXECUTABLES:
            return
        if any(argument.startswith("--type=") for argument in arguments[1:]):
            return
        if candidate and not executable:
            executable = candidate
        for index, argument in enumerate(arguments[1:], start=1):
            value = ""
            if argument.startswith("--user-data-dir="):
                value = argument.split("=", 1)[1]
            elif argument == "--user-data-dir" and index+1 < len(arguments):
                value = arguments[index+1]
            if not value:
                continue
            path = Path(value).expanduser()
            if path.is_absolute() and path.is_dir():
                user_data_dirs.add(str(path.resolve()))

    try:
        entries = list(proc.iterdir())
    except OSError:
        entries = []
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != current_uid:
                continue
            with (entry / "cmdline").open("rb") as command:
                raw = command.read(64 << 10)
        except OSError:
            continue
        arguments = [part.decode("utf-8", "surrogateescape") for part in raw.split(b"\0") if part]
        if not arguments:
            continue
        try:
            candidate = str((entry / "exe").resolve(strict=True))
        except OSError:
            candidate = arguments[0] if Path(arguments[0]).is_absolute() else ""
        observe(arguments, candidate)

    if ps_output is None:
        try:
            ps_output = subprocess.run(
                ["ps", "-u", str(current_uid), "-o", "args="],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            ps_output = ""
    for line in ps_output.splitlines():
        arguments = line.split()
        candidate = arguments[0] if arguments and Path(arguments[0]).is_absolute() else ""
        observe(arguments, candidate)
    return executable, sorted(user_data_dirs)


def agent_path(goos: str) -> Path:
    if goos == "windows":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "AL" / "CredentialAgent" / "credential-agent.exe" if local else Path()
    candidates = [
        Path.home() / ".local" / "bin" / "credential-agent",
        Path("/usr/local/bin/credential-agent"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def runtime_hints() -> dict[str, Optional[str]]:
    kind = os.environ.get("CREDENTIAL_AGENT_RUNTIME_KIND", "").strip()
    if not kind.replace("_", "").replace("-", "").isalnum():
        kind = ""
    daemon_manager = os.environ.get("CREDENTIAL_AGENT_DAEMON_MANAGER", "").strip()
    if daemon_manager not in {"platform", "external", "none"}:
        daemon_manager = ""
    return {
        "kind": kind or "desktop",
        "daemon_manager_hint": daemon_manager or None,
    }


def main() -> None:
    goos = platform.system().lower()
    goos = {"darwin": "darwin", "windows": "windows", "linux": "linux"}.get(goos, goos)
    agent = agent_path(goos)
    running_chrome, user_data_dirs = running_linux_chromium()
    chrome = chrome_path(goos) or running_chrome
    output = {
        "schema_version": 1,
        "os": goos,
        "arch": normalized_arch(),
        "interactive": bool(sys.stdin.isatty() and sys.stdout.isatty()),
        "runtime": runtime_hints(),
        "chrome": {
            "installed": bool(chrome),
            "executable": chrome or None,
            "user_data_dirs": user_data_dirs,
        },
        "agent": {
            "installed": bool(str(agent)) and agent.is_file(),
            "path": str(agent.resolve(strict=False)) if str(agent) else None,
        },
    }
    json.dump(output, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
