from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
from typing import Optional


def _run(cmd: list[str]) -> str:
    return subprocess.run(
        cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout.strip()


def iface_exists(iface: str) -> bool:
    return pathlib.Path(f"/sys/class/net/{iface}").exists()


def read_iface_mtu(iface: str) -> int:
    return int(pathlib.Path(f"/sys/class/net/{iface}/mtu").read_text().strip())


def set_iface_mtu(iface: str, mtu: int, dry: bool) -> None:
    if dry:
        print(f"[automtu] DRY-RUN: ip link set mtu {mtu} dev {iface}")
        return
    subprocess.run(["ip", "link", "set", "mtu", str(mtu), "dev", iface], check=True)


def require_root(*, dry: bool, needs_root: bool) -> None:
    if needs_root and (not dry) and os.geteuid() != 0:
        print(
            "[automtu][ERROR] Please run as root (sudo) or use --dry-run.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def detect_egress_iface(ignore_vpn: bool = True) -> Optional[str]:
    devs: list[str] = []
    for cmd in (
        ["ip", "-4", "route", "show", "default"],
        ["ip", "-6", "route", "show", "default"],
    ):
        for line in _run(cmd).splitlines():
            m = re.search(r"\bdev\s+(\S+)", line)
            if m:
                devs.append(m.group(1))

    if not devs:
        for cmd in (
            ["ip", "route", "get", "1.1.1.1"],
            ["ip", "-6", "route", "get", "2606:4700:4700::1111"],
        ):
            m = re.search(r"\bdev\s+(\S+)", _run(cmd))
            if m:
                devs.append(m.group(1))

    seen: set[str] = set()
    for d in devs:
        if not d or d == "lo" or not iface_exists(d):
            continue
        if ignore_vpn and re.match(r"^(wg|tun)\d*$", d):
            continue
        if d in seen:
            continue
        seen.add(d)
        return d
    return None


def default_route_uses_iface(iface: str) -> bool:
    pat = rf"\bdev\s+{re.escape(iface)}\b"
    for cmd in (
        ["ip", "-4", "route", "show", "default"],
        ["ip", "-6", "route", "show", "default"],
    ):
        if re.search(pat, _run(cmd)):
            return True
    return False
