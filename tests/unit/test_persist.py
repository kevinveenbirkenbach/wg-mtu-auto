import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import automtu.persist as persist


class TestPersist(unittest.TestCase):
    def test_strip_persist_args_removes_flag_and_value(self) -> None:
        argv = ["automtu", "--apply-wg-mtu", "--persist", "systemd"]
        self.assertEqual(
            persist._strip_persist_args(argv),
            ["automtu", "--apply-wg-mtu"],
        )

    def test_strip_persist_args_removes_equals_form(self) -> None:
        argv = ["automtu", "--apply-wg-mtu", "--persist=systemd"]
        self.assertEqual(
            persist._strip_persist_args(argv),
            ["automtu", "--apply-wg-mtu"],
        )

    def test_strip_persist_args_removes_uninstall(self) -> None:
        argv = ["automtu", "--persist", "systemd", "--uninstall", "--apply-wg-mtu"]
        self.assertEqual(
            persist._strip_persist_args(argv),
            ["automtu", "--apply-wg-mtu"],
        )

    def test_persist_systemd_dry_run_prints_unit(self) -> None:
        argv = [
            "automtu",
            "--auto-pmtu-from-wg",
            "--apply-wg-mtu",
            "--persist",
            "systemd",
        ]

        with (
            patch("automtu.persist.shutil.which", return_value="/usr/bin/automtu"),
            patch("automtu.persist._SYSTEMD_UNIT_PATH", Path("/tmp/automtu.service")),
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                persist.persist_systemd(argv, dry=True)

        s = out.getvalue()
        self.assertIn("DRY-RUN", s)
        self.assertIn(
            "ExecStart=/usr/bin/automtu --auto-pmtu-from-wg --apply-wg-mtu", s
        )

    def test_uninstall_systemd_dry_run_prints_actions(self) -> None:
        with patch("automtu.persist._SYSTEMD_UNIT_PATH", Path("/tmp/automtu.service")):
            out = io.StringIO()
            with redirect_stdout(out):
                persist.uninstall_systemd(dry=True)

        s = out.getvalue()
        self.assertIn("DRY-RUN", s)
        self.assertIn("systemctl disable", s)

    def test_uninstall_systemd_runs_disable_and_removes_unit_when_present(self) -> None:
        fake_path = Path("/tmp/automtu.service")

        calls = []

        def fake_run(cmd, check=False):  # type: ignore[no-untyped-def]
            calls.append((tuple(cmd), bool(check)))

        with (
            patch("automtu.persist._SYSTEMD_UNIT_PATH", fake_path),
            patch("automtu.persist.subprocess.run", side_effect=fake_run),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "unlink", return_value=None),
        ):
            persist.uninstall_systemd(dry=False)

        # Must disable unit and reload daemon
        self.assertIn((("systemctl", "disable", "automtu.service"), True), calls)
        self.assertIn((("systemctl", "daemon-reload"), True), calls)

    def test_persist_systemd_writes_unit_and_enables(self) -> None:
        argv = ["automtu", "--apply-wg-mtu", "--persist", "systemd"]

        writes = {"text": None}
        calls = []

        def fake_write_text(self, txt, *args, **kwargs):  # type: ignore[no-untyped-def]
            writes["text"] = txt
            return len(txt)

        def fake_run(cmd, check=False):  # type: ignore[no-untyped-def]
            calls.append((tuple(cmd), bool(check)))

        with (
            patch("automtu.persist.shutil.which", return_value="/usr/bin/automtu"),
            patch("automtu.persist._SYSTEMD_UNIT_PATH", Path("/tmp/automtu.service")),
            patch.object(Path, "write_text", new=fake_write_text),
            patch("automtu.persist.subprocess.run", side_effect=fake_run),
        ):
            persist.persist_systemd(argv, dry=False)

        self.assertIsNotNone(writes["text"])
        self.assertIn("ExecStart=/usr/bin/automtu --apply-wg-mtu", writes["text"] or "")

        self.assertIn((("systemctl", "daemon-reload"), True), calls)
        self.assertIn((("systemctl", "enable", "automtu.service"), True), calls)


if __name__ == "__main__":
    unittest.main(verbosity=2)
