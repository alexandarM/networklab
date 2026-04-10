import subprocess
import re
import statistics
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def ping_host(host: str, count: int = 5, timeout: int = 3) -> dict:

    result = {
        "host": host,
        "sent": count,
        "received": 0,
        "packet_loss": 100.0,
        "latency_min": None,
        "latency_avg": None,
        "latency_max": None,
        "latency_std": None,
        "error": None,
    }

    try:
        cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout * count + 5,
        )
        stdout = proc.stdout

        # received packets
        rx_match = re.search(r"(\d+) received", stdout)
        if rx_match:
            received = int(rx_match.group(1))
            result["received"] = received
            result["packet_loss"] = round((count - received) / count * 100, 1)

        # Parse rtt stats line: min/avg/max/mdev
        rtt_match = re.search(
            r"rtt min/avg/max/mdev = "
            r"([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)",
            stdout,
        )
        if rtt_match:
            result["latency_min"] = float(rtt_match.group(1))
            result["latency_avg"] = float(rtt_match.group(2))
            result["latency_max"] = float(rtt_match.group(3))
            result["latency_std"] = float(rtt_match.group(4))

        logger.debug(
            f"Ping {host}: avg={result['latency_avg']}ms "
            f"loss={result['packet_loss']}%"
        )

    except subprocess.TimeoutExpired:
        result["error"] = "timeout"
        logger.warning(f"Ping timeout for {host}")
    except FileNotFoundError:
        result["error"] = "ping_not_found"
        logger.error("ping command not found — install iputils: pkg install iputils")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Ping error for {host}: {e}")

    return result


def collect(targets: list, count: int = 5, timeout: int = 3) -> dict:

    results = []
    all_avgs = []
    all_losses = []
    all_stds = []
    all_mins = []
    all_maxs = []

    for host in targets:
        r = ping_host(host, count=count, timeout=timeout)
        results.append(r)
        if r["latency_avg"] is not None:
            all_avgs.append(r["latency_avg"])
            all_stds.append(r["latency_std"])
            all_mins.append(r["latency_min"])
            all_maxs.append(r["latency_max"])
        if r["packet_loss"] is not None:
            all_losses.append(r["packet_loss"])

    # all hosts
    aggregated = {
        "latency_avg": round(statistics.mean(all_avgs), 2) if all_avgs else None,
        "latency_min": round(min(all_mins), 2) if all_mins else None,
        "latency_max": round(max(all_maxs), 2) if all_maxs else None,
        "latency_std": round(statistics.mean(all_stds), 2) if all_stds else None,
        "packet_loss": round(statistics.mean(all_losses), 1) if all_losses else 100.0,
        "hosts_reachable": len(all_avgs),
        "hosts_total": len(targets),
        "per_host": results,
    }

    return aggregated
