# NetworkLab — Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NETWORKLAB SYSTEM ARCHITECTURE                       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  📱 PHONE (Termux, non-rooted)                                      │    │
│  │                                                                     │    │
│  │  ┌─────────────────────┐   ┌──────────────────┐   ┌─────────────┐  │    │
│  │  │  Collector Layer    │   │  ML Inference    │   │  Agent      │  │    │
│  │  │                     │   │                  │   │  (agent.py) │  │    │
│  │  │  ping_monitor.py    │   │  anomaly_        │   │             │  │    │
│  │  │  (subprocess ping)  │   │  detector.py     │   │  Orchestr.  │  │    │
│  │  │                     │   │                  │   │  + sends    │  │    │
│  │  │  http_monitor.py    │──►│  Isolation       │──►│  metrics    │  │    │
│  │  │  (urllib probes)    │   │  Forest model    │   │  to server  │  │    │
│  │  │                     │   │  (model.pkl)     │   │             │  │    │
│  │  │  net_stats.py       │   │                  │   │             │  │    │
│  │  │  (psutil counters)  │   │  Runs fully      │   │  HTTP POST  │  │    │
│  │  │                     │   │  offline, no     │   │  /api/      │  │    │
│  │  │  wifi_info.py       │   │  internet needed │   │  metrics    │  │    │
│  │  │  (termux:api)       │   └──────────────────┘   └──────┬──────┘  │    │
│  │  └─────────────────────┘                                 │         │    │
│  └────────────────────────────────────────────────────────┬─┘─────────┘    │
│                                                           │                 │
│                              WiFi LAN (same network)      │                 │
│                                                           ▼                 │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  💻 LAPTOP (Linux Mint, VS Code)                                   │     │
│  │                                                                    │     │
│  │  ┌─────────────────┐   ┌───────────────────────────────────────┐   │     │
│  │  │  Flask Server   │   │  Dashboard (browser)                  │   │     │
│  │  │  (app.py)       │   │                                       │   │     │
│  │  │                 │   │  ┌─────────┐ ┌──────────┐ ┌────────┐  │   │     │
│  │  │  POST /metrics  │   │  │ Latency │ │  I/O     │ │Anomaly │  │   │     │
│  │  │  ↓              │──►│  │ Charts  │ │ Charts   │ │Alerts  │  │   │     │
│  │  │  SQLite DB      │   │  └─────────┘ └──────────┘ └────────┘  │   │     │
│  │  │  (metrics.db)   │   │                                       │   │     │
│  │  │  ↓              │   │  Real-time via WebSocket               │   │     │
│  │  │  WebSocket emit │──►│  (Socket.IO)                           │   │     │
│  │  │                 │   │                                       │   │     │
│  │  │  REST API:      │   └───────────────────────────────────────┘   │     │
│  │  │  GET /api/data  │                                                │     │
│  │  │  GET /api/stats │   ┌───────────────────────────────────────┐   │     │
│  │  │  GET /api/anom  │   │  ML Training Pipeline                 │   │     │
│  │  └─────────────────┘   │                                       │   │     │
│  │                        │  generate_data.py → training_data.csv │   │     │
│  │                        │  train.py → model.pkl + scaler.pkl    │   │     │
│  │                        │  evaluate.py → plots + report         │   │     │
│  │                        └───────────────────────────────────────┘   │     │
│  │                                                                    │     │
│  │  Model export: model.pkl → phone_agent/inference/                  │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Collection** (every 30s on phone)
   - 5× ping to 3 DNS servers → latency stats
   - HTTP HEAD to 3 URLs → response times
   - psutil net_io_counters diff → bytes/packets/s
   - termux-wifi-connectioninfo → RSSI, SSID
   - socket.getaddrinfo × 3 → DNS resolution time

2. **Inference** (on phone, offline)
   - Features extracted from raw metrics
   - StandardScaler normalization applied
   - IsolationForest.predict() → normal / anomaly
   - IsolationForest.decision_function() → score
   - Anomaly reason generated by rule heuristics

3. **Transmission** (phone → laptop)
   - HTTP POST /api/metrics with full JSON payload
   - Payload includes raw metrics + ML prediction
   - Timeout: 10s, retry on failure

4. **Storage** (laptop SQLite)
   - All fields stored with WAL mode (concurrent read/write)
   - Indexed on timestamp, device_id, is_anomaly

5. **Visualization** (browser)
   - On connect: last 10 rows served via WebSocket
   - New data: pushed via `new_metrics` socket event
   - Anomaly: `anomaly_alert` event → toast notification
   - Fallback: polling every 10s if WebSocket fails

## Why No Root Is Needed

| Capability | Linux kernel default | Notes |
|---|---|---|
| `ping` via subprocess | ✅ Allowed | Uses setuid bit on `/bin/ping` |
| `psutil.net_io_counters()` | ✅ Allowed | Reads `/proc/net/dev` |
| `socket.getaddrinfo()` | ✅ Allowed | Standard DNS resolve |
| `urllib.request.urlopen()` | ✅ Allowed | HTTP client |
| `termux-wifi-connectioninfo` | ✅ Allowed | Termux:API app |
| `tcpdump` / raw sockets | ❌ Needs root | Not used — we use psutil instead |
| Packet injection | ❌ Needs root | Not used |

## ML Model Details

**Algorithm:** Isolation Forest (sklearn 1.3.x)
- Unsupervised anomaly detection
- Works by isolating points using random binary splits
- Anomalous points are isolated with fewer splits
- `n_estimators=200` for stability

**Feature Engineering:** None beyond StandardScaler normalization
- All raw numeric features fed directly

**Inference Time (Snapdragon 425):**
- Model load: ~200ms (once at startup)
- Per-sample inference: <5ms
- Memory footprint: ~8MB

**Deployment:**
- Model serialized with `joblib.dump()` (~1MB pickle)
- `joblib.load()` on phone, inference in-process
- No network needed for inference

## API Reference

### POST /api/metrics
Receives a metrics payload from the phone agent.

```json
{
  "timestamp": "2025-01-15T14:30:00Z",
  "device_id": "huawei-y6-2018",
  "latency_avg": 34.5,
  "latency_std": 4.2,
  "packet_loss": 0.0,
  "http_response_time": 312.4,
  "bytes_recv_rate": 15420,
  "bytes_sent_rate": 2048,
  "dns_time": 45.2,
  "wifi_signal": -58,
  "is_anomaly": 0,
  "anomaly_score": 0.123,
  "anomaly_reason": "Network conditions normal"
}
```

### GET /api/data?limit=100
Returns last N metric rows (oldest first, for chart ordering).

### GET /api/stats
Returns aggregate statistics:
```json
{
  "total_samples": 1234,
  "avg_latency_ms": 38.2,
  "avg_packet_loss_pct": 0.3,
  "total_anomalies": 12,
  "last_seen": "2025-01-15T14:30:00Z"
}
```

### GET /api/anomalies?limit=20
Returns most recent anomaly events.

### WebSocket Events
- `connect` → server sends `history` with last 10 rows
- `new_metrics` → pushed on every new data point
- `anomaly_alert` → pushed when anomaly detected
