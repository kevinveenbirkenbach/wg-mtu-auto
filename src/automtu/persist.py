from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path
from typing import List


_SYSTEMD_UNIT_PATH = Path("/etc/systemd/system/automtu.service")


def _strip_persist_args(argv: List[str]) -> List[str]:
    """
    Remove persistence-only arguments from argv:
    - --persist systemd
    - --persist=systemd
    - --uninstall
    Keeps all other args as-is.
    """
    out: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--persist":
            i += 1
            if i < len(argv) and not argv[i].startswith("-"):
                i += 1
            continue
        if a.startswith("--persist="):
            i += 1
            continue
        if a == "--uninstall":
            i += 1
            continue
        out.append(a)
        i += 1
    return out


def _resolve_exec(argv0: str) -> str:
    """
    Resolve the executable path for systemd ExecStart.

    Prefer an absolute path (from PATH lookup). Fall back to argv0.
    """
    resolved = shutil.which(argv0)
    if resolved:
        return resolved
    return argv0


def persist_systemd(argv: List[str], *, dry: bool) -> None:
    """
    Install a systemd oneshot service that re-runs automtu with the same arguments.
    This provides a distro-agnostic persistence mechanism.
    """
    if not argv:
        raise ValueError("argv must not be empty")

    filtered = _strip_persist_args(argv[:])
    if not filtered:
        raise ValueError("argv filtered to empty; cannot persist")

    exe = _resolve_exec(filtered[0])
    args = [exe, *filtered[1:]]

    execstart = shlex.join(args)

    unit = f"""\
[Unit]
Description=Auto MTU via automtu
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart={execstart}

[Install]
WantedBy=multi-user.target
"""

    if dry:
        print(f"[automtu] DRY-RUN: would write systemd unit to {_SYSTEMD_UNIT_PATH}")
        print(unit.rstrip())
        print("[automtu] DRY-RUN: would run: systemctl daemon-reload")
        print("[automtu] DRY-RUN: would run: systemctl enable automtu.service")
        return

    _SYSTEMD_UNIT_PATH.write_text(unit)

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "automtu.service"], check=True)

    print("[automtu] Installed and enabled systemd service: automtu.service")
    print("[automtu] Tip: run 'systemctl start automtu.service' to apply immediately.")


def uninstall_systemd(*, dry: bool) -> None:
    """
    Uninstall the systemd persistence backend:
    - disable automtu.service
    - remove unit file (if present)
    - daemon-reload
    """
    if dry:
        print("[automtu] DRY-RUN: would run: systemctl disable automtu.service")
        print(f"[automtu] DRY-RUN: would remove: {_SYSTEMD_UNIT_PATH} (if exists)")
        print("[automtu] DRY-RUN: would run: systemctl daemon-reload")
        return

    subprocess.run(["systemctl", "disable", "automtu.service"], check=True)

    if _SYSTEMD_UNIT_PATH.exists():
        _SYSTEMD_UNIT_PATH.unlink()

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    print("[automtu] Uninstalled systemd service: automtu.service")
