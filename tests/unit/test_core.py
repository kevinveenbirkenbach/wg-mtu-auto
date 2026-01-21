import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from automtu.core import run_automtu


class TestCore(unittest.TestCase):
    def test_run_automtu_happy_path_all_mocked(self) -> None:
        args = SimpleNamespace(
            dry_run=True,
            egress_if=None,
            prefer_wg_egress=False,
            force_egress_mtu=None,
            pmtu_target=["1.1.1.1,8.8.8.8"],
            auto_pmtu_from_wg=False,
            pmtu_min_payload=1200,
            pmtu_max_payload=1472,
            pmtu_timeout=1.0,
            pmtu_policy="min",
            apply_egress_mtu=True,
            apply_wg_mtu=True,
            wg_if="wg0",
            wg_overhead=80,
            wg_min=1280,
            set_wg_mtu=None,
        )

        # PMTU probes: 1452 and 1500 -> min policy => 1452, effective=min(base(1500),1452)=1452
        # wg_mtu = 1452-80 = 1372
        with (
            patch("automtu.core.require_root", return_value=None),
            patch("automtu.core.detect_egress_iface", return_value="eth0"),
            patch("automtu.core.iface_exists", return_value=True),
            patch("automtu.core.read_iface_mtu", return_value=1500),
            patch("automtu.core.probe_pmtu", side_effect=[1452, 1500]),
            patch("automtu.core.set_iface_mtu") as mock_set,
            patch("automtu.core.wg_is_active", return_value=False),
            patch("automtu.core.wg_peer_endpoints", return_value=[]),
            patch("automtu.core.default_route_uses_iface", return_value=False),
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_automtu(args)

        self.assertEqual(rc, 0)
        s = buf.getvalue()
        self.assertIn("Detected egress interface: eth0", s)
        self.assertIn("Egress base MTU: 1500", s)
        self.assertIn("Selected Path MTU (policy=min): 1452", s)
        self.assertIn("Computed wg0 MTU: 1372", s)

        # apply egress and wg are both true -> two calls in order
        mock_set.assert_any_call("eth0", 1452, True)
        mock_set.assert_any_call("wg0", 1372, True)

    def test_run_automtu_does_not_apply_wg_without_flag(self) -> None:
        args = SimpleNamespace(
            dry_run=True,
            egress_if="eth0",
            prefer_wg_egress=False,
            force_egress_mtu=None,
            pmtu_target=None,
            auto_pmtu_from_wg=False,
            pmtu_min_payload=1200,
            pmtu_max_payload=1472,
            pmtu_timeout=1.0,
            pmtu_policy="min",
            apply_egress_mtu=False,
            apply_wg_mtu=False,
            wg_if="wg0",
            wg_overhead=80,
            wg_min=1280,
            set_wg_mtu=None,
        )

        with (
            patch("automtu.core.require_root", return_value=None),
            patch("automtu.core.iface_exists", return_value=True),
            patch("automtu.core.read_iface_mtu", return_value=1500),
            patch("automtu.core.set_iface_mtu") as mock_set,
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_automtu(args)

        self.assertEqual(rc, 0)
        mock_set.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
