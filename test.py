import io
import sys
import unittest
from unittest.mock import patch, call
from contextlib import redirect_stdout

# Import the script as a module
import main as automtu


class TestWgMtuAuto(unittest.TestCase):

    @patch("main.set_mtu")
    @patch("main.read_mtu", return_value=1500)
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0"])
    @patch("main.require_root", return_value=None)
    def test_no_pmtu_uses_egress_minus_overhead(
        self, _req_root, _get_def, _exists, _read_mtu, mock_set_mtu
    ):
        """
        Without PMTU probing, wg MTU should be base_mtu - overhead (clamped by min).
        With base=1500, overhead=80 ⇒ wg_mtu=1420.
        """
        argv = ["main.py", "--dry-run"]
        with patch.object(sys, "argv", argv):
            buf = io.StringIO()
            with redirect_stdout(buf):
                automtu.main()

        out = buf.getvalue()
        self.assertIn("Detected egress interface: eth0", out)
        self.assertIn("Egress base MTU: 1500", out)
        self.assertIn("Computed wg0 MTU: 1420", out)

        # dry-run still calls set_mtu (but prints DRY-RUN); ensure it targeted wg0 with 1420
        mock_set_mtu.assert_any_call("wg0", 1420, True)

    @patch("main.set_mtu")
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0"])
    @patch("main.require_root", return_value=None)
    def test_force_egress_mtu_and_pmtu_multiple_targets_min_policy(
        self, _req_root, _get_def, _exists, mock_set_mtu
    ):
        """
        base_mtu forced=1452; PMTU results: 1452, 1420 -> policy=min => 1420 chosen.
        effective=min(1452,1420)=1420; wg_mtu=1420-80=1340
        """
        with patch("main.read_mtu", return_value=9999):  # should be ignored because we force
            with patch("main.probe_pmtu", side_effect=[1452, 1420]):
                argv = [
                    "main.py",
                    "--dry-run",
                    "--force-egress-mtu", "1452",
                    "--pmtu-target", "t1",
                    "--pmtu-target", "t2",
                    "--pmtu-policy", "min",
                ]
                with patch.object(sys, "argv", argv):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        automtu.main()

        out = buf.getvalue()
        self.assertIn("Forcing egress MTU 1452 on eth0", out)
        self.assertIn("Probing Path MTU for: t1, t2 (policy=min)", out)
        self.assertIn("Selected Path MTU (policy=min): 1420", out)
        self.assertIn("Computed wg0 MTU: 1340", out)
        mock_set_mtu.assert_any_call("wg0", 1340, True)

    @patch("main.set_mtu")
    @patch("main.read_mtu", return_value=1500)
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0"])
    @patch("main.require_root", return_value=None)
    def test_pmtu_policy_median(
        self, _req_root, _get_def, _exists, _read_mtu, mock_set_mtu
    ):
        """
        base=1500; PMTUs: 1500, 1452, 1472 -> median=1472.
        effective=min(1500,1472)=1472; wg_mtu=1472-80=1392
        """
        with patch("main.probe_pmtu", side_effect=[1500, 1452, 1472]):
            argv = [
                "main.py",
                "--dry-run",
                "--pmtu-target", "a",
                "--pmtu-target", "b",
                "--pmtu-target", "c",
                "--pmtu-policy", "median",
            ]
            with patch.object(sys, "argv", argv):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    automtu.main()

        out = buf.getvalue()
        self.assertIn("Probing Path MTU for: a, b, c (policy=median)", out)
        self.assertIn("Selected Path MTU (policy=median): 1472", out)
        self.assertIn("Computed wg0 MTU: 1392", out)
        mock_set_mtu.assert_any_call("wg0", 1392, True)

    @patch("main.set_mtu")
    @patch("main.read_mtu", return_value=1500)
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0"])
    @patch("main.require_root", return_value=None)
    def test_pmtu_all_fail_falls_back_to_base(
        self, _req_root, _get_def, _exists, _read_mtu, mock_set_mtu
    ):
        """
        If all PMTU probes fail, fall back to base MTU (1500) => wg_mtu=1420.
        """
        with patch("main.probe_pmtu", side_effect=[None, None]):
            argv = [
                "main.py",
                "--dry-run",
                "--pmtu-target", "bad1",
                "--pmtu-target", "bad2",
            ]
            with patch.object(sys, "argv", argv):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    automtu.main()

        out = buf.getvalue()
        self.assertIn("WARNING: All PMTU probes failed. Falling back to egress MTU.", out)
        self.assertIn("Computed wg0 MTU: 1420", out)
        mock_set_mtu.assert_any_call("wg0", 1420, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
