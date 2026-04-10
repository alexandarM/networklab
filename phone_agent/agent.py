"""
Usage (in Termux):
    python agent.py              # Normal run
    python agent.py --once       # Single collection cycle
    python agent.py --debug      # Verbose logging
    python agent.py --no-ml      # Skip ML inference
"""

import sys
import os
import time
import json
import logging
import argparse
import datetime
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from collectors import ping_monitor, http_monitor, net_stats, wifi_info
from inference.anomaly_detector import AnomalyDetector


def setup_logging(level: str, log_file: str):
    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    datefmt = "%H:%M:%S"
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
    )


logger = logging.getLogger("agent")


# cool banner idk
BANNER = r"""
  _   _      _   _____ ___ _   _ _  __
 | \ | | ___| |_|_   _|_ _| \ | | |/ /
 |  \| |/ _ \ __| | |  | ||  \| | ' /
 | |\  |  __/ |_  | |  | || |\  | . \
 |_| \_|\___|\__| |_| |___|_| \_|_|\_\
  NetworkLab Agent v1.0
  Device: {device}
  Server: {server}
"""


def collect_all_metrics() -> dict:
    # run all collectors
    logger.info("Starting metric collection ")
    t_start = time.time()

    # Ping latency
    logger.debug("  Collecting ping metrics")
    ping_data = ping_monitor.collect(
        targets=config.PING_TARGETS,
        count=config.PING_COUNT,
        timeout=config.PING_TIMEOUT,
    )

    # HTTP probes
    logger.debug("  Collecting HTTP metrics")
    http_data = http_monitor.collect(
        targets=config.HTTP_TARGETS,
        timeout=config.HTTP_TIMEOUT,
    )

    # Network interface stats
    logger.debug("  Collecting interface stats")
    net_data = net_stats.collect(dns_targets=config.DNS_TARGETS)

    # WiFi info
    logger.debug("  Collecting WiFi info")
    wifi_data = wifi_info.collect()

    # MErge all to dict
    metrics = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "device_id": config.DEVICE_ID,
        # Ping
        "latency_avg": ping_data.get("latency_avg"),
        "latency_min": ping_data.get("latency_min"),
        "latency_max": ping_data.get("latency_max"),
        "latency_std": ping_data.get("latency_std"),
        "packet_loss": ping_data.get("packet_loss"),
        "hosts_reachable": ping_data.get("hosts_reachable"),
        # HTTP
        "http_response_time": http_data.get("http_response_time"),
        "http_success_rate": http_data.get("http_success_rate"),
        # Network I/O
        "bytes_sent_rate": net_data.get("bytes_sent_rate"),
        "bytes_recv_rate": net_data.get("bytes_recv_rate"),
        "packets_sent_rate": net_data.get("packets_sent_rate"),
        "packets_recv_rate": net_data.get("packets_recv_rate"),
        "errors_in": net_data.get("errors_in"),
        "errors_out": net_data.get("errors_out"),
        "drops_in": net_data.get("drops_in"),
        "dns_time": net_data.get("dns_time"),
        "active_connections": net_data.get("active_connections"),
        # WiFi
        "wifi_ssid": wifi_data.get("wifi_ssid"),
        "wifi_signal": wifi_data.get("wifi_signal"),
        "wifi_signal_quality": wifi_data.get("wifi_signal_quality"),
        "wifi_link_speed": wifi_data.get("wifi_link_speed"),
        # Battery
        "battery_percentage": wifi_data.get("battery_percentage"),
        "battery_plugged": wifi_data.get("battery_plugged"),
    }

    elapsed = round((time.time() - t_start) * 1000)
    logger.info(f"Collection done in {elapsed}ms")

    return metrics


def run_inference(metrics: dict, detector: AnomalyDetector) -> dict:

    prediction = detector.predict(metrics)
    metrics["is_anomaly"] = int(prediction["is_anomaly"])
    metrics["anomaly_score"] = prediction["anomaly_score"]
    metrics["anomaly_confidence"] = prediction["confidence"]
    metrics["anomaly_reason"] = prediction["reason"]
    return metrics


def send_metrics(metrics: dict) -> bool:

    url = config.SERVER_URL.rstrip("/") + config.API_ENDPOINT
    try:
        resp = requests.post(
            url,
            json=metrics,
            timeout=10,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code == 200:
            logger.info(f"Metrics sent to : {url} [{resp.status_code}]")
            return True
        else:
            logger.warning(f"Server returned {resp.status_code}: {resp.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(
            f"Cannot reach server at {url}\n"
            "   Check:\n"
            "   1. Is the Flask server running on your laptop?\n"
            "   2. Are phone and laptop on the same WiFi?\n"
            "   3. Is SERVER_URL correct in config.py?"
        )
        return False
    except requests.exceptions.Timeout:
        logger.error("Request timed out — server may be overloaded")
        return False


def print_summary(metrics: dict):
    """Print a human-readable summary to stdout."""
    sep = "─" * 50
    print(f"\n{sep}")
    print(f"METRICS — {metrics['timestamp']}")
    print(sep)
    print(f"  Latency:      avg={metrics.get('latency_avg')}ms  "
          f"std={metrics.get('latency_std')}ms")
    print(f"  Packet Loss:  {metrics.get('packet_loss')}%")
    print(f"  HTTP Time:    {metrics.get('http_response_time')}ms")
    print(f"  DNS Time:     {metrics.get('dns_time')}ms")
    print(f"  Network I/O:  ↓{metrics.get('bytes_recv_rate', 0):.0f}B/s  "
          f"↑{metrics.get('bytes_sent_rate', 0):.0f}B/s")
    print(f"  WiFi Signal:  {metrics.get('wifi_signal')}dBm  "
          f"({metrics.get('wifi_signal_quality')}%)")
    print(f"  Battery:      {metrics.get('battery_percentage')}%  "
          f"plugged={metrics.get('battery_plugged')}")

    anomaly = metrics.get("is_anomaly", 0)
    score = metrics.get("anomaly_score", 0.0)
    reason = metrics.get("anomaly_reason", "")
    if anomaly:
        print(f"\nANOMALY DETECTED  score={score:.3f}")
        print(f"     {reason}")
    else:
        print(f"\nNetwork Normal    score={score:.3f}")
    print(sep)


def main():
    parser = argparse.ArgumentParser(description="NetworkLab Phone Agent")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-ml", action="store_true", help="Disable ML inference")
    parser.add_argument("--interval", type=int, default=config.SEND_INTERVAL,
                        help=f"Seconds between cycles (default: {config.SEND_INTERVAL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Collect metrics but do NOT send to server")
    args = parser.parse_args()

    log_level = "DEBUG" if args.debug else config.LOG_LEVEL
    setup_logging(log_level, config.LOG_FILE)

    print(BANNER.format(device=config.DEVICE_ID, server=config.SERVER_URL))

    # Load ml model
    detector = None
    if not args.no_ml:
        detector = AnomalyDetector(
            model_path=config.MODEL_PATH,
            scaler_path=config.SCALER_PATH,
            feature_names=config.FEATURE_NAMES,
        )

    cycle = 0
    while True:
        cycle += 1
        logger.info(f"═══ Cycle #{cycle} ═══")

        # collect
        metrics = collect_all_metrics()

        # INference
        if detector is not None:
            metrics = run_inference(metrics, detector)

        # Display
        print_summary(metrics)

        # Send
        if not args.dry_run:
            send_metrics(metrics)
        else:
            logger.info("Not sending to server")

        if args.once:
            logger.info("--once flag set — exiting after first cycle")
            break

        logger.info(f"Next cycle in {args.interval}s...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
