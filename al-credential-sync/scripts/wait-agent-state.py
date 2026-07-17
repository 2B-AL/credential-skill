#!/usr/bin/env python3
"""Wait for a future machine-readable credential-agent state without prose parsing."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def nested(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for component in path.split("."):
        if not isinstance(current, dict) or component not in current:
            return None
        current = current[component]
    return current


def probe(agent: Path, command: str) -> dict[str, Any]:
    args = [str(agent), command, "--output", "json"]
    if command == "doctor":
        args.insert(2, "--strict")
    completed = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode not in (0, 1):
        raise RuntimeError("machine-readable Agent command is unavailable")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("machine-readable Agent command is unavailable") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Agent JSON output is not an object")
    return value


def parse_expected(raw: str) -> Any:
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--command", choices=("status", "doctor"), default="status")
    parser.add_argument("--field", required=True)
    parser.add_argument("--equals", required=True)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--interval", type=float, default=1)
    args = parser.parse_args()
    agent = Path(args.agent).expanduser().resolve()
    if not agent.is_file():
        print("Agent executable does not exist", file=sys.stderr)
        return 2
    deadline = time.monotonic() + args.timeout
    expected = parse_expected(args.equals)
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        try:
            last = probe(agent, args.command)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 3
        if nested(last, args.field) == expected:
            json.dump(last, sys.stdout, ensure_ascii=False, separators=(",", ":"))
            sys.stdout.write("\n")
            return 0
        time.sleep(max(args.interval, 0.1))
    print(
        json.dumps(
            {"ok": False, "code": "WAIT_TIMEOUT", "field": args.field, "last": last},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        file=sys.stderr,
    )
    return 11


if __name__ == "__main__":
    raise SystemExit(main())
