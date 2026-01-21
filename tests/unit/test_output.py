import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr

from automtu.output import OutputMode, emit_json, emit_single_number, Logger


class TestOutput(unittest.TestCase):
    def test_output_mode_validate_mutual_exclusive(self) -> None:
        mode = OutputMode(print_mtu="effective", print_json=True)
        self.assertIsNotNone(mode.validate())

        mode_ok = OutputMode(print_mtu=None, print_json=True)
        self.assertIsNone(mode_ok.validate())

    def test_logger_routes_to_stderr_in_machine_mode(self) -> None:
        log = Logger(machine_mode=True).log

        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            log("[automtu] hello")

        self.assertEqual(out.getvalue(), "")
        self.assertIn("hello", err.getvalue())

    def test_emit_single_number_effective(self) -> None:
        mode = OutputMode(print_mtu="effective", print_json=False)

        out = io.StringIO()
        with redirect_stdout(out):
            emitted = emit_single_number(
                mode, base_mtu=1500, effective_mtu=1452, wg_mtu=1372
            )

        self.assertTrue(emitted)
        self.assertEqual(out.getvalue().strip(), "1452")

    def test_emit_json_is_valid_and_contains_expected_fields(self) -> None:
        mode = OutputMode(print_mtu=None, print_json=True)

        out = io.StringIO()
        with redirect_stdout(out):
            emitted = emit_json(
                mode,
                egress_iface="eth0",
                base_mtu=1500,
                effective_mtu=1452,
                egress_forced_mtu=None,
                egress_applied=False,
                pmtu_targets=["1.1.1.1", "8.8.8.8"],
                pmtu_auto_targets_added=[],
                pmtu_policy="min",
                pmtu_chosen=1452,
                pmtu_results={"1.1.1.1": 1452, "8.8.8.8": None},
                wg_iface="wg0",
                wg_mtu=1372,
                wg_overhead=80,
                wg_min=1280,
                wg_set_mtu=None,
                wg_clamped=False,
                wg_present=True,
                wg_active=False,
                wg_applied=False,
                dry_run=True,
            )

        self.assertTrue(emitted)

        payload = json.loads(out.getvalue())
        self.assertEqual(payload["egress"]["iface"], "eth0")
        self.assertEqual(payload["egress"]["base_mtu"], 1500)
        self.assertEqual(payload["egress"]["effective_mtu"], 1452)

        self.assertEqual(payload["pmtu"]["policy"], "min")
        self.assertEqual(payload["pmtu"]["chosen"], 1452)
        self.assertEqual(payload["pmtu"]["results"]["1.1.1.1"], 1452)
        self.assertIsNone(payload["pmtu"]["results"]["8.8.8.8"])

        self.assertEqual(payload["wg"]["iface"], "wg0")
        self.assertEqual(payload["wg"]["mtu"], 1372)
        self.assertTrue(payload["dry_run"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
