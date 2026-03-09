# server/database.py
"""
SQLite database layer for NetworkLab server.
Handles schema creation, inserts, and query helpers.
"""

import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "metrics.db")


def init_db():
    """Create the database and tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS metrics (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT NOT NULL,
                device_id       TEXT DEFAULT 'unknown',

                -- Ping
                latency_avg     REAL,
                latency_min     REAL,
                latency_max     REAL,
                latency_std     REAL,
                packet_loss     REAL,
                hosts_reachable INTEGER,

                -- HTTP
                http_response_time  REAL,
                http_success_rate   REAL,

                -- Network I/O
                bytes_sent_rate     REAL,
                bytes_recv_rate     REAL,
                packets_sent_rate   REAL,
                packets_recv_rate   REAL,
                errors_in           INTEGER,
                errors_out          INTEGER,
                drops_in            INTEGER,
                dns_time            REAL,
                active_connections  INTEGER,

                -- WiFi
                wifi_ssid           TEXT,
                wifi_signal         INTEGER,
                wifi_signal_quality INTEGER,
                wifi_link_speed     INTEGER,

                -- Battery
                battery_percentage  INTEGER,
                battery_plugged     INTEGER,

                -- ML inference
                is_anomaly          INTEGER DEFAULT 0,
                anomaly_score       REAL DEFAULT 0.0,
                anomaly_confidence  TEXT,
                anomaly_reason      TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
                ON metrics (timestamp DESC);

            CREATE INDEX IF NOT EXISTS idx_metrics_device
                ON metrics (device_id);

            CREATE INDEX IF NOT EXISTS idx_metrics_anomaly
                ON metrics (is_anomaly);
        """)
    logger.info(f"Database ready: {DB_PATH}")


@contextmanager
def get_conn():
    """Context manager for SQLite connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_metrics(data: dict) -> Optional[int]:
    """Insert a metrics dict into the database. Returns new row id."""
    fields = [
        "timestamp", "device_id",
        "latency_avg", "latency_min", "latency_max", "latency_std", "packet_loss",
        "hosts_reachable", "http_response_time", "http_success_rate",
        "bytes_sent_rate", "bytes_recv_rate", "packets_sent_rate", "packets_recv_rate",
        "errors_in", "errors_out", "drops_in", "dns_time", "active_connections",
        "wifi_ssid", "wifi_signal", "wifi_signal_quality", "wifi_link_speed",
        "battery_percentage", "battery_plugged",
        "is_anomaly", "anomaly_score", "anomaly_confidence", "anomaly_reason",
    ]
    placeholders = ", ".join(["?"] * len(fields))
    col_names = ", ".join(fields)
    values = [data.get(f) for f in fields]

    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO metrics ({col_names}) VALUES ({placeholders})",
                values,
            )
            return cur.lastrowid
    except Exception as e:
        logger.error(f"DB insert failed: {e}")
        return None


def get_recent_metrics(limit: int = 100, device_id: str = None) -> list:
    """Return the most recent metric rows as list of dicts."""
    query = "SELECT * FROM metrics"
    params = []
    if device_id:
        query += " WHERE device_id = ?"
        params.append(device_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in reversed(rows)]  # Oldest first for charts


def get_summary_stats(device_id: str = None) -> dict:
    """Return aggregate statistics for the summary panel."""
    where = "WHERE device_id = ?" if device_id else ""
    params = [device_id] if device_id else []

    query = f"""
        SELECT
            COUNT(*) as total_samples,
            ROUND(AVG(latency_avg), 2)       as avg_latency_ms,
            ROUND(MIN(latency_avg), 2)       as min_latency_ms,
            ROUND(MAX(latency_avg), 2)       as max_latency_ms,
            ROUND(AVG(packet_loss), 2)       as avg_packet_loss_pct,
            ROUND(AVG(http_response_time), 0) as avg_http_ms,
            ROUND(AVG(dns_time), 0)          as avg_dns_ms,
            ROUND(AVG(wifi_signal), 1)       as avg_wifi_signal,
            ROUND(AVG(bytes_recv_rate), 0)   as avg_bytes_recv_rate,
            ROUND(AVG(bytes_sent_rate), 0)   as avg_bytes_sent_rate,
            SUM(is_anomaly)                  as total_anomalies,
            MAX(timestamp)                   as last_seen
        FROM metrics {where}
    """

    with get_conn() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else {}


def get_anomaly_history(limit: int = 20) -> list:
    """Return the most recent anomalous events."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT timestamp, device_id, latency_avg, packet_loss,
                      anomaly_score, anomaly_reason
               FROM metrics
               WHERE is_anomaly = 1
               ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
