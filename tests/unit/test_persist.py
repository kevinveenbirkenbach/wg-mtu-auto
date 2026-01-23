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
        argv = ["automtu", "--persist", "docker", "--uninstall", "--apply-wg-mtu"]
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

    def test_persist_systemd_adds_docker_ordering_if_apply_docker_mtu_present(
        self,
    ) -> None:
        argv = ["automtu", "--apply-docker-mtu", "--persist", "systemd"]

        with (
            patch("automtu.persist.shutil.which", return_value="/usr/bin/automtu"),
            patch("automtu.persist._SYSTEMD_UNIT_PATH", Path("/tmp/automtu.service")),
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                persist.persist_systemd(argv, dry=True)

        s = out.getvalue()
        self.assertIn("After=network-online.target docker.service", s)
        self.assertIn("Wants=network-online.target docker.service", s)

    def test_persist_docker_dry_run_prints_unit_with_docker_ordering(self) -> None:
        argv = ["automtu", "--dry-run", "--persist", "docker"]

        with (
            patch("automtu.persist.shutil.which", return_value="/usr/bin/automtu"),
            patch(
                "automtu.persist._DOCKER_SYSTEMD_UNIT_PATH",
                Path("/tmp/automtu-docker.service"),
            ),
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                persist.persist_docker(argv, dry=True)

        s = out.getvalue()
        self.assertIn("DRY-RUN", s)
        self.assertIn("After=network-online.target docker.service", s)
        self.assertIn("Wants=network-online.target docker.service", s)
        self.assertIn("ExecStart=/usr/bin/automtu --dry-run", s)

    def test_uninstall_systemd_dry_run_prints_actions(self) -> None:
        with patch("automtu.persist._SYSTEMD_UNIT_PATH", Path("/tmp/automtu.service")):
            out = io.StringIO()
            with redirect_stdout(out):
                persist.uninstall_systemd(dry=True)

        s = out.getvalue()
        self.assertIn("DRY-RUN", s)
        self.assertIn("systemctl disable", s)

    def test_uninstall_docker_dry_run_prints_actions(self) -> None:
        with patch(
            "automtu.persist._DOCKER_SYSTEMD_UNIT_PATH",
            Path("/tmp/automtu-docker.service"),
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                persist.uninstall_docker(dry=True)

        s = out.getvalue()
        self.assertIn("DRY-RUN", s)
        self.assertIn("automtu-docker.service", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
