# automtu — Practical Guide

The tool can:
- auto-detect your egress interface (e.g., eth0)
- probe Path MTU (PMTU) using `ping -M do`
- compute a safe WireGuard MTU: `effective_mtu - overhead` (default overhead=80)
- apply MTU to egress and/or WireGuard (explicit flags)

## Recipes

1) Only compute/show (safe default):
    automtu --dry-run

2) Probe PMTU and apply to egress:
    sudo automtu --pmtu-target 1.1.1.1 --apply-egress-mtu

3) Auto-add WireGuard peer endpoints as PMTU targets and apply WG MTU:
    sudo automtu --auto-pmtu-from-wg --apply-wg-mtu

4) Prefer WireGuard as egress basis if default route uses wg0:
    sudo automtu --prefer-wg-egress --auto-pmtu-from-wg --apply-wg-mtu

5) Force WG MTU:
    sudo automtu --set-wg-mtu 1372 --apply-wg-mtu

## Notes

- Applying MTU requires root (unless `--dry-run`).
- PMTU probing can fail if ICMP is blocked; the tool then falls back to egress MTU.
- Runtime MTU changes are not persistent across reboots.
