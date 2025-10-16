#!/usr/bin/env python3
"""
wg_mtu_auto.py — Auto-detect egress IF, optionally probe Path MTU to one or more targets,
compute the correct WireGuard MTU, and apply it.

Examples:
  sudo ./main.py
  sudo ./main.py --force-egress-mtu 1452
  sudo ./main.py --pmtu-target 46.4.224.77 --pmtu-target 2a01:4f8:2201:4695::2
  sudo ./main.py --pmtu-target 46.4.224.77,2a01:4f8:2201:4695::2 --pmtu-policy min
  sudo ./main.py --prefer-wg-egress --auto-pmtu-from-wg
  ./main.py --dry-run
"""
import argparse
import ipaddress
import os
import pathlib
import re
import statistics
import subprocess
import sys


# ----------------- helpers -----------------

def run(cmd):  # -> str
    return subprocess.run(
        cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout.strip()


def rc(cmd):  # -> int
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode


def exists_iface(iface):  # -> bool
    return pathlib.Path(f"/sys/class/net/{iface}").exists()


def read_mtu(iface):  # -> int
    with open(f"/sys/class/net/{iface}/mtu", "r") as f:
        return int(f.read().strip())


def set_mtu(iface, mtu, dry):
    if dry:
        print(f"[wg-mtu] DRY-RUN: ip link set mtu {mtu} dev {iface}")
    else:
        subprocess.run(["ip", "link", "set", "mtu", str(mtu), "dev", iface], check=True)


def require_root(dry):
    if not dry and os.geteuid() != 0:
        print("[wg-mtu][ERROR] Please run as root (sudo) or use --dry-run.", file=sys.stderr)
        sys.exit(1)


def is_ipv6(addr):  # -> bool
    try:
        return isinstance(ipaddress.ip_address(addr), ipaddress.IPv6Address)
    except ValueError:
        # best-effort for hostnames (contains ':')
        return ":" in addr


# ----------------- route & iface selection -----------------

def default_route_lines():
    lines = []
    for cmd in (["ip", "-4", "route", "show", "default"], ["ip", "-6", "route", "show", "default"]):
        out = run(cmd)
        if out:
            lines.extend(out.splitlines())
    return lines


def get_default_ifaces(ignore_vpn=True):  # -> list[str]
    devs = []
    for line in default_route_lines():
        m = re.search(r"\bdev\s+(\S+)", line)
        if m:
            devs.append(m.group(1))
    # fallback via route get
    if not devs:
        for cmd in (["ip", "route", "get", "1.1.1.1"], ["ip", "-6", "route", "get", "2606:4700:4700::1111"]):
            out = run(cmd)
            m = re.search(r"\bdev\s+(\S+)", out)
            if m:
                devs.append(m.group(1))
    uniq = []
    for d in devs:
        if not d or d == "lo" or not exists_iface(d):
            continue
        if ignore_vpn and re.match(r"^(wg|tun)\d*$", d):
            continue
        if d not in uniq:
            uniq.append(d)
    return uniq


def wg_default_is_active(wg_if: str) -> bool:
    # check if any default route is via wg_if
    return any(re.search(rf"\bdev\s+{re.escape(wg_if)}\b", line) for line in default_route_lines())


# ----------------- PMTU probing -----------------

def ping_ok(payload, target, timeout_s):  # -> bool
    base = ["ping", "-M", "do", "-c", "1", "-s", str(payload), "-W", str(max(1, int(round(timeout_s))))]
    if is_ipv6(target):
        base.insert(1, "-6")
    return rc(base + [target]) == 0


def probe_pmtu(target, lo_payload=1200, hi_payload=1472, timeout=1.0):  # -> int|None
    """Binary-search the largest payload that passes with DF. Return Path MTU (payload + hdr) or None.
       Header: +28 (IPv4), +48 (IPv6)."""
    hdr = 48 if is_ipv6(target) else 28
    # ensure lower bound works; if not, try smaller floors
    if not ping_ok(lo_payload, target, timeout):
        for p in (1180, 1160, 1140):
            if ping_ok(p, target, timeout):
                lo_payload = p
                break
        else:
            return None
    lo, hi, best = lo_payload, hi_payload, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if ping_ok(mid, target, timeout):
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return (best + hdr) if best is not None else None


def choose_effective(pmtus, policy="min"):  # -> int
    if not pmtus:
        raise ValueError("no PMTUs to choose from")
    if policy == "min":
        return min(pmtus)
    if policy == "max":
        return max(pmtus)
    if policy == "median":
        return int(statistics.median(sorted(pmtus)))
    raise ValueError(f"unknown policy {policy}")


# ----------------- WireGuard helpers (opt-in) -----------------

def wg_is_active(wg_if: str) -> bool:
    if not exists_iface(wg_if):
        return False
    return rc(["wg", "show", wg_if]) == 0


def wg_peer_endpoints(wg_if: str) -> list[str]:
    """Return list of peer endpoints (hostnames/IPs) – port stripped."""
    targets = []

    # 1) Try: wg show <if> endpoints
    out = run(["wg", "show", wg_if, "endpoints"])
    for line in out.splitlines():
        # format: <peer_public_key>\t<endpoint or (none)>
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1] != "(none)":
            ep = parts[-1]  # host:port
            host = ep.rsplit(":", 1)[0]
            # IPv6 endpoint may be like [2001:db8::1]:51820
            host = host.strip("[]")
            targets.append(host)

    # 2) Fallback: wg showconf (root may be required)
    if not targets:
        conf = run(["wg", "showconf", wg_if])
        if conf:
            for m in re.finditer(r"^Endpoint\s*=\s*(.+)$", conf, flags=re.MULTILINE):
                ep = m.group(1).strip()
                host = ep.rsplit(":", 1)[0].strip("[]")
                targets.append(host)

    # dedupe & sanity
    cleaned = []
    for t in targets:
        if t and t not in cleaned:
            cleaned.append(t)
    return cleaned


# ----------------- main -----------------

def main():
    ap = argparse.ArgumentParser(description="Compute/apply WireGuard MTU based on egress MTU and optional multi-target PMTU probing.")
    ap.add_argument("--egress-if", help="Explicit egress interface (auto-detected if omitted).")
    ap.add_argument("--prefer-wg-egress", action="store_true",
                    help="Allow/consider wg* as egress and prefer it if default route uses wg (default: disabled).")
    ap.add_argument("--auto-pmtu-from-wg", action="store_true",
                    help="Automatically add WireGuard peer endpoints as PMTU targets (default: disabled).")
    ap.add_argument("--wg-if", default=os.environ.get("WG_IF", "wg0"), help="WireGuard interface name (default: wg0).")
    ap.add_argument("--wg-overhead", type=int, default=int(os.environ.get("WG_OVERHEAD", "80")), help="Bytes of WG overhead to subtract (default: 80).")
    ap.add_argument("--wg-min", type=int, default=int(os.environ.get("WG_MIN", "1280")), help="Minimum allowed WG MTU (default: 1280).")
    # PMTU (multi-target)
    ap.add_argument("--pmtu-target", action="append", help="Target hostname/IP to probe PMTU. Can be given multiple times OR comma-separated.")
    ap.add_argument("--pmtu-timeout", type=float, default=1.0, help="Timeout (seconds) per ping probe (default: 1.0).")
    ap.add_argument("--pmtu-min-payload", type=int, default=1200, help="Lower bound payload for PMTU search (default: 1200).")
    ap.add_argument("--pmtu-max-payload", type=int, default=1472, help="Upper bound payload for PMTU search (default: 1472 ~ 1500-28).")
    ap.add_argument("--pmtu-policy", choices=["min", "median", "max"], default="min",
                    help="How to choose effective PMTU across multiple targets (default: min).")
    ap.add_argument("--apply-egress-mtu", action="store_true",
                    help="Apply the effective Path MTU to the detected egress interface (e.g. eth0).")
     
    ap.add_argument("--dry-run", action="store_true", help="Show actions without applying changes.")
    # NEW: force a specific WireGuard MTU (overrides computed value)
    ap.add_argument("--set-wg-mtu", type=int, help="Force a specific MTU to apply on the WireGuard interface (overrides computed value).")
    # (legacy / optional) force egress MTU
    ap.add_argument("--force-egress-mtu", type=int, help="Force this MTU on the egress interface before computing wg MTU.")
    args = ap.parse_args()

    require_root(args.dry_run)

    # Egress detection (wg ignored by default)
    if args.egress_if:
        egress = args.egress_if
    else:
        ignore_vpn = not args.prefer_wg_egress
        cands = get_default_ifaces(ignore_vpn=ignore_vpn)
        # If we allow wg and default route is via wg-if, prefer it first
        if args.prefer_wg_egress and wg_is_active(args.wg_if) and wg_default_is_active(args.wg_if):
            if args.wg_if in cands:
                cands.remove(args.wg_if)
            cands.insert(0, args.wg_if)
        egress = cands[0] if cands else None

    if not egress:
        print("[wg-mtu][ERROR] Could not detect egress interface (use --egress-if).", file=sys.stderr)
        sys.exit(2)
    if not exists_iface(egress):
        print(f"[wg-mtu][ERROR] Interface {egress} does not exist.", file=sys.stderr)
        sys.exit(3)
    print(f"[wg-mtu] Detected egress interface: {egress}")

    # Egress MTU
    if args.prefer_wg_egress and egress == args.wg_if:
        print(f"[wg-mtu] Using WireGuard interface {args.wg_if} as egress basis.")
    if args.wg_if == egress and not wg_is_active(args.wg_if):
        print(f"[wg-mtu][WARN] {args.wg_if} selected as egress but WireGuard is not active.", file=sys.stderr)

    if args.force_egress_mtu:
        print(f"[wg-mtu] Forcing egress MTU {args.force_egress_mtu} on {egress}")
        set_mtu(egress, args.force_egress_mtu, args.dry_run)
        base_mtu = args.force_egress_mtu
    else:
        base_mtu = read_mtu(egress)
    print(f"[wg-mtu] Egress base MTU: {base_mtu}")

    # Build PMTU target list
    pmtu_targets = []
    if args.pmtu_target:
        for item in args.pmtu_target:
            pmtu_targets.extend([x.strip() for x in item.split(",") if x.strip()])

    if args.auto_pmtu_from_wg:
        if wg_is_active(args.wg_if):
            wg_targets = wg_peer_endpoints(args.wg_if)
            if wg_targets:
                print(f"[wg-mtu] Auto-added WG peer endpoints as PMTU targets: {', '.join(wg_targets)}")
                pmtu_targets.extend(wg_targets)
            else:
                print("[wg-mtu] INFO: No WG peer endpoints discovered (wg show/showconf).")
        else:
            print(f"[wg-mtu] INFO: {args.wg_if} is not active; skipping auto PMTU targets from WG.")

    # Deduplicate PMTU targets
    if pmtu_targets:
        pmtu_targets = list(dict.fromkeys(pmtu_targets))

    # PMTU probing
    effective_mtu = base_mtu
    if pmtu_targets:
        good = []
        print(f"[wg-mtu] Probing Path MTU for: {', '.join(pmtu_targets)} (policy={args.pmtu_policy})")
        for t in pmtu_targets:
            p = probe_pmtu(t, args.pmtu_min_payload, args.pmtu_max_payload, args.pmtu_timeout)
            print(f"[wg-mtu]  - {t}: {p if p else 'probe failed'}")
            if p:
                good.append(p)
        if good:
            chosen = choose_effective(good, args.pmtu_policy)
            print(f"[wg-mtu] Selected Path MTU (policy={args.pmtu_policy}): {chosen}")
            effective_mtu = min(base_mtu, chosen)
        else:
            print("[wg-mtu] WARNING: All PMTU probes failed. Falling back to egress MTU.")

    # Optionally apply the effective MTU to the egress interface
    if args.apply_egress_mtu:
        if egress == args.wg_if:
            print(f"[wg-mtu] INFO: Skipping egress MTU apply because egress == {args.wg_if}.")
        else:
            print(f"[wg-mtu] Applying effective MTU {effective_mtu} to egress {egress}")
            set_mtu(egress, effective_mtu, args.dry_run)

    # Compute WG MTU
    wg_mtu = max(args.wg_min, effective_mtu - args.wg_overhead)
    print(f"[wg-mtu] Computed {args.wg_if} MTU: {wg_mtu}  (overhead={args.wg_overhead}, min={args.wg_min})")

    # --- NEW: override with --set-wg-mtu if provided
    if args.set_wg_mtu is not None:
        if args.set_wg_mtu < args.wg_min:
            print(f"[wg-mtu][WARN] --set-wg-mtu {args.set_wg_mtu} is below wg-min {args.wg_min}; clamping to {args.wg_min}.")
            args.set_wg_mtu = args.wg_min
        wg_mtu = args.set_wg_mtu
        print(f"[wg-mtu] Forcing WireGuard MTU (override): {wg_mtu}")

    # Apply
    if exists_iface(args.wg_if):
        set_mtu(args.wg_if, wg_mtu, args.dry_run)
        print(f"[wg-mtu] Applied: {args.wg_if} MTU {wg_mtu}")
    else:
        print(f"[wg-mtu] NOTE: {args.wg_if} not present yet. Start WireGuard first, then re-run this script.")

    print(f"[wg-mtu] Done. Summary: egress={egress} mtu={base_mtu}, effective_mtu={effective_mtu}, {args.wg_if}_mtu={wg_mtu}")


if __name__ == "__main__":
    main()
