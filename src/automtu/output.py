# src/automtu/output.py
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OutputMode:
    print_mtu: Optional[str]  # "egress" | "effective" | "wg" | None
    print_json: bool

    @property
    def machine(self) -> bool:
        return bool(self.print_mtu or self.print_json)

    def validate(self) -> Optional[str]:
        if self.print_mtu and self.print_json:
            return "--print-mtu and --print-json are mutually exclusive."
        return None


class Logger:
    """
    Routes logs to stderr when in machine mode, so stdout can be cleanly parsed.
    """

    def __init__(self, machine_mode: bool) -> None:
        self._machine = bool(machine_mode)

    def log(self, msg: str) -> None:
        if self._machine:
            print(msg, file=sys.stderr)
        else:
            print(msg)


def emit_single_number(
    mode: OutputMode, *, base_mtu: int, effective_mtu: int, wg_mtu: int
) -> bool:
    """
    Returns True if it emitted output (and caller should return).
    """
    if not mode.print_mtu:
        return False

    key = mode.print_mtu
    if key == "egress":
        print(int(base_mtu))
        return True
    if key == "effective":
        print(int(effective_mtu))
        return True
    if key == "wg":
        print(int(wg_mtu))
        return True

    print("[automtu][ERROR] Invalid --print-mtu value.", file=sys.stderr)
    raise SystemExit(4)


def emit_json(
    mode: OutputMode,
    *,
    egress_iface: str,
    base_mtu: int,
    effective_mtu: int,
    egress_forced_mtu: Optional[int],
    egress_applied: bool,
    pmtu_targets: list[str],
    pmtu_auto_targets_added: list[str],
    pmtu_policy: str,
    pmtu_chosen: Optional[int],
    pmtu_results: dict[str, Optional[int]],
    wg_iface: str,
    wg_mtu: int,
    wg_overhead: int,
    wg_min: int,
    wg_set_mtu: Optional[int],
    wg_clamped: bool,
    wg_present: bool,
    wg_active: bool,
    wg_applied: bool,
    docker_ifaces: Optional[list[str]] = None,
    docker_applied: Optional[list[str]] = None,
    dry_run: bool,
) -> bool:
    """
    Returns True if it emitted output (and caller should return).
    """
    if not mode.print_json:
        return False

    docker_ifaces = list(docker_ifaces or [])
    docker_applied = list(docker_applied or [])

    payload = {
        "egress": {
            "iface": egress_iface,
            "base_mtu": int(base_mtu),
            "effective_mtu": int(effective_mtu),
            "forced_mtu": int(egress_forced_mtu)
            if egress_forced_mtu is not None
            else None,
            "applied": bool(egress_applied),
        },
        "pmtu": {
            "targets": list(pmtu_targets),
            "auto_targets_added": list(pmtu_auto_targets_added),
            "policy": pmtu_policy,
            "chosen": int(pmtu_chosen) if pmtu_chosen is not None else None,
            "results": {
                k: (int(v) if v is not None else None) for k, v in pmtu_results.items()
            },
        },
        "wg": {
            "iface": wg_iface,
            "mtu": int(wg_mtu),
            "overhead": int(wg_overhead),
            "min": int(wg_min),
            "set_mtu": int(wg_set_mtu) if wg_set_mtu is not None else None,
            "clamped": bool(wg_clamped),
            "present": bool(wg_present),
            "active": bool(wg_active),
            "applied": bool(wg_applied),
        },
        "docker": {
            "ifaces": docker_ifaces,
            "applied": docker_applied,
        },
        "dry_run": bool(dry_run),
    }

    print(json.dumps(payload, sort_keys=True))
    return True
