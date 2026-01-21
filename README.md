# 🚀 automtu — Automatic Path MTU Detection for Linux & WireGuard

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-blue?logo=github)](https://github.com/sponsors/kevinveenbirkenbach) [![Patreon](https://img.shields.io/badge/Support-Patreon-orange?logo=patreon)](https://www.patreon.com/c/kevinveenbirkenbach) [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20Coffee-Funding-yellow?logo=buymeacoffee)](https://buymeacoffee.com/kevinveenbirkenbach) [![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://s.veen.world/paypaldonate)

**automtu** is a small but powerful CLI tool that automatically detects your egress interface, probes the Path MTU (PMTU), computes a safe MTU for WireGuard, and optionally applies it — or simply prints it for automation tools like **Ansible**.

Perfect for:

* Docker-in-Docker (DiD)
* WireGuard tunnels
* Cloud VPS setups
* CI runners
* NAT / overlay networks

No more TLS handshake timeouts. No more guessing MTU values.
Just reliable networking. ✅

---

## ✨ Features

* 🔍 Auto-detects your egress interface (`eth0`, `ens3`, etc.)
* 📡 Probes Path MTU using DF-ping (`ping -M do`)
* 🧮 Computes a safe WireGuard MTU (`effective_mtu - overhead`)
* 🔐 Supports WireGuard peer auto-discovery
* ⚙️ Optional automatic MTU application
* 🤖 Machine-readable output for Ansible / CI
* 📦 JSON output for automation pipelines
* 🧪 Fully unit-tested

---

## 📦 Installation

### Option 1 — Install via pip (recommended)

```bash
pip install automtu
```

or editable mode for development:

```bash
pip install -e .
```

---

### Option 2 — Local installation from source

```bash
git clone https://github.com/kevinveenbirkenbach/automtu.git
cd automtu
pip install -e .
```

Now the `automtu` command is available system-wide.

---

## 🚦 Usage

### 🔍 Show detected MTU (no changes)

```bash
automtu --dry-run
```

---

### 📡 Probe PMTU and apply to egress interface

```bash
sudo automtu --pmtu-target 1.1.1.1 --apply-egress-mtu
```

---

### 🔐 Auto-detect WireGuard peers and apply WG MTU

```bash
sudo automtu --auto-pmtu-from-wg --apply-wg-mtu
```

---

### ⚡ Prefer WireGuard as egress if default route uses wg0

```bash
sudo automtu --prefer-wg-egress --auto-pmtu-from-wg --apply-wg-mtu
```

---

### 🧮 Print only the MTU number (for Ansible & scripts)

```bash
automtu --print-mtu effective
```

Output:

```
1452
```

Perfect for:

```yaml
- name: Detect MTU
  command: automtu --print-mtu effective
  register: mtu

- name: Apply MTU
  command: ip link set mtu {{ mtu.stdout }} dev eth0
```

---

### 📤 JSON output (CI / automation)

```bash
automtu --print-json
```

Output:

```json
{
  "egress": { "iface": "eth0", "base_mtu": 1500, "effective_mtu": 1452 },
  "pmtu": { "policy": "min", "chosen": 1452 },
  "wg": { "iface": "wg0", "mtu": 1372 },
  "dry_run": true
}
```

---

## 🛡 Notes

* Applying MTU requires root (`sudo`) unless `--dry-run` is used
* PMTU probing may fail if ICMP is blocked — fallback is automatic
* MTU changes are runtime-only (not persistent across reboot)

---

## 🧠 Why automtu?

Because networking stacks are layered, tunneled, NATed and virtualized.
Path MTU matters — especially for:

* Docker-in-Docker
* VPN tunnels
* Cloud providers
* Kubernetes nodes
* CI runners

automtu removes guesswork and prevents hard-to-debug TLS timeouts.

---

## 👤 Author

**Kevin Veen-Birkenbach**
🌍 [https://www.iveen.world](https://www.iveen.world)

Open Source, Automation, Infrastructure & Digital Sovereignty.

---

## ❤️ Support

If automtu helped you, consider supporting the project:

* ⭐ Star on GitHub
* ☕ Buy Me a Coffee
* 💙 GitHub Sponsors

---

Happy networking! 🌐✨
