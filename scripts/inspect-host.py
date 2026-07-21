#!/usr/bin/env python3
"""Emit minimal, non-sensitive host facts needed by the Skill."""

from __future__ import annotations

import json
import os
import platform
import shutil
import stat
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

DEFAULT_RUNTIME_DESCRIPTOR_PATH = Path("/run/credential-agent/runtime.json")
MAX_RUNTIME_DESCRIPTOR_BYTES = 16 << 10


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
        # Some Chromium builds replace argv with one human-readable process
        # title. Recover the usual whitespace-free flag value just as the
        # Agent does; ambiguous paths can still be supplied explicitly.
        if len(arguments) == 1:
            arguments = arguments[0].split()
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


def read_runtime_descriptor(
    descriptor_path: Path | None = None,
    system: str | None = None,
) -> dict[str, object]:
    if (system or platform.system()).lower() != "linux":
        return {}
    overridden = descriptor_path is not None or bool(
        os.environ.get("CREDENTIAL_AGENT_RUNTIME_DESCRIPTOR_PATH", "").strip()
    )
    if descriptor_path is None:
        descriptor_path = Path(
            os.environ.get(
                "CREDENTIAL_AGENT_RUNTIME_DESCRIPTOR_PATH",
                str(DEFAULT_RUNTIME_DESCRIPTOR_PATH),
            )
        )
    if not descriptor_path.is_absolute():
        return {}
    try:
        info = descriptor_path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            return {}
        if stat.S_IMODE(info.st_mode) & 0o022:
            return {}
        if info.st_uid != 0 and not (overridden and info.st_uid == os.geteuid()):
            return {}
        if info.st_size > MAX_RUNTIME_DESCRIPTOR_BYTES:
            return {}
        payload = json.loads(descriptor_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return {}
    runtime_value = payload.get("runtime")
    daemon_value = payload.get("daemon")
    browser_value = payload.get("browser")
    kind = runtime_value.get("kind", "") if isinstance(runtime_value, dict) else ""
    manager = daemon_value.get("manager", "") if isinstance(daemon_value, dict) else ""
    if not isinstance(kind, str) or not kind.replace("_", "").replace("-", "").isalnum():
        return {}
    if manager not in {"platform", "external", "none"}:
        return {}
    user_data_dirs: list[str] = []
    if isinstance(browser_value, dict) and isinstance(browser_value.get("user_data_dirs"), list):
        for raw in browser_value["user_data_dirs"]:
            if not isinstance(raw, str):
                continue
            path = Path(raw).expanduser()
            if path.is_absolute() and path.is_dir():
                resolved = str(path.resolve())
                if resolved not in user_data_dirs:
                    user_data_dirs.append(resolved)
    return {
        "kind": kind,
        "daemon_manager": manager,
        "browser_user_data_dirs": user_data_dirs,
    }


def runtime_hints(descriptor: dict[str, object] | None = None) -> dict[str, Optional[str]]:
    kind = os.environ.get("CREDENTIAL_AGENT_RUNTIME_KIND", "").strip()
    if not kind.replace("_", "").replace("-", "").isalnum():
        kind = ""
    daemon_manager = os.environ.get("CREDENTIAL_AGENT_DAEMON_MANAGER", "").strip()
    if daemon_manager not in {"platform", "external", "none"}:
        daemon_manager = ""
    if descriptor is None:
        descriptor = read_runtime_descriptor()
    return {
        "kind": kind or str(descriptor.get("kind") or "desktop"),
        "daemon_manager_hint": daemon_manager or str(descriptor.get("daemon_manager") or "") or None,
    }


def main() -> None:
    goos = platform.system().lower()
    goos = {"darwin": "darwin", "windows": "windows", "linux": "linux"}.get(goos, goos)
    agent = agent_path(goos)
    running_chrome, user_data_dirs = running_linux_chromium()
    descriptor = read_runtime_descriptor(system=goos)
    for path in descriptor.get("browser_user_data_dirs", []):
        if isinstance(path, str) and path not in user_data_dirs:
            user_data_dirs.append(path)
    user_data_dirs.sort()
    chrome = chrome_path(goos) or running_chrome
    output = {
        "schema_version": 1,
        "os": goos,
        "arch": normalized_arch(),
        "interactive": bool(sys.stdin.isatty() and sys.stdout.isatty()),
        "runtime": runtime_hints(descriptor),
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
