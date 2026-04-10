import subprocess
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _run_termux_api(command: list, timeout: int = 5) -> Optional[dict]:

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        logger.debug(f"Termux:API unavailable ({command[0]}): {e}")
        return None


def get_wifi_info() -> dict:

    data = _run_termux_api(["termux-wifi-connectioninfo"])

    if data is None:
        return {
            "wifi_ssid": None,
            "wifi_bssid": None,
            "wifi_signal": None,
            "wifi_link_speed": None,
            "wifi_frequency": None,
            "wifi_ip": None,
            "wifi_available": False,
        }

    # get rssi (dbm)
    signal = data.get("rssi")

    # Rssi to quality 
    quality = None
    if signal is not None:
        quality = max(0, min(100, int((signal + 90) / 60 * 100)))

    return {
        "wifi_ssid": data.get("ssid", "").strip('"'),
        "wifi_bssid": data.get("bssid"),
        "wifi_signal": signal,          # dBm (raw RSSI)
        "wifi_signal_quality": quality, # 0–100%
        "wifi_link_speed": data.get("link_speed_mbps"),
        "wifi_frequency": data.get("frequency_mhz"),
        "wifi_ip": data.get("ip"),
        "wifi_available": True,
    }


def get_battery_info() -> dict:

    data = _run_termux_api(["termux-battery-status"])

    if data is None:
        return {"battery_percentage": None, "battery_plugged": None}

    return {
        "battery_percentage": data.get("percentage"),
        "battery_plugged": data.get("plugged") != "UNPLUGGED",
        "battery_status": data.get("status"),
        "battery_temperature": data.get("temperature"),
    }


def collect() -> dict:

    wifi = get_wifi_info()
    battery = get_battery_info()
    return {**wifi, **battery}
