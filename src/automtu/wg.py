from __future__ import annotations

import re
import subprocess
from typing import List

from .net import iface_exists


def _run(cmd: list[str]) -> str:
    return subprocess.run(
        cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout.strip()


def _rc(cmd: list[str]) -> int:
    return subprocess.run(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode


def wg_is_active(wg_if: str) -> bool:
    return iface_exists(wg_if) and _rc(["wg", "show", wg_if]) == 0


def wg_peer_endpoints(wg_if: str) -> List[str]:
    targets: list[str] = []

    out = _run(["wg", "show", wg_if, "endpoints"])
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1] != "(none)":
            ep = parts[-1]
            host = ep.rsplit(":", 1)[0].strip("[]")
            targets.append(host)

    if not targets:
        conf = _run(["wg", "showconf", wg_if])
        for m in re.finditer(r"^Endpoint\s*=\s*(.+)$", conf, flags=re.MULTILINE):
            ep = m.group(1).strip()
            host = ep.rsplit(":", 1)[0].strip("[]")
            targets.append(host)

    dedup: list[str] = []
    for t in targets:
        if t and t not in dedup:
            dedup.append(t)
    return dedup
