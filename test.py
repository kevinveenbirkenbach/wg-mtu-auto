import io
import sys
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

# Import the script as a module
import main as automtu


class TestWgMtuAutoExtended(unittest.TestCase):
    # ---------- Baseline behavior (unchanged) ----------

    @patch("main.set_mtu")
    @patch("main.read_mtu", return_value=1500)
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0"])
    @patch("main.require_root", return_value=None)
    def test_no_pmtu_uses_egress_minus_overhead(
        self, _req_root, mock_get_def, _exists, _read_mtu, mock_set_mtu
    ):
        argv = ["main.py", "--dry-run"]
        with patch.object(sys, "argv", argv):
            buf = io.StringIO()
            with redirect_stdout(buf):
                automtu.main()

        out = buf.getvalue()
        self.assertIn("Detected egress interface: eth0", out)
        self.assertIn("Egress base MTU: 1500", out)
        self.assertIn("Computed wg0 MTU: 1420", out)
        mock_set_mtu.assert_any_call("wg0", 1420, True)
        # get_default_ifaces should be called with ignore_vpn=True by default
        mock_get_def.assert_called_with(ignore_vpn=True)

    # ---------- prefer-wg-egress selection ----------

    @patch("main.wg_default_is_active", return_value=True)
    @patch("main.wg_is_active", return_value=True)
    @patch("main.set_mtu")
    @patch("main.read_mtu", return_value=1420)
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0", "wg0"])
    @patch("main.require_root", return_value=None)
    def test_prefer_wg_egress_picks_wg0_when_default_route_via_wg(
        self, _req_root, mock_get_def, _exists, _read_mtu, _set_mtu, _wg_is_active, _wg_def_active
    ):
        argv = ["main.py", "--dry-run", "--prefer-wg-egress", "--wg-if", "wg0"]
        with patch.object(sys, "argv", argv):
            buf = io.StringIO()
            with redirect_stdout(buf):
                automtu.main()

        out = buf.getvalue()
        # When prefer-wg is set AND wg default route is active, wg0 should be chosen as egress
        self.assertIn("Detected egress interface: wg0", out)
        self.assertIn("Using WireGuard interface wg0 as egress basis.", out)
        # Computed MTU: base 1420 - 80 = 1340 (clamped by min=1280)
        self.assertIn("Computed wg0 MTU: 1340", out)
        # get_default_ifaces should be called with ignore_vpn=False (because prefer-wg)
        mock_get_def.assert_called_with(ignore_vpn=False)

    # ---------- auto-pmtu-from-wg adds peer endpoints ----------

    @patch("main.wg_peer_endpoints", return_value=["46.4.224.77", "2a01:db8::1"])
    @patch("main.wg_is_active", return_value=True)
    @patch("main.probe_pmtu", side_effect=[1452, 1420])  # results for two peers
    @patch("main.set_mtu")
    @patch("main.read_mtu", return_value=1500)
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0"])
    @patch("main.require_root", return_value=None)
    def test_auto_pmtu_from_wg_adds_targets_and_uses_min_policy(
        self, _req_root, _get_def, _exists, _read_mtu, _set_mtu, _probe_pmtu, _wg_active, _wg_peers
    ):
        argv = ["main.py", "--dry-run", "--auto-pmtu-from-wg", "--wg-if", "wg0"]
        with patch.object(sys, "argv", argv):
            buf = io.StringIO()
            with redirect_stdout(buf):
                automtu.main()

        out = buf.getvalue()
        # Confirm WG peers were added
        self.assertIn("Auto-added WG peer endpoints as PMTU targets: 46.4.224.77, 2a01:db8::1", out)
        # The policy default is 'min', so chosen PMTU should be 1420
        self.assertIn("Selected Path MTU (policy=min): 1420", out)
        # Computed wg0 MTU: 1420 - 80 = 1340
        self.assertIn("Computed wg0 MTU: 1340", out)
        # Ensure probe was called twice (for both peers)
        self.assertEqual(_probe_pmtu.call_count, 2)

    # ---------- manual PMTU still works with prefer-wg-egress ----------

    @patch("main.wg_default_is_active", return_value=True)
    @patch("main.wg_is_active", return_value=True)
    @patch("main.probe_pmtu", side_effect=[1472, 1452, 1500])
    @patch("main.set_mtu")
    @patch("main.read_mtu", return_value=1500)
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0"])
    @patch("main.require_root", return_value=None)
    def test_prefer_wg_egress_with_manual_targets_and_median_policy(
        self, _req_root, _get_def, _exists, _read_mtu, _set_mtu, _probe_pmtu, _wg_is_active, _wg_def_active
    ):
        argv = [
            "main.py", "--dry-run",
            "--prefer-wg-egress", "--wg-if", "wg0",
            "--pmtu-target", "a", "--pmtu-target", "b", "--pmtu-target", "c",
            "--pmtu-policy", "median"
        ]
        with patch.object(sys, "argv", argv):
            buf = io.StringIO()
            with redirect_stdout(buf):
                automtu.main()

        out = buf.getvalue()
        # As default route via wg is active, wg0 should be used
        self.assertIn("Detected egress interface: wg0", out)
        # PMTU values: 1472, 1452, 1500 -> median = 1472
        self.assertIn("Selected Path MTU (policy=median): 1472", out)
        # Computed WG MTU: 1472 - 80 = 1392
        self.assertIn("Computed wg0 MTU: 1392", out)
        self.assertEqual(_probe_pmtu.call_count, 3)

    # ---------- PMTU all fail fallback ----------

    @patch("main.set_mtu")
    @patch("main.read_mtu", return_value=1500)
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0"])
    @patch("main.require_root", return_value=None)
    def test_pmtu_all_fail_falls_back_to_base(
        self, _req_root, _get_def, _exists, _read_mtu, mock_set_mtu
    ):
        with patch("main.probe_pmtu", side_effect=[None, None]):
            argv = ["main.py", "--dry-run", "--pmtu-target", "bad1", "--pmtu-target", "bad2"]
            with patch.object(sys, "argv", argv):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    automtu.main()

        out = buf.getvalue()
        self.assertIn("WARNING: All PMTU probes failed. Falling back to egress MTU.", out)
        self.assertIn("Computed wg0 MTU: 1420", out)  # 1500 - 80
        mock_set_mtu.assert_any_call("wg0", 1420, True)

    # ---------- NEW: --set-wg-mtu overrides computed ----------

    @patch("main.set_mtu")
    @patch("main.read_mtu", return_value=1500)
    @patch("main.exists_iface", return_value=True)
    @patch("main.get_default_ifaces", return_value=["eth0"])
    @patch("main.require_root", return_value=None)
    def test_force_set_wg_mtu_overrides_computed(
        self, _req_root, _get_def, _exists, _read_mtu, mock_set_mtu
    ):
        """
        --set-wg-mtu must override the computed value.
        Base=1500 -> computed 1420 (1500-80), but we force 1300.
        """
        argv = ["main.py", "--dry-run", "--set-wg-mtu", "1300"]
        with patch.object(sys, "argv", argv):
            buf = io.StringIO()
            with redirect_stdout(buf):
                automtu.main()

        out = buf.getvalue()
        # Computation is printed first
        self.assertIn("Computed wg0 MTU: 1420", out)
        # Then override message appears and applied value is 1300
        self.assertIn("Forcing WireGuard MTU (override): 1300", out)
        mock_set_mtu.assert_any_call("wg0", 1300, True)

        # also test clamping below wg-min
        argv2 = ["main.py", "--dry-run", "--set-wg-mtu", "1200"]  # below default wg_min=1280
        with patch.object(sys, "argv", argv2):
            out2 = io.StringIO()
            with redirect_stdout(out2):
                automtu.main()
        s = out2.getvalue()
        self.assertIn("[wg-mtu][WARN] --set-wg-mtu 1200 is below wg-min 1280; clamping to 1280.", s)
        self.assertIn("Forcing WireGuard MTU (override): 1280", s)
        mock_set_mtu.assert_any_call("wg0", 1280, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
