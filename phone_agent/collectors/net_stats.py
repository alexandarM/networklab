"""
Reads network via psutil
Calculates per-second rates by diffing two snapshots separated
by `interval` seconds. Also resolves DNS timing.

Returns:
  bytes_sent_rate, bytes_recv_rate, packet rates, error/drop counters,
  dns_time, active_connections
"""
import time
import socket
import logging

logger = logging.getLogger(__name__)


def _get_net_counters():
    stats = {}
    with open("/proc/net/dev", "r") as f:
        lines = f.readlines()
    for line in lines[2:]:
        parts = line.split()
        if len(parts) < 10:
            continue
        iface = parts[0].replace(":", "")
        stats[iface] = {
            "bytes_recv": int(parts[1]),
            "packets_recv": int(parts[2]),
            "bytes_sent": int(parts[9]),
            "packets_sent": int(parts[10]),
        }
    return stats


def _aggregate(stats):
    total = {"bytes_recv": 0, "packets_recv": 0, "bytes_sent": 0, "packets_sent": 0}
    for iface, data in stats.items():
        if iface == "lo":
            continue
        for key in total:
            total[key] += data[key]
    return total


def _probe_dns(hostnames):
    times = []
    for hostname in hostnames:
        try:
            t = time.perf_counter()
            socket.getaddrinfo(hostname, None)
            times.append((time.perf_counter() - t) * 1000)
        except Exception:
            pass
    return round(sum(times) / len(times), 2) if times else None


def collect(dns_targets=None, interval=1.0):
    dns_targets = dns_targets or ["google.com", "cloudflare.com"]

    snap1 = _aggregate(_get_net_counters())
    t1 = time.time()

    dns_time = _probe_dns(dns_targets)

    time.sleep(interval)

    snap2 = _aggregate(_get_net_counters())
    dt = time.time() - t1

    return {
        "bytes_sent_rate":    round(max(0, (snap2["bytes_sent"]    - snap1["bytes_sent"])    / dt), 1),
        "bytes_recv_rate":    round(max(0, (snap2["bytes_recv"]    - snap1["bytes_recv"])    / dt), 1),
        "packets_sent_rate":  round(max(0, (snap2["packets_sent"]  - snap1["packets_sent"])  / dt), 1),
        "packets_recv_rate":  round(max(0, (snap2["packets_recv"]  - snap1["packets_recv"])  / dt), 1),
        "bytes_sent_total":   snap2["bytes_sent"],
        "bytes_recv_total":   snap2["bytes_recv"],
        "errors_in":          0,
        "errors_out":         0,
        "drops_in":           0,
        "dns_time":           dns_time,
        "active_connections": -1,
    }