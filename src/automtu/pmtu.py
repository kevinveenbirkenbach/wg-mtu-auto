from __future__ import annotations

import ipaddress
import subprocess
from typing import Optional


def _is_ipv6(target: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(target), ipaddress.IPv6Address)
    except ValueError:
        return ":" in target  # best-effort for hostnames


def _rc(cmd: list[str]) -> int:
    return subprocess.run(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode


def _ping_ok(payload: int, target: str, timeout_s: float) -> bool:
    cmd = [
        "ping",
        "-M",
        "do",
        "-c",
        "1",
        "-s",
        str(payload),
        "-W",
        str(max(1, int(round(timeout_s)))),
    ]
    if _is_ipv6(target):
        cmd.insert(1, "-6")
    return _rc(cmd + [target]) == 0


def probe_pmtu(
    target: str, lo_payload: int = 1200, hi_payload: int = 1472, timeout: float = 1.0
) -> Optional[int]:
    hdr = 48 if _is_ipv6(target) else 28

    if not _ping_ok(lo_payload, target, timeout):
        for p in (1180, 1160, 1140):
            if _ping_ok(p, target, timeout):
                lo_payload = p
                break
        else:
            return None

    lo, hi, best = lo_payload, hi_payload, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if _ping_ok(mid, target, timeout):
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return (best + hdr) if best is not None else None
