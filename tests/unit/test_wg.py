import unittest
from unittest.mock import patch

import automtu.wg as wg


class TestWg(unittest.TestCase):
    def test_wg_peer_endpoints_from_wg_show(self) -> None:
        # wg show wg0 endpoints output
        out = "abcde12345\t46.4.224.77:51820\nfffff00000\t[2a01:db8::1]:51820\n"

        with (
            patch(
                "automtu.wg._run",
                side_effect=lambda cmd: out if cmd[:3] == ["wg", "show", "wg0"] else "",
            ),
            patch("automtu.wg.iface_exists", return_value=True),
            patch("automtu.wg._rc", return_value=0),
        ):
            eps = wg.wg_peer_endpoints("wg0")

        self.assertEqual(eps, ["46.4.224.77", "2a01:db8::1"])

    def test_wg_peer_endpoints_fallback_showconf(self) -> None:
        show_endpoints_empty = ""
        showconf = (
            "[Interface]\n"
            "PrivateKey = x\n"
            "[Peer]\n"
            "Endpoint = 46.4.224.77:51820\n"
            "[Peer]\n"
            "Endpoint = [2a01:db8::1]:51820\n"
        )

        def fake_run(cmd: list[str]) -> str:
            if cmd == ["wg", "show", "wg0", "endpoints"]:
                return show_endpoints_empty
            if cmd == ["wg", "showconf", "wg0"]:
                return showconf
            return ""

        with patch("automtu.wg._run", side_effect=fake_run):
            eps = wg.wg_peer_endpoints("wg0")

        self.assertEqual(eps, ["46.4.224.77", "2a01:db8::1"])

    def test_wg_is_active_uses_iface_exists_and_wg_show_rc(self) -> None:
        with (
            patch("automtu.wg.iface_exists", return_value=True),
            patch("automtu.wg._rc", return_value=0),
        ):
            self.assertTrue(wg.wg_is_active("wg0"))
        with patch("automtu.wg.iface_exists", return_value=False):
            self.assertFalse(wg.wg_is_active("wg0"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
