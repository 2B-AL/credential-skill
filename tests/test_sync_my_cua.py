import argparse
import importlib.util
import queue
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("sync_my_cua", ROOT / "scripts" / "sync-my-cua.py")
sync_my_cua = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(sync_my_cua)


class FakeProcess:
    def __init__(self):
        self.stopped = False

    def poll(self):
        return 0 if self.stopped else None

    def kill(self):
        self.stopped = True

    def wait(self, timeout=None):
        self.stopped = True
        return 0


class SyncMyCuaTests(unittest.TestCase):
    def test_authoritative_wait_finishes_before_adapter_deadline(self):
        captured = []
        process = FakeProcess()
        with mock.patch.object(sync_my_cua, "start_jsonl", side_effect=lambda command: (captured.append(command) or process, queue.Queue())), \
                mock.patch.object(sync_my_cua, "wait_jsonl_result", return_value={"status": "pending_target"}):
            result = sync_my_cua.wait_authoritative_job(Path("/agent"), "job-1", time.monotonic() + 10)
        self.assertEqual(result["status"], "pending_target")
        timeout = captured[0][captured[0].index("--timeout") + 1]
        self.assertLessEqual(int(timeout.removesuffix("s")), 8)
        self.assertTrue(process.stopped)

    def test_target_health_drops_unbounded_diagnostic_fields(self):
        response = {
            "data": {
                "healthy": True,
                "device_ready": True,
                "browser_ready": False,
                "warning_count": 1,
                "issue_count": 2,
                "checks": ["must not escape"],
                "secret": "must not escape",
            }
        }
        with mock.patch.object(sync_my_cua, "run_json", return_value=response):
            health = sync_my_cua.target_health(Path("/cua.py"), "session-1")
        self.assertEqual(health, {
            "available": True,
            "healthy": True,
            "device_ready": True,
            "browser_ready": False,
            "warning_count": 1,
            "issue_count": 2,
        })

    def test_failed_workflow_still_deletes_exact_pair_session(self):
        commands = []
        process = FakeProcess()
        events = queue.Queue()
        events.put('{"type":"phase","phase":"create_sync_job","status":"succeeded","details":{"job":{"id":"job-1"}}}\n')

        def run_json(command, _timeout, _code):
            commands.append(command)
            if command[0] == "/agent" and command[1:3] == ["browser", "validate"]:
                return {"status": "succeeded"}
            if "pair-auto" in command:
                return {"data": {"device_id": "device-1", "session_id": "session-1", "browser_connected": True}}
            if "authorize-begin" in command:
                return {"data": {"operation": {"operation_id": "operation-1"}}}
            if "health" in command:
                return {"data": {"healthy": False}}
            return {"ok": True}

        args = argparse.Namespace(agent_path="/agent", cua_cli="/cua.py", site=["github"], timeout_seconds=120)
        with mock.patch.object(sync_my_cua, "safe_executable", side_effect=lambda value, *_args, **_kwargs: Path(value)), \
                mock.patch.object(sync_my_cua, "run_json", side_effect=run_json), \
                mock.patch.object(sync_my_cua, "ensure_target_network", return_value={"data": {"network": {"mode": "direct"}}}), \
                mock.patch.object(sync_my_cua, "start_jsonl", return_value=(process, events)), \
                mock.patch.object(sync_my_cua, "wait_jsonl_result", return_value={"status": "failed"}), \
                mock.patch.object(sync_my_cua, "emit"):
            with self.assertRaises(sync_my_cua.WorkflowError):
                sync_my_cua.run(args)

        cleanup = [command for command in commands if "sessions" in command and "delete" in command]
        self.assertEqual(len(cleanup), 1)
        self.assertIn("session-1", cleanup[0])
        self.assertTrue(process.stopped)


if __name__ == "__main__":
    unittest.main()
