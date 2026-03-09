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
import psutil
from typing import Optional

logger = logging.getLogger(__name__)

# Store previous snapshot for rate calculation
_prev_snapshot: Optional[dict] = None
_prev_time: Optional[float] = None


def _get_net_counters() -> dict:
    #Read aggregate network I/O counters across all interfaces
    counters = psutil.net_io_counters()
    return {
        "bytes_sent": counters.bytes_sent,
        "bytes_recv": counters.bytes_recv,
        "packets_sent": counters.packets_sent,
        "packets_recv": counters.packets_recv,
        "errin": counters.errin,
        "errout": counters.errout,
        "dropin": counters.dropin,
        "dropout": counters.dropout,
    }


def _probe_dns(hostnames: list, dns_server: str = "8.8.8.8") -> float:
    # measure average dns resposne time
    times = []
    for hostname in hostnames:
        try:
            t_start = time.perf_counter()
            socket.getaddrinfo(hostname, None)
            elapsed = (time.perf_counter() - t_start) * 1000
            times.append(elapsed)
        except Exception as e:
            logger.debug(f"DNS probe failed for {hostname}: {e}")

    return round(sum(times) / len(times), 2) if times else None


def _count_active_connections() -> int:
    # count ESTABLISHED TCP connections
    try:
        conns = psutil.net_connections(kind="tcp")
        return sum(1 for c in conns if c.status == "ESTABLISHED")
    except (psutil.AccessDenied, PermissionError):
        # Some kernels restrict this without root
        return -1


def collect(dns_targets: list = None, interval: float = 1.0) -> dict:

    global _prev_snapshot, _prev_time

    dns_targets = dns_targets or ["google.com", "cloudflare.com"]

    # Snapshot 1
    snap1 = _get_net_counters()
    t1 = time.time()

    dns_time = _probe_dns(dns_targets)

    # Snapshot 2 
    time.sleep(interval)
    snap2 = _get_net_counters()
    t2 = time.time()
    dt = t2 - t1  # time

    # Compute rates (bytes/sec)
    bytes_sent_rate = round((snap2["bytes_sent"] - snap1["bytes_sent"]) / dt, 1)
    bytes_recv_rate = round((snap2["bytes_recv"] - snap1["bytes_recv"]) / dt, 1)
    pkt_sent_rate = round((snap2["packets_sent"] - snap1["packets_sent"]) / dt, 1)
    pkt_recv_rate = round((snap2["packets_recv"] - snap1["packets_recv"]) / dt, 1)

    active_conns = _count_active_connections()

    result = {
        # Rates (per second)
        "bytes_sent_rate": max(0, bytes_sent_rate),
        "bytes_recv_rate": max(0, bytes_recv_rate),
        "packets_sent_rate": max(0, pkt_sent_rate),
        "packets_recv_rate": max(0, pkt_recv_rate),
        
        "bytes_sent_total": snap2["bytes_sent"],
        "bytes_recv_total": snap2["bytes_recv"],

        "errors_in": snap2["errin"],
        "errors_out": snap2["errout"],
        "drops_in": snap2["dropin"],
        "drops_out": snap2["dropout"],

        "dns_time": dns_time,

        "active_connections": active_conns,
    }

    logger.debug(
        f"NetStats: ↓{bytes_recv_rate:.0f}B/s ↑{bytes_sent_rate:.0f}B/s "
        f"DNS={dns_time}ms conns={active_conns}"
    )

    return result
