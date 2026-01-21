import unittest
from unittest.mock import patch

import automtu.net as net


class TestNet(unittest.TestCase):
    def test_detect_egress_iface_parses_default_route_and_ignores_vpn(self) -> None:
        # Simulate: ip route show default -> dev wg0 first, then eth0
        ip4_default = (
            "default via 10.0.0.1 dev wg0 proto dhcp src 10.0.0.2 metric 100\n"
        )
        ip6_default = "default via fe80::1 dev eth0 proto ra metric 100\n"

        def fake_run(cmd: list[str]) -> str:
            if cmd[:4] == ["ip", "-4", "route", "show"]:
                return ip4_default.strip()
            if cmd[:4] == ["ip", "-6", "route", "show"]:
                return ip6_default.strip()
            return ""

        with (
            patch("automtu.net._run", side_effect=fake_run),
            patch("automtu.net.iface_exists", return_value=True),
        ):
            # ignore_vpn=True -> should skip wg0 and pick eth0
            self.assertEqual(net.detect_egress_iface(ignore_vpn=True), "eth0")

            # ignore_vpn=False -> first seen is wg0
            self.assertEqual(net.detect_egress_iface(ignore_vpn=False), "wg0")

    def test_default_route_uses_iface_true_false(self) -> None:
        ip4_default = "default via 10.0.0.1 dev eth0\n"
        ip6_default = ""

        def fake_run(cmd: list[str]) -> str:
            if cmd[:4] == ["ip", "-4", "route", "show"]:
                return ip4_default.strip()
            if cmd[:4] == ["ip", "-6", "route", "show"]:
                return ip6_default.strip()
            return ""

        with patch("automtu.net._run", side_effect=fake_run):
            self.assertTrue(net.default_route_uses_iface("eth0"))
            self.assertFalse(net.default_route_uses_iface("wg0"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
