import unittest
from unittest.mock import patch

import automtu.pmtu as pmtu


class TestPmtu(unittest.TestCase):
    def test_probe_pmtu_binary_search_and_hdr_addition(self) -> None:
        # Mock _is_ipv6 -> IPv4, so hdr = 28.
        # Mock _ping_ok so that payload <= 1400 works, >1400 fails.
        def fake_ping_ok(payload: int, target: str, timeout_s: float) -> bool:
            return payload <= 1400

        with (
            patch("automtu.pmtu._is_ipv6", return_value=False),
            patch("automtu.pmtu._ping_ok", side_effect=fake_ping_ok),
        ):
            # lo=1200 works, hi=1472 partially works -> best = 1400 -> mtu = 1400+28 = 1428
            mtu = pmtu.probe_pmtu(
                "1.1.1.1", lo_payload=1200, hi_payload=1472, timeout=1.0
            )
            self.assertEqual(mtu, 1428)

    def test_probe_pmtu_returns_none_if_even_floor_fails(self) -> None:
        with (
            patch("automtu.pmtu._is_ipv6", return_value=False),
            patch("automtu.pmtu._ping_ok", return_value=False),
        ):
            mtu = pmtu.probe_pmtu(
                "1.1.1.1", lo_payload=1200, hi_payload=1472, timeout=1.0
            )
            self.assertIsNone(mtu)


if __name__ == "__main__":
    unittest.main(verbosity=2)
