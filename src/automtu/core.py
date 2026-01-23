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
from .output import Logger, OutputMode, emit_json, emit_single_number
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
    mode = OutputMode(
        print_mtu=getattr(args, "print_mtu", None),
        print_json=bool(getattr(args, "print_json", False)),
    )
    err = mode.validate()
    if err:
        print(f"[automtu][ERROR] {err}", file=sys.stderr)
        return 4

    log = Logger(mode.machine).log

    needs_root = bool(
        getattr(args, "apply_egress_mtu", False)
        or getattr(args, "apply_wg_mtu", False)
        or (getattr(args, "force_egress_mtu", None) is not None)
        or (getattr(args, "persist", None) is not None)
    )
    require_root(dry=args.dry_run, needs_root=needs_root)

    # Persistence mode: install/uninstall persistence mechanism and exit.
    if getattr(args, "persist", None):
        if args.persist == "systemd":
            from .persist import persist_systemd, uninstall_systemd

            if getattr(args, "uninstall", False):
                uninstall_systemd(dry=args.dry_run)
                return 0

            persist_systemd(sys.argv, dry=args.dry_run)
            return 0

        print(
            f"[automtu][ERROR] Unknown persist backend: {args.persist}", file=sys.stderr
        )
        return 4

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
        log(f"[automtu] Using WireGuard interface {args.wg_if} as egress basis.")

    log(f"[automtu] Detected egress interface: {egress}")

    # Base MTU (optionally forced)
    if args.force_egress_mtu:
        log(f"[automtu] Forcing egress MTU {args.force_egress_mtu} on {egress}")
        set_iface_mtu(egress, args.force_egress_mtu, args.dry_run)
        base_mtu = int(args.force_egress_mtu)
    else:
        base_mtu = int(read_iface_mtu(egress))
    log(f"[automtu] Egress base MTU: {base_mtu}")

    # Targets (explicit + optional WG auto targets)
    targets = _split_targets(args.pmtu_target)
    auto_targets_added: list[str] = []

    if args.auto_pmtu_from_wg:
        if wg_is_active(args.wg_if):
            peers = wg_peer_endpoints(args.wg_if)
            if peers:
                auto_targets_added = peers[:]
                log(
                    f"[automtu] Auto-added WG peer endpoints as PMTU targets: {', '.join(peers)}"
                )
                targets = list(dict.fromkeys([*targets, *peers]))
        else:
            log(f"[automtu] INFO: {args.wg_if} not active; skipping auto PMTU targets.")

    # PMTU probing
    effective_mtu = base_mtu
    probe_results: dict[str, Optional[int]] = {}
    chosen_pmtu: Optional[int] = None

    if targets:
        log(
            f"[automtu] Probing Path MTU for: {', '.join(targets)} (policy={args.pmtu_policy})"
        )
        good: list[int] = []
        for t in targets:
            p = probe_pmtu(
                t, args.pmtu_min_payload, args.pmtu_max_payload, args.pmtu_timeout
            )
            probe_results[t] = p
            log(f"[automtu]  - {t}: {p if p else 'probe failed'}")
            if p:
                good.append(int(p))

        if good:
            chosen_pmtu = _choose(good, args.pmtu_policy)
            log(
                f"[automtu] Selected Path MTU (policy={args.pmtu_policy}): {chosen_pmtu}"
            )
            effective_mtu = min(base_mtu, chosen_pmtu)
        else:
            log(
                "[automtu] WARNING: All PMTU probes failed. Falling back to egress MTU."
            )

    # Apply egress MTU (optional)
    egress_applied = False
    if args.apply_egress_mtu:
        if egress == args.wg_if:
            log(
                f"[automtu] INFO: Skipping egress MTU apply because egress == {args.wg_if}."
            )
        else:
            log(f"[automtu] Applying effective MTU {effective_mtu} to egress {egress}")
            set_iface_mtu(egress, effective_mtu, args.dry_run)
            egress_applied = True

    # Compute WG MTU
    wg_mtu = max(int(args.wg_min), int(effective_mtu) - int(args.wg_overhead))
    log(
        f"[automtu] Computed {args.wg_if} MTU: {wg_mtu} (overhead={args.wg_overhead}, min={args.wg_min})"
    )

    wg_mtu_set: Optional[int] = None
    wg_mtu_clamped = False

    if args.set_wg_mtu is not None:
        wg_mtu_set = int(args.set_wg_mtu)
        forced = max(int(args.wg_min), wg_mtu_set)
        wg_mtu_clamped = forced != wg_mtu_set
        if wg_mtu_clamped:
            log(
                f"[automtu][WARN] --set-wg-mtu clamped to {forced} (wg-min={args.wg_min})."
            )
        wg_mtu = forced
        log(f"[automtu] Forcing WireGuard MTU (override): {wg_mtu}")

    # Apply WG MTU (optional)
    wg_present = iface_exists(args.wg_if)
    wg_active = wg_is_active(args.wg_if) if wg_present else False
    wg_applied = False

    if args.apply_wg_mtu:
        if wg_present:
            set_iface_mtu(args.wg_if, wg_mtu, args.dry_run)
            log(f"[automtu] Applied: {args.wg_if} MTU {wg_mtu}")
            wg_applied = True
        else:
            log(
                f"[automtu] NOTE: {args.wg_if} not present yet. Start WireGuard first, then re-run."
            )
    else:
        log("[automtu] INFO: Not applying WireGuard MTU (use --apply-wg-mtu).")

    # Machine-readable outputs
    if emit_single_number(
        mode, base_mtu=base_mtu, effective_mtu=effective_mtu, wg_mtu=wg_mtu
    ):
        return 0

    if emit_json(
        mode,
        egress_iface=egress,
        base_mtu=base_mtu,
        effective_mtu=effective_mtu,
        egress_forced_mtu=int(args.force_egress_mtu) if args.force_egress_mtu else None,
        egress_applied=egress_applied,
        pmtu_targets=targets,
        pmtu_auto_targets_added=auto_targets_added,
        pmtu_policy=args.pmtu_policy,
        pmtu_chosen=chosen_pmtu,
        pmtu_results=probe_results,
        wg_iface=args.wg_if,
        wg_mtu=wg_mtu,
        wg_overhead=int(args.wg_overhead),
        wg_min=int(args.wg_min),
        wg_set_mtu=wg_mtu_set,
        wg_clamped=wg_mtu_clamped,
        wg_present=wg_present,
        wg_active=wg_active,
        wg_applied=wg_applied,
        dry_run=bool(args.dry_run),
    ):
        return 0

    _ = Result(
        egress=egress,
        base_mtu=base_mtu,
        effective_mtu=effective_mtu,
        wg_if=args.wg_if,
        wg_mtu=wg_mtu,
    )
    return 0
