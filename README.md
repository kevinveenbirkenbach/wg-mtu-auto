# wg-mtu-auto

Automatically detect the optimal WireGuard MTU by analyzing your local egress interface and optionally probing the Path MTU (PMTU) to one or more remote hosts.  
The tool ensures stable and efficient VPN connections by preventing fragmentation and latency caused by mismatched MTU settings.

---

## ✨ Features

- **Automatic Egress Detection** — Finds your primary internet interface automatically.  
- **WireGuard MTU Calculation** — Computes `wg0` MTU based on egress MTU minus overhead (default 80 bytes).  
- **Optional Path MTU Probing** — Uses ICMP “Don’t Fragment” (`ping -M do`) to find the real usable MTU across network paths.  
- **Multi-Target PMTU Support** — Test multiple remote hosts and choose an effective value via policy (`min`, `median`, `max`).  
- **Dry-Run Mode** — Simulate changes without applying them.  
- **Safe for Automation** — Integrates well with WireGuard systemd services or Ansible setups.

---

## 🚀 Installation

### Option 1 — Using [pkgmgr](https://github.com/kevinveenbirkenbach/package-manager)

If you use Kevin Veen-Birkenbach’s package manager (`pkgmgr`):

```bash
pkgmgr install automtu
````

This will automatically fetch and install `wg-mtu-auto` system-wide.

### Option 2 — Run directly from source

Clone this repository and execute the script manually:

```bash
git clone https://github.com/kevinveenbirkenbach/wg-mtu-auto.git
cd wg-mtu-auto
sudo python3 main.py --help
```

---

## 🧩 Usage Examples

### Basic detection (no PMTU)

```bash
sudo automtu
```

### Specify egress interface and force MTU

```bash
sudo automtu --egress-if eth0 --force-egress-mtu 1452
```

### Probe multiple PMTU targets (safe policy: `min`)

```bash
sudo automtu --pmtu-target 46.4.224.77 --pmtu-target 2a01:4f8:2201:4695::2
```

### Choose median or max policy

```bash
sudo automtu --pmtu-target 46.4.224.77,1.1.1.1 --pmtu-policy median
sudo automtu --pmtu-target 46.4.224.77,1.1.1.1 --pmtu-policy max
```

### Dry-run (no system changes)

```bash
automtu --dry-run
```

---

## 🧪 Development

Run unit tests using:

```bash
make test
```

To see installation guidance (does not install anything):

```bash
make install
```

---

## 👤 Author

**Kevin Veen-Birkenbach**
[https://www.veen.world](https://www.veen.world)

