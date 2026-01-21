# automtu
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-blue?logo=github)](https://github.com/sponsors/kevinveenbirkenbach) [![Patreon](https://img.shields.io/badge/Support-Patreon-orange?logo=patreon)](https://www.patreon.com/c/kevinveenbirkenbach) [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20Coffee-Funding-yellow?logo=buymeacoffee)](https://buymeacoffee.com/kevinveenbirkenbach) [![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://s.veen.world/paypaldonate)

Auto-detect your egress interface, optionally probe Path MTU (PMTU) using DF-ping,
compute a WireGuard MTU, and apply MTU settings.

## Install (editable)
pip install -e .

## Usage

Show only (no changes):
    automtu --dry-run

Probe PMTU to targets and apply on egress:
    sudo automtu --pmtu-target registry-1.docker.io --apply-egress-mtu

Auto-add WireGuard peer endpoints as targets and apply WG MTU:
    sudo automtu --auto-pmtu-from-wg --apply-wg-mtu

Force WG MTU:
    sudo automtu --set-wg-mtu 1372 --apply-wg-mtu

Help:
    automtu --help


---

## 👤 Author

**Kevin Veen-Birkenbach**
[https://www.veen.world](https://www.veen.world)

