# measures http response time and returns :
# http_response_time (avg ms), http_success_rate, per_url breakdown


import time
import logging
import statistics
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)


def probe_url(url: str, timeout: int = 5) -> dict:
    # perform single http head/get and measure resposne time 

    result = {
        "url": url,
        "status_code": None,
        "response_time_ms": None,
        "success": False,
        "error": None,
    }

    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "NetworkLab-Agent/1.0"},
        )
        t_start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = (time.perf_counter() - t_start) * 1000  # → ms
            result["status_code"] = resp.status
            result["response_time_ms"] = round(elapsed, 2)
            result["success"] = True

        logger.debug(f"HTTP {url}: {result['status_code']} in {elapsed:.1f}ms")

    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        result["success"] = e.code < 500
        result["error"] = f"HTTP {e.code}"
    except urllib.error.URLError as e:
        result["error"] = str(e.reason)
        logger.warning(f"HTTP probe failed for {url}: {e.reason}")
    except TimeoutError:
        result["error"] = "timeout"
        logger.warning(f"HTTP timeout for {url}")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"HTTP error for {url}: {e}")

    return result


def collect(targets: list, timeout: int = 5) -> dict:
    
    results = []
    response_times = []
    successes = 0

    for url in targets:
        r = probe_url(url, timeout=timeout)
        results.append(r)
        if r["success"] and r["response_time_ms"] is not None:
            response_times.append(r["response_time_ms"])
            successes += 1

    aggregated = {
        "http_response_time": (
            round(statistics.mean(response_times), 2) if response_times else None
        ),
        "http_response_time_min": (
            round(min(response_times), 2) if response_times else None
        ),
        "http_response_time_max": (
            round(max(response_times), 2) if response_times else None
        ),
        "http_success_rate": round(successes / len(targets) * 100, 1) if targets else 0,
        "http_targets_up": successes,
        "http_targets_total": len(targets),
        "per_url": results,
    }

    return aggregated
