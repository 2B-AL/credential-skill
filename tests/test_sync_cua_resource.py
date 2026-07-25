import argparse
import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sync_cua_resource", ROOT / "scripts" / "sync-cua-resource.py")
sync_resource = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(sync_resource)


class SyncCuaResourceTests(unittest.TestCase):
    def args(self):
        return argparse.Namespace(
            agent_path="/agent",
            target_adapter="/adapter.py",
            desktop_id="desk-1",
            timeout_seconds=120,
            resource="env",
            name=["OPENAI_API_KEY"],
        )

    def test_delivery_uses_exact_device_and_finishes_workflow(self):
        calls = []

        def adapter(_path, *arguments, **_kwargs):
            calls.append(arguments)
            if arguments[0] == "begin":
                return {"workflow_id": "workflow-1", "device_id": "device-1", "device_ready": True}
            return {"finished": True}

        with (
            mock.patch.object(sync_resource, "safe_file", side_effect=lambda value, *_args, **_kwargs: Path(value)),
            mock.patch.object(sync_resource, "adapter", side_effect=adapter),
            mock.patch.object(sync_resource.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run,
        ):
            result = sync_resource.run(self.args())

        self.assertEqual(result["device_id"], "device-1")
        self.assertEqual(run.call_args.args[0], [
            "/agent", "env", "sync", "--to", "device-1", "OPENAI_API_KEY",
        ])
        self.assertEqual(calls[-1], ("finish", "--workflow-id", "workflow-1"))

    def test_cleanup_failure_does_not_mask_delivery_failure(self):
        def adapter(_path, *arguments, **_kwargs):
            if arguments[0] == "begin":
                return {"workflow_id": "workflow-1", "device_id": "device-1", "device_ready": True}
            raise sync_resource.ResourceError("WORKFLOW_EXPIRED", "already gone")

        with (
            mock.patch.object(sync_resource, "safe_file", side_effect=lambda value, *_args, **_kwargs: Path(value)),
            mock.patch.object(sync_resource, "adapter", side_effect=adapter),
            mock.patch.object(sync_resource.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "")),
        ):
            with self.assertRaises(sync_resource.ResourceError) as raised:
                sync_resource.run(self.args())
        self.assertEqual(raised.exception.code, "SOURCE_SYNC_FAILED")

    def test_secret_and_credential_set_keep_hidden_input_terminal(self):
        for resource in ("secret", "credential-set"):
            args = self.args()
            args.resource = resource
            if resource == "credential-set":
                args.set_type = "volcengine_aksk"
                args.set_name = "default"
                del args.name
            with (
                mock.patch.object(sync_resource, "safe_file", side_effect=lambda value, *_args, **_kwargs: Path(value)),
                mock.patch.object(sync_resource, "adapter", side_effect=[
                    {"workflow_id": "workflow-1", "device_id": "device-1", "device_ready": True},
                    {"finished": True},
                ]),
                mock.patch.object(sync_resource.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run,
            ):
                sync_resource.run(args)
            self.assertIsNone(run.call_args.kwargs["stdin"])
            self.assertIsNone(run.call_args.kwargs["stderr"])


if __name__ == "__main__":
    unittest.main()
