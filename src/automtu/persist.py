from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path
from typing import List


_SYSTEMD_UNIT_PATH = Path("/etc/systemd/system/automtu.service")
_DOCKER_SYSTEMD_UNIT_PATH = Path("/etc/systemd/system/automtu-docker.service")


def _strip_persist_args(argv: List[str]) -> List[str]:
    """
    Remove persistence-only arguments from argv:
    - --persist systemd|docker
    - --persist=systemd|docker
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


def _needs_docker_ordering(filtered_argv: List[str]) -> bool:
    """
    Heuristic: If we apply docker MTU (directly or via --apply-all), order after docker.service.
    """
    return ("--apply-docker-mtu" in filtered_argv) or ("--apply-all" in filtered_argv)


def _build_unit(execstart: str, *, docker_ordering: bool) -> str:
    after_lines = ["network-online.target"]
    wants_lines = ["network-online.target"]

    if docker_ordering:
        after_lines.append("docker.service")
        wants_lines.append("docker.service")

    after = " ".join(after_lines)
    wants = " ".join(wants_lines)

    return f"""\
[Unit]
Description=Auto MTU via automtu
After={after}
Wants={wants}

[Service]
Type=oneshot
ExecStart={execstart}

[Install]
WantedBy=multi-user.target
"""


def _install_unit(unit_path: Path, unit_text: str, *, dry: bool) -> None:
    if dry:
        print(f"[automtu] DRY-RUN: would write systemd unit to {unit_path}")
        print(unit_text.rstrip())
        print("[automtu] DRY-RUN: would run: systemctl daemon-reload")
        print(f"[automtu] DRY-RUN: would run: systemctl enable {unit_path.name}")
        return

    unit_path.write_text(unit_text)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", unit_path.name], check=True)
    print(f"[automtu] Installed and enabled systemd service: {unit_path.name}")
    print(
        f"[automtu] Tip: run 'systemctl start {unit_path.name}' to apply immediately."
    )


def _uninstall_unit(unit_path: Path, *, dry: bool) -> None:
    if dry:
        print(f"[automtu] DRY-RUN: would run: systemctl disable {unit_path.name}")
        print(f"[automtu] DRY-RUN: would remove: {unit_path} (if exists)")
        print("[automtu] DRY-RUN: would run: systemctl daemon-reload")
        return

    subprocess.run(["systemctl", "disable", unit_path.name], check=True)
    if unit_path.exists():
        unit_path.unlink()
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    print(f"[automtu] Uninstalled systemd service: {unit_path.name}")


def persist_systemd(argv: List[str], *, dry: bool) -> None:
    """
    Install a systemd oneshot service that re-runs automtu with the same arguments.
    Adds docker ordering automatically if docker MTU is applied.
    """
    if not argv:
        raise ValueError("argv must not be empty")

    filtered = _strip_persist_args(argv[:])
    if not filtered:
        raise ValueError("argv filtered to empty; cannot persist")

    exe = _resolve_exec(filtered[0])
    args = [exe, *filtered[1:]]
    execstart = shlex.join(args)

    unit = _build_unit(execstart, docker_ordering=_needs_docker_ordering(filtered))
    _install_unit(_SYSTEMD_UNIT_PATH, unit, dry=dry)


def uninstall_systemd(*, dry: bool) -> None:
    """
    Uninstall the base systemd persistence backend.
    """
    _uninstall_unit(_SYSTEMD_UNIT_PATH, dry=dry)


def persist_docker(argv: List[str], *, dry: bool) -> None:
    """
    Docker-focused persistence backend:
    always orders after docker.service (even if args don't include docker flags),
    because the user chose it explicitly.
    """
    if not argv:
        raise ValueError("argv must not be empty")

    filtered = _strip_persist_args(argv[:])
    if not filtered:
        raise ValueError("argv filtered to empty; cannot persist")

    exe = _resolve_exec(filtered[0])
    args = [exe, *filtered[1:]]
    execstart = shlex.join(args)

    unit = _build_unit(execstart, docker_ordering=True)
    _install_unit(_DOCKER_SYSTEMD_UNIT_PATH, unit, dry=dry)


def uninstall_docker(*, dry: bool) -> None:
    """
    Uninstall the docker-ordered systemd backend.
    """
    _uninstall_unit(_DOCKER_SYSTEMD_UNIT_PATH, dry=dry)
