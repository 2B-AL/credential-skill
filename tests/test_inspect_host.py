import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from typing import Optional


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "inspect-host.py"
SPEC = importlib.util.spec_from_file_location("credential_inspect_host", MODULE_PATH)
assert SPEC and SPEC.loader
inspect_host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspect_host)


class RunningLinuxChromiumTest(unittest.TestCase):
    def test_runtime_hints_are_bounded(self) -> None:
        previous_kind = os.environ.get("CREDENTIAL_AGENT_RUNTIME_KIND")
        previous_manager = os.environ.get("CREDENTIAL_AGENT_DAEMON_MANAGER")
        self.addCleanup(self._restore_env, "CREDENTIAL_AGENT_RUNTIME_KIND", previous_kind)
        self.addCleanup(self._restore_env, "CREDENTIAL_AGENT_DAEMON_MANAGER", previous_manager)
        os.environ["CREDENTIAL_AGENT_RUNTIME_KIND"] = "aio_sandbox"
        os.environ["CREDENTIAL_AGENT_DAEMON_MANAGER"] = "external"
        self.assertEqual(
            inspect_host.runtime_hints(),
            {"kind": "aio_sandbox", "daemon_manager_hint": "external"},
        )
        os.environ["CREDENTIAL_AGENT_RUNTIME_KIND"] = "bad/value"
        os.environ["CREDENTIAL_AGENT_DAEMON_MANAGER"] = "unknown"
        self.assertEqual(
            inspect_host.runtime_hints(),
            {"kind": "desktop", "daemon_manager_hint": None},
        )

    @staticmethod
    def _restore_env(name: str, value: Optional[str]) -> None:
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value

    def test_finds_custom_user_data_dir_without_exposing_other_args(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proc = root / "proc"
            process = proc / "100"
            process.mkdir(parents=True)
            user_data_dir = root / "browser"
            user_data_dir.mkdir()
            (process / "cmdline").write_bytes(
                b"/opt/browser/chrome\0"
                + f"--user-data-dir={user_data_dir}".encode()
                + b"\0--remote-debugging-port=9222\0--secret-looking-arg=not-output\0"
            )

            executable, user_data_dirs = inspect_host.running_linux_chromium(
                proc=proc,
                current_uid=os.geteuid(),
                system="linux",
                ps_output="",
            )

            self.assertEqual(executable, "/opt/browser/chrome")
            self.assertEqual(user_data_dirs, [str(user_data_dir.resolve())])

    def test_ignores_renderer_and_relative_user_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            proc = Path(temporary) / "proc"
            renderer = proc / "101"
            renderer.mkdir(parents=True)
            (renderer / "cmdline").write_bytes(
                b"/opt/browser/chrome\0--type=renderer\0--user-data-dir=/tmp/browser\0"
            )
            main = proc / "102"
            main.mkdir()
            (main / "cmdline").write_bytes(
                b"/opt/browser/chrome\0--user-data-dir=relative/browser\0"
            )
            zombie = proc / "103"
            zombie.mkdir()
            (zombie / "cmdline").write_bytes(b"")

            executable, user_data_dirs = inspect_host.running_linux_chromium(
                proc=proc,
                current_uid=os.geteuid(),
                system="linux",
                ps_output="",
            )

            self.assertEqual(executable, "/opt/browser/chrome")
            self.assertEqual(user_data_dirs, [])

    def test_finds_custom_user_data_dir_in_chromium_rewritten_cmdline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proc = root / "proc"
            process = proc / "104"
            process.mkdir(parents=True)
            user_data_dir = root / "browser"
            user_data_dir.mkdir()
            (process / "cmdline").write_bytes(
                f"/opt/browser/chrome --user-data-dir={user_data_dir} --remote-debugging-port=9222".encode()
            )

            executable, user_data_dirs = inspect_host.running_linux_chromium(
                proc=proc,
                current_uid=os.geteuid(),
                system="linux",
                ps_output="",
            )

            self.assertEqual(executable, "/opt/browser/chrome")
            self.assertEqual(user_data_dirs, [str(user_data_dir.resolve())])

    def test_uses_ps_fallback_when_proc_is_restricted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proc = root / "proc"
            proc.mkdir()
            user_data_dir = root / "browser"
            user_data_dir.mkdir()
            ps_output = "\n".join(
                [
                    f"/opt/browser/chrome --user-data-dir={user_data_dir} --remote-debugging-port=9222",
                    f"/opt/browser/chrome --type=renderer --user-data-dir={user_data_dir}",
                ]
            )

            executable, user_data_dirs = inspect_host.running_linux_chromium(
                proc=proc,
                current_uid=os.geteuid(),
                system="linux",
                ps_output=ps_output,
            )

            self.assertEqual(executable, "/opt/browser/chrome")
            self.assertEqual(user_data_dirs, [str(user_data_dir.resolve())])


if __name__ == "__main__":
    unittest.main()
