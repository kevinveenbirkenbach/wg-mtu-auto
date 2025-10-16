# wg-mtu-auto — Practical Guide

This guide shows **how to *determine* and *set*** correct MTU values:

* **with WireGuard** (`wg0`), and
* **without WireGuard** (just your egress interface like `eth0`/`wlan0`).

The tool can:

* auto-detect your **egress interface**
* optionally **probe Path MTU (PMTU)** to one or more remote targets
* compute a safe **WireGuard MTU** (`effective_mtu - 80` by default)
* **apply** MTU to `wg0` and/or your egress interface

---

## TL;DR recipes

### 1) Just compute & set WireGuard MTU (no PMTU probing)

```bash
sudo automtu
# Equivalent from repo:
# sudo python3 main.py
```

* Detects egress (e.g., `eth0`), reads its MTU (e.g., 1500)
* Computes `wg0` MTU = `egress_mtu - 80` (min clamp 1280)
* Applies to `wg0` (if present)

Dry-run:

```bash
automtu --dry-run
```

---

### 2) Compute & apply MTU on *egress* (non-WireGuard)

Useful if you want the *link itself* (e.g., `eth0`) to use the discovered PMTU.

```bash
sudo automtu --pmtu-target 1.1.1.1 --apply-egress-mtu
```

* Probes PMTU to `1.1.1.1`, applies that result to `eth0`
* Also computes a matching WireGuard MTU (`PMTU - 80`) and sets `wg0` (if present)

> If the selected egress is `wg0`, egress application is **skipped** on purpose.

---

### 3) With WireGuard peers: auto-add endpoints as PMTU targets

```bash
sudo automtu --auto-pmtu-from-wg
```

* Reads `wg0` peer endpoints (`wg show ...` / `wg showconf`)
* Probes PMTU to those endpoints
* Picks an **effective PMTU** (policy = `min` by default)
* Applies **`wg0` MTU = effective PMTU − 80**

Add extra targets & choose different policy:

```bash
sudo automtu --auto-pmtu-from-wg \
  --pmtu-target 46.4.224.77,1.1.1.1 \
  --pmtu-policy median
```

---

### 4) Force a specific WireGuard MTU (override)

```bash
sudo automtu --set-wg-mtu 1372
```

* Skips the computed value and **forces** 1372 on `wg0` (clamped to ≥1280)

---

## When to use which approach?

* **You just use WireGuard** and want a safe default:
  `sudo automtu` → picks `wg0 = egress_mtu - 80` (e.g., `1500 - 80 = 1420`).

* **You suspect smaller upstream MTU** (PPPoE/ISP/VPN/“somewhere in the path”):
  Use PMTU probing towards stable targets (your WG peer, DNS resolvers):

  ```bash
  sudo automtu --pmtu-target 46.4.224.77 --pmtu-target 1.1.1.1
  ```

  Then optionally apply the PMTU to your egress:

  ```bash
  sudo automtu --pmtu-target 46.4.224.77 --apply-egress-mtu
  ```

* **You have WireGuard peers** and want the tool to discover them automatically:
  `sudo automtu --auto-pmtu-from-wg`
  (You can still add manual targets and change policy.)

---

## How it works (short)

1. **Egress detection**
   Reads default routes and picks a non-VPN interface (e.g., `eth0`).
   If you want to prefer `wg0` when the default route already uses it:

   ```bash
   sudo automtu --prefer-wg-egress --wg-if wg0
   ```

2. **PMTU probing (optional)**
   Uses `ping -M do` (DF set) with a quick binary search to find the largest unfragmented payload for each target.
   From the successful results, selects an **effective PMTU** using a policy:

   * `--pmtu-policy min` (default, safest)
   * `--pmtu-policy median`
   * `--pmtu-policy max`

3. **WireGuard MTU calculation**
   `wg_mtu = max(wg_min, effective_mtu - wg_overhead)`
   Defaults: `wg_min=1280`, `wg_overhead=80`.

4. **Apply**

   * If `--apply-egress-mtu` is set, apply **effective PMTU** to the egress (unless egress is `wg0`).
   * Apply **WireGuard MTU** to `wg0` (or the iface passed via `--wg-if`).
   * If `--set-wg-mtu X` is given, it **overrides** the computed value.

---

## Examples (copy & paste)

### A) Quick WireGuard tuning with peer awareness

```bash
sudo automtu --auto-pmtu-from-wg
```

### B) Manual targets, conservative (min) policy

```bash
sudo automtu --pmtu-target 46.4.224.77 --pmtu-target 1.1.1.1
```

### C) Apply PMTU on egress + set matching wg0

```bash
sudo automtu --pmtu-target 1.1.1.1 --apply-egress-mtu
```

### D) Prefer WireGuard as egress (if default route uses WG)

```bash
sudo automtu --prefer-wg-egress --wg-if wg0 --auto-pmtu-from-wg
```

### E) Force a specific wg0 MTU

```bash
sudo automtu --set-wg-mtu 1372
```

### F) Dry-run any of the above

```bash
automtu --dry-run --auto-pmtu-from-wg --pmtu-target 1.1.1.1
```

---

## Persisting the value in WireGuard

Runtime changes are **not** permanent. To persist:

* Either let your automation run this tool before/after `wg-quick up wg0`, **or**
* Add a fixed value in your `wg0` config (`/etc/wireguard/wg0.conf`):

  ```ini
  [Interface]
  MTU = 1372
  ```

  > Static MTU is fine if the path is stable. If your route/ISP changes, prefer running this tool.

---

## Notes & Troubleshooting

* If **all PMTU probes fail**, the tool prints a warning and falls back to the egress MTU (e.g., `1500`) and sets `wg0 = egress - 80`.
  Some networks block ICMP “fragmentation needed”; use multiple targets or rely on egress-only.
* You can **override defaults** via flags or environment:

  * `WG_IF=wg0 WG_OVERHEAD=80 WG_MIN=1280 automtu ...`
* The tool **deduplicates targets** and understands IPv4/IPv6 endpoints (e.g., `2a01:...`).
