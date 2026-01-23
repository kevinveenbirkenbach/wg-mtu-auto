from __future__ import annotations

import re
from typing import Optional

from .net import iface_exists, list_ifaces


_BRIDGE_RE = re.compile(r"^br-[0-9a-f]+$", re.IGNORECASE)


def _split_items(items: Optional[list[str]]) -> list[str]:
    raw: list[str] = []
    for item in items or []:
        raw.extend([x.strip() for x in item.split(",") if x.strip()])
    # de-dup while preserving order
    return list(dict.fromkeys(raw))


def detect_docker_ifaces(
    docker_if_args: Optional[list[str]], *, include_user_bridges: bool
) -> list[str]:
    """
    Determine Docker-related interfaces to apply MTU to.

    - If docker_if_args is given (repeatable / comma-separated), use those names (deduped).
    - Otherwise auto-detect:
      - docker0 (if exists)
      - br-* user bridges (if include_user_bridges=True)
    """
    explicit = _split_items(docker_if_args)
    if explicit:
        # keep only real interfaces; silently drop unknown names
        return [i for i in explicit if iface_exists(i)]

    found: list[str] = []

    # docker0 is the classic default bridge
    if iface_exists("docker0"):
        found.append("docker0")

    if include_user_bridges:
        for name in list_ifaces():
            if _BRIDGE_RE.match(name):
                found.append(name)

    # de-dup (defensive)
    return list(dict.fromkeys(found))
