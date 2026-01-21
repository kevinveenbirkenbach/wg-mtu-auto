import unittest

from automtu.cli import build_parser


class TestCli(unittest.TestCase):
    def test_build_parser_accepts_known_args(self) -> None:
        p = build_parser()

        # Parse only; no side effects.
        args = p.parse_args(
            [
                "--egress-if",
                "eth0",
                "--prefer-wg-egress",
                "--pmtu-target",
                "1.1.1.1,8.8.8.8",
                "--pmtu-timeout",
                "2.0",
                "--pmtu-min-payload",
                "1200",
                "--pmtu-max-payload",
                "1472",
                "--pmtu-policy",
                "median",
                "--apply-egress-mtu",
                "--apply-wg-mtu",
                "--wg-if",
                "wg0",
                "--wg-overhead",
                "80",
                "--wg-min",
                "1280",
                "--auto-pmtu-from-wg",
                "--set-wg-mtu",
                "1372",
                "--force-egress-mtu",
                "1452",
                "--dry-run",
            ]
        )

        self.assertEqual(args.egress_if, "eth0")
        self.assertTrue(args.prefer_wg_egress)
        self.assertEqual(args.pmtu_target, ["1.1.1.1,8.8.8.8"])
        self.assertEqual(args.pmtu_timeout, 2.0)
        self.assertEqual(args.pmtu_min_payload, 1200)
        self.assertEqual(args.pmtu_max_payload, 1472)
        self.assertEqual(args.pmtu_policy, "median")
        self.assertTrue(args.apply_egress_mtu)
        self.assertTrue(args.apply_wg_mtu)
        self.assertEqual(args.wg_if, "wg0")
        self.assertEqual(args.wg_overhead, 80)
        self.assertEqual(args.wg_min, 1280)
        self.assertTrue(args.auto_pmtu_from_wg)
        self.assertEqual(args.set_wg_mtu, 1372)
        self.assertEqual(args.force_egress_mtu, 1452)
        self.assertTrue(args.dry_run)


if __name__ == "__main__":
    unittest.main(verbosity=2)
