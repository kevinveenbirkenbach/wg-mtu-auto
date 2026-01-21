from __future__ import annotations

import statistics
import sys
from dataclasses import dataclass
from typing import Iterable, Optional

from .net import (
    default_route_uses_iface,
    detect_egress_iface,
    iface_exists,
    read_iface_mtu,
    require_root,
    set_iface_mtu,
)
from .pmtu import probe_pmtu
from .wg import wg_is_active, wg_peer_endpoints


@dataclass(frozen=True)
class Result:
    egress: str
    base_mtu: int
    effective_mtu: int
    wg_if: str
    wg_mtu: int


def _split_targets(items: Optional[list[str]]) -> list[str]:
    raw: list[str] = []
    for item in items or []:
        raw.extend([x.strip() for x in item.split(",") if x.strip()])
    return list(dict.fromkeys(raw))


def _choose(values: Iterable[int], policy: str) -> int:
    vals = sorted(values)
    if policy == "min":
        return vals[0]
    if policy == "max":
        return vals[-1]
    if policy == "median":
        return int(statistics.median(vals))
    raise ValueError(f"unknown policy: {policy}")


def run_automtu(args) -> int:
    require_root(args.dry_run)

    egress = args.egress_if or detect_egress_iface(ignore_vpn=not args.prefer_wg_egress)
    if not egress:
        print(
            "[automtu][ERROR] Could not detect egress interface (use --egress-if).",
            file=sys.stderr,
        )
        return 2
    if not iface_exists(egress):
        print(f"[automtu][ERROR] Interface {egress} does not exist.", file=sys.stderr)
        return 3

    if (
        args.egress_if is None
        and args.prefer_wg_egress
        and iface_exists(args.wg_if)
        and wg_is_active(args.wg_if)
        and default_route_uses_iface(args.wg_if)
    ):
        egress = args.wg_if
        print(f"[automtu] Using WireGuard interface {args.wg_if} as egress basis.")

    print(f"[automtu] Detected egress interface: {egress}")

    if args.force_egress_mtu:
        print(f"[automtu] Forcing egress MTU {args.force_egress_mtu} on {egress}")
        set_iface_mtu(egress, args.force_egress_mtu, args.dry_run)
        base_mtu = args.force_egress_mtu
    else:
        base_mtu = read_iface_mtu(egress)
    print(f"[automtu] Egress base MTU: {base_mtu}")

    targets = _split_targets(args.pmtu_target)
    if args.auto_pmtu_from_wg:
        if wg_is_active(args.wg_if):
            peers = wg_peer_endpoints(args.wg_if)
            if peers:
                print(
                    f"[automtu] Auto-added WG peer endpoints as PMTU targets: {', '.join(peers)}"
                )
                targets = list(dict.fromkeys([*targets, *peers]))
        else:
            print(
                f"[automtu] INFO: {args.wg_if} not active; skipping auto PMTU targets."
            )

    effective_mtu = base_mtu
    if targets:
        print(
            f"[automtu] Probing Path MTU for: {', '.join(targets)} (policy={args.pmtu_policy})"
        )
        good: list[int] = []
        for t in targets:
            p = probe_pmtu(
                t, args.pmtu_min_payload, args.pmtu_max_payload, args.pmtu_timeout
            )
            print(f"[automtu]  - {t}: {p if p else 'probe failed'}")
            if p:
                good.append(p)

        if good:
            chosen = _choose(good, args.pmtu_policy)
            print(f"[automtu] Selected Path MTU (policy={args.pmtu_policy}): {chosen}")
            effective_mtu = min(base_mtu, chosen)
        else:
            print(
                "[automtu] WARNING: All PMTU probes failed. Falling back to egress MTU."
            )

    if args.apply_egress_mtu:
        if egress == args.wg_if:
            print(
                f"[automtu] INFO: Skipping egress MTU apply because egress == {args.wg_if}."
            )
        else:
            print(
                f"[automtu] Applying effective MTU {effective_mtu} to egress {egress}"
            )
            set_iface_mtu(egress, effective_mtu, args.dry_run)

    wg_mtu = max(int(args.wg_min), int(effective_mtu) - int(args.wg_overhead))
    print(
        f"[automtu] Computed {args.wg_if} MTU: {wg_mtu} (overhead={args.wg_overhead}, min={args.wg_min})"
    )

    if args.set_wg_mtu is not None:
        forced = max(int(args.wg_min), int(args.set_wg_mtu))
        if forced != int(args.set_wg_mtu):
            print(
                f"[automtu][WARN] --set-wg-mtu clamped to {forced} (wg-min={args.wg_min})."
            )
        wg_mtu = forced
        print(f"[automtu] Forcing WireGuard MTU (override): {wg_mtu}")

    if args.apply_wg_mtu:
        if iface_exists(args.wg_if):
            set_iface_mtu(args.wg_if, wg_mtu, args.dry_run)
            print(f"[automtu] Applied: {args.wg_if} MTU {wg_mtu}")
        else:
            print(
                f"[automtu] NOTE: {args.wg_if} not present yet. Start WireGuard first, then re-run."
            )
    else:
        print("[automtu] INFO: Not applying WireGuard MTU (use --apply-wg-mtu).")

    _ = Result(
        egress=egress,
        base_mtu=base_mtu,
        effective_mtu=effective_mtu,
        wg_if=args.wg_if,
        wg_mtu=wg_mtu,
    )
    return 0
