#!/usr/bin/env python3
"""Compatibility wrapper for the legacy development my-cua composite."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def translated_argv(arguments: list[str]) -> list[str]:
    result: list[str] = []
    has_adapter = False
    index = 0
    while index < len(arguments):
        value = arguments[index]
        if value == "--cua-cli":
            result.append("--target-adapter")
            has_adapter = True
        elif value == "--target-adapter":
            result.append(value)
            has_adapter = True
        else:
            result.append(value)
        index += 1
    if not has_adapter:
        result[0:0] = [
            "--target-adapter",
            str(Path.home() / ".codex" / "skills" / "my-cua-dev" / "scripts" / "cua.py"),
        ]
    return result


if __name__ == "__main__":
    sys.argv = [sys.argv[0], *translated_argv(sys.argv[1:])]
    runpy.run_path(str(Path(__file__).with_name("sync-cua.py")), run_name="__main__")
