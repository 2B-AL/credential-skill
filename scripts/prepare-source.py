#!/usr/bin/env python3
"""Install and prepare the personal Credential source using public Agent CLIs."""

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_BASE = "https://al-artifacts-bj.tos-cn-beijing.volces.com"


def browser_prepare_command(agent):
    return [
        str(agent),
        "browser",
        "prepare",
        "--artifact-base-url",
        DEFAULT_ARTIFACT_BASE,
        "--output",
        "json",
    ]


def safe_agent(path):
    value = Path(path).expanduser()
    try:
        info = value.lstat()
    except OSError:
        return None
    if not value.is_absolute() or not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_mode & 0o022 or not os.access(value, os.X_OK):
        return None
    return value


def run(command, timeout, *, interactive=False):
    completed = subprocess.run(
        command,
        stdin=None if interactive else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=None if interactive else subprocess.DEVNULL,
        text=True,
        timeout=timeout,
        check=False,
    )
    return completed


def json_result(completed):
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {}


def default_agent():
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / "AL" / "CredentialAgent" / "credential-agent.exe"
    return Path.home() / ".local" / "bin" / "credential-agent"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-path")
    parser.add_argument("--skip-browser", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    agent = safe_agent(args.agent_path or default_agent())
    installed = False
    if agent is None:
        bootstrap = run([sys.executable, str(ROOT / "scripts" / "bootstrap-agent.py")], min(args.timeout_seconds, 240))
        if bootstrap.returncode:
            print(json.dumps({"schema_version": 1, "status": "failed", "error": {"code": "AGENT_INSTALL_FAILED"}}))
            return 1
        agent = safe_agent(args.agent_path or default_agent())
        if agent is None:
            print(json.dumps({"schema_version": 1, "status": "failed", "error": {"code": "AGENT_INSTALL_INVALID"}}))
            return 1
        installed = True
    capabilities = json_result(run([str(agent), "capabilities", "--output", "json"], 30))
    enrollment = capabilities.get("enrollment") if isinstance(capabilities.get("enrollment"), dict) else {}
    if enrollment.get("valid") is not True:
        setup = run([str(agent), "setup", "--role", "personal", "--skip-browser"], args.timeout_seconds, interactive=True)
        if setup.returncode:
            print(json.dumps({"schema_version": 1, "status": "failed", "error": {"code": "SOURCE_SETUP_FAILED"}}))
            return 1
        capabilities = json_result(run([str(agent), "capabilities", "--output", "json"], 30))
        enrollment = capabilities.get("enrollment") if isinstance(capabilities.get("enrollment"), dict) else {}
    if enrollment.get("valid") is not True:
        print(json.dumps({"schema_version": 1, "status": "failed", "error": {"code": "SOURCE_ENROLLMENT_REQUIRED"}}))
        return 1
    if not args.skip_browser:
        prepared = run(browser_prepare_command(agent), min(args.timeout_seconds, 180))
        if prepared.returncode:
            print(json.dumps({"schema_version": 1, "status": "failed", "error": {"code": "SOURCE_BROWSER_PREPARE_FAILED"}}))
            return 1
        activated = run([str(agent), "browser", "activate", "--timeout", "2m", "--output", "json"], min(args.timeout_seconds, 150))
        if activated.returncode:
            print(json.dumps({"schema_version": 1, "status": "failed", "error": {"code": "SOURCE_BROWSER_USER_ACTION_REQUIRED"}}))
            return 1
        waited = run([str(agent), "browser", "wait", "--for", "connected", "--timeout", "5m", "--output", "json"], min(args.timeout_seconds, 310))
        if waited.returncode:
            print(json.dumps({"schema_version": 1, "status": "failed", "error": {"code": "SOURCE_BROWSER_NOT_CONNECTED"}}))
            return 1
    doctor = run([str(agent), "doctor", "--strict", "--output", "json"], min(args.timeout_seconds, 90))
    if doctor.returncode:
        print(json.dumps({"schema_version": 1, "status": "failed", "error": {"code": "SOURCE_HEALTH_FAILED"}}))
        return 1
    print(json.dumps({
        "schema_version": 1,
        "status": "succeeded",
        "agent_path": str(agent),
        "agent_installed": installed,
        "device_ready": True,
        "browser_ready": not args.skip_browser,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
