from __future__ import annotations

import argparse
import os


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="automtu",
        description="Probe Path MTU and compute/apply MTU for egress and/or WireGuard.",
    )

    ap.add_argument(
        "--egress-if", help="Explicit egress interface (auto-detected if omitted)."
    )
    ap.add_argument(
        "--prefer-wg-egress",
        action="store_true",
        help="Allow wg* as egress and prefer it if default route uses wg (default: off).",
    )

    ap.add_argument(
        "--pmtu-target",
        action="append",
        help="Target hostname/IP to probe PMTU. Repeatable or comma-separated.",
    )
    ap.add_argument(
        "--pmtu-timeout",
        type=float,
        default=1.0,
        help="Ping timeout seconds (default: 1.0).",
    )
    ap.add_argument(
        "--pmtu-min-payload",
        type=int,
        default=1200,
        help="PMTU lower payload bound (default: 1200).",
    )
    ap.add_argument(
        "--pmtu-max-payload",
        type=int,
        default=1472,
        help="PMTU upper payload bound (default: 1472).",
    )
    ap.add_argument(
        "--pmtu-policy",
        choices=["min", "median", "max"],
        default="min",
        help="Aggregate PMTU across targets (default: min).",
    )

    ap.add_argument(
        "--apply-egress-mtu",
        action="store_true",
        help="Apply effective MTU to egress interface.",
    )
    ap.add_argument(
        "--apply-wg-mtu", action="store_true", help="Apply MTU to WireGuard interface."
    )

    ap.add_argument(
        "--wg-if",
        default=os.environ.get("WG_IF", "wg0"),
        help="WireGuard interface (default: wg0).",
    )
    ap.add_argument(
        "--wg-overhead",
        type=int,
        default=int(os.environ.get("WG_OVERHEAD", "80")),
        help="WG overhead.",
    )
    ap.add_argument(
        "--wg-min",
        type=int,
        default=int(os.environ.get("WG_MIN", "1280")),
        help="Minimum WG MTU.",
    )
    ap.add_argument(
        "--auto-pmtu-from-wg",
        action="store_true",
        help="Add WG peer endpoints as PMTU targets.",
    )
    ap.add_argument("--set-wg-mtu", type=int, help="Force MTU for WireGuard interface.")

    ap.add_argument(
        "--force-egress-mtu",
        type=int,
        help="Force MTU on the egress interface before computing.",
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="Show actions without applying changes."
    )

    # --- Persistence ---
    ap.add_argument(
        "--persist",
        choices=["systemd"],
        help="Persist MTU configuration across reboots (currently supported: systemd).",
    )
    ap.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall persistence backend (requires --persist).",
    )

    # --- Machine-readable output modes ---
    ap.add_argument(
        "--print-mtu",
        choices=["egress", "effective", "wg"],
        help="Print only the selected MTU value as a number (stdout) for automation (e.g. Ansible).",
    )
    ap.add_argument(
        "--print-json",
        action="store_true",
        help="Print a JSON object with computed values (stdout) for automation.",
    )

    return ap
