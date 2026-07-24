#!/usr/bin/env python3
"""Run one exact-site Credential sync through the trusted my-cua adapter."""

from __future__ import annotations

import argparse
import json
import os
import queue
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path


class WorkflowError(RuntimeError):
    def __init__(self, code: str, message: str, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def emit(value: dict) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def safe_executable(value: str, label: str, *, python_script: bool = False) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise WorkflowError("PATH_INVALID", f"{label} must be an absolute path.")
    try:
        info = path.lstat()
    except OSError as exc:
        raise WorkflowError("PATH_INVALID", f"{label} does not exist.") from exc
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_mode & 0o022:
        raise WorkflowError("PATH_UNSAFE", f"{label} must be a non-symlink regular file not writable by group or others.")
    if not python_script and not os.access(path, os.X_OK):
        raise WorkflowError("PATH_UNSAFE", f"{label} must be executable.")
    return path


def site_names(values: list[str]) -> list[str]:
    result = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    if not result or len(result) > 32:
        raise WorkflowError("SITE_INVALID", "Pass between one and 32 exact site ids.")
    for site in result:
        if len(site) > 80 or not site[0].isalnum() or not all(char.isalnum() or char in "._-" for char in site):
            raise WorkflowError("SITE_INVALID", "Every site id must use only letters, numbers, dot, underscore, or hyphen.")
    return result


def parse_result(stdout: str, code: str) -> dict:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise WorkflowError(code, "Command returned no machine-readable result.")
    try:
        value = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise WorkflowError(code, "Command returned invalid machine-readable output.") from exc
    if not isinstance(value, dict):
        raise WorkflowError(code, "Command returned a non-object result.")
    return value


def run_json(command: list[str], timeout_seconds: int, code: str) -> dict:
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise WorkflowError(code, "Command timed out.") from exc
    value = parse_result(completed.stdout, code)
    if completed.returncode != 0 or value.get("ok") is False:
        error = value.get("error") if isinstance(value.get("error"), dict) else {}
        raise WorkflowError(
            str(error.get("code") or code),
            str(error.get("message") or "Command failed."),
            upstream_code=error.get("upstream_code"),
        )
    return value


def cua_command(cua_cli: Path, *arguments: str) -> list[str]:
    return [sys.executable, str(cua_cli), *arguments]


def start_jsonl(command: list[str]) -> tuple[subprocess.Popen, queue.Queue]:
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    events: queue.Queue = queue.Queue()

    def read_output() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            events.put(line)
        events.put(None)

    threading.Thread(target=read_output, daemon=True).start()
    return process, events


def read_event(events: queue.Queue, deadline: float) -> dict | None:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise WorkflowError("SYNC_TIMEOUT", "Timed out waiting for source Agent output.")
    try:
        line = events.get(timeout=remaining)
    except queue.Empty as exc:
        raise WorkflowError("SYNC_TIMEOUT", "Timed out waiting for source Agent output.") from exc
    if line is None:
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError as exc:
        raise WorkflowError("SOURCE_OUTPUT_INVALID", "Source Agent returned invalid JSONL output.") from exc
    if not isinstance(event, dict):
        raise WorkflowError("SOURCE_OUTPUT_INVALID", "Source Agent returned a non-object event.")
    emit({"schema_version": 1, "type": "source_event", "event": event})
    return event


def wait_jsonl_result(process: subprocess.Popen, events: queue.Queue, deadline: float) -> dict:
    result = None
    while True:
        event = read_event(events, deadline)
        if event is None:
            break
        if event.get("type") == "result":
            result = event
    remaining = max(0.1, deadline - time.monotonic())
    try:
        return_code = process.wait(timeout=remaining)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise WorkflowError("SYNC_TIMEOUT", "Source Agent did not exit after its final output.") from exc
    if return_code != 0 or not result:
        raise WorkflowError("SOURCE_SYNC_FAILED", "Source Agent sync failed before a final result.")
    return result


def ensure_target_network(cua_cli: Path, session_id: str, sites: list[str], deadline: float) -> dict:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WorkflowError("NETWORK_TIMEOUT", "Timed out waiting for target site policies before network probing.")
        try:
            return run_json(
                cua_command(
                    cua_cli,
                    "credential-browser",
                    "network-ensure",
                    *sites,
                    "--session-id",
                    session_id,
                    "--timeout-seconds",
                    str(max(1, min(90, int(remaining)))),
                ),
                max(2, min(95, int(remaining) + 1)),
                "TARGET_NETWORK_FAILED",
            )
        except WorkflowError as exc:
            if exc.message != "credential_browser_site_policy_missing":
                raise
            time.sleep(min(0.5, remaining))


def run(args: argparse.Namespace) -> dict:
    started = time.monotonic()
    agent = safe_executable(args.agent_path, "credential-agent")
    cua_cli = safe_executable(args.cua_cli, "my-cua-dev CLI", python_script=True)
    sites = site_names(args.site)
    deadline = started + args.timeout_seconds

    validated = run_json(
        [str(agent), "browser", "validate", "--output", "json", *sites],
        min(90, args.timeout_seconds),
        "SOURCE_VALIDATION_FAILED",
    )
    if validated.get("status") != "succeeded":
        raise WorkflowError("SOURCE_VALIDATION_FAILED", "Source browser login validation failed.")
    emit({"schema_version": 1, "type": "phase", "phase": "source_validate", "status": "succeeded"})

    paired = run_json(
        cua_command(cua_cli, "credential-agent", "pair-auto", "--keep-session", "--timeout-seconds", str(min(240, args.timeout_seconds))),
        min(250, args.timeout_seconds),
        "TARGET_PAIR_FAILED",
    )
    pair_data = paired.get("data") if isinstance(paired.get("data"), dict) else {}
    device_id = str(pair_data.get("device_id") or "").strip()
    session_id = str(pair_data.get("session_id") or "").strip()
    if not device_id or not session_id or pair_data.get("browser_connected") is not True:
        raise WorkflowError("TARGET_PAIR_FAILED", "CUA pairing did not return an exact ready device and workflow session.")
    emit({"schema_version": 1, "type": "phase", "phase": "target_pair", "status": "succeeded", "device_id": device_id})

    source, source_events = start_jsonl([
        str(agent), "browser", "sync", "--to", device_id, "--yes", "--output", "jsonl", *sites
    ])
    job_id = ""
    source_result = None
    try:
        while True:
            event = read_event(source_events, deadline)
            if event is None:
                break
            if event.get("type") == "phase" and event.get("phase") == "create_sync_job" and event.get("status") == "succeeded":
                details = event.get("details") if isinstance(event.get("details"), dict) else {}
                job = details.get("job") if isinstance(details.get("job"), dict) else {}
                job_id = str(job.get("id") or "").strip()
                break
        if not job_id:
            source_result = wait_jsonl_result(source, source_events, deadline)
            raise WorkflowError("SYNC_JOB_MISSING", "Source Agent did not create an authoritative Sync Job.")

        authorization = run_json(
            cua_command(
                cua_cli,
                "credential-browser",
                "authorize-begin",
                *sites,
                "--session-id",
                session_id,
                "--timeout-seconds",
                "30",
            ),
            35,
            "TARGET_AUTHORIZATION_FAILED",
        )
        authorization_data = authorization.get("data") if isinstance(authorization.get("data"), dict) else {}
        operation = authorization_data.get("operation") if isinstance(authorization_data.get("operation"), dict) else {}
        operation_id = str(operation.get("operation_id") or "").strip()
        if not operation_id:
            raise WorkflowError("TARGET_AUTHORIZATION_FAILED", "CUA did not return an authorization operation id.")

        network = ensure_target_network(cua_cli, session_id, sites, deadline)
        network_data = network.get("data") if isinstance(network.get("data"), dict) else {}
        emit({
            "schema_version": 1,
            "type": "phase",
            "phase": "target_network",
            "status": "succeeded",
            "mode": (network_data.get("network") or {}).get("mode"),
        })

        authorized = run_json(
            cua_command(
                cua_cli,
                "credential-browser",
                "authorize-watch",
                operation_id,
                "--timeout-seconds",
                str(max(1, int(deadline - time.monotonic()))),
                "--poll-interval-ms",
                "500",
            ),
            max(2, int(deadline - time.monotonic()) + 1),
            "TARGET_AUTHORIZATION_FAILED",
        )
        emit({"schema_version": 1, "type": "phase", "phase": "target_authorize", "status": "succeeded"})
        source_result = wait_jsonl_result(source, source_events, deadline)
    finally:
        if source.poll() is None:
            source.kill()
            source.wait()

    if source_result.get("status") == "pending_target":
        waiter, waiter_events = start_jsonl([
            str(agent), "job", "wait", job_id, "--timeout", "5m", "--output", "jsonl"
        ])
        source_result = wait_jsonl_result(waiter, waiter_events, deadline)
    if source_result.get("status") != "succeeded":
        raise WorkflowError(
            "SYNC_NOT_SUCCEEDED",
            "The authoritative Sync Job did not succeed.",
            job_id=job_id,
            status=source_result.get("status"),
        )

    run_json(
        cua_command(cua_cli, "sessions", "delete", "--session-id", session_id, "--allow-empty"),
        30,
        "SESSION_CLEANUP_FAILED",
    )
    return {
        "schema_version": 1,
        "status": "succeeded",
        "device_id": device_id,
        "job_id": job_id,
        "sites": sites,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Sync exact browser sites to the configured development my-cua.")
    value.add_argument("--agent-path", required=True)
    value.add_argument(
        "--cua-cli",
        default=str(Path.home() / ".codex" / "skills" / "my-cua-dev" / "scripts" / "cua.py"),
    )
    value.add_argument("--timeout-seconds", type=int, default=420)
    value.add_argument("site", nargs="+")
    return value


def main() -> int:
    args = parser().parse_args()
    if args.timeout_seconds < 60:
        emit({"schema_version": 1, "type": "result", "status": "failed", "error": {"code": "TIMEOUT_INVALID"}})
        return 2
    try:
        result = run(args)
    except WorkflowError as exc:
        emit({
            "schema_version": 1,
            "type": "result",
            "status": "failed",
            "error": {"code": exc.code, "message": exc.message},
            "details": exc.details,
        })
        return 1
    emit({"schema_version": 1, "type": "result", **result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
