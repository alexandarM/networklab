# 📡 NetworkLab — Phone-Powered Network Intelligence System

> A real-world network monitoring and ML inference pipeline running on an Android phone (Termux) + Linux laptop — no root required.

![Architecture](docs/screenshots/architecture.png)

## 🧠 What This Project Does

A **non-rooted Android phone** (Huawei Y6 2018) running **Termux** acts as a network intelligence agent:

- Continuously **monitors network health** (latency, packet loss, HTTP response times, DNS speed, WiFi signal, interface I/O stats)
- Runs a **lightweight ML model locally** (Isolation Forest anomaly detection) for edge inference
- Streams metrics to a **Flask web server** on a laptop via REST API
- Server stores data in **SQLite** and serves a **real-time dashboard** with live charts
- ML model is **trained on the laptop** and deployed back to the phone

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE OVERVIEW                        │
│                                                                 │
│  📱 PHONE (Termux - No Root)          💻 LAPTOP (Linux Mint)    │
│  ┌─────────────────────────┐          ┌───────────────────────┐ │
│  │  Network Collectors     │          │  Flask Web Server     │ │
│  │  ├─ ping_monitor.py     │  HTTP    │  ├─ REST API          │ │
│  │  ├─ http_monitor.py     │ ──────►  │  ├─ SQLite DB         │ │
│  │  ├─ net_stats.py        │  POST    │  └─ WebSocket         │ │
│  │  └─ wifi_info.py        │          └───────────┬───────────┘ │
│  │                         │                      │             │
│  │  ML Inference           │  model.pkl           │             │
│  │  └─ anomaly_detector.py │ ◄────────────────────┤             │
│  │      (Isolation Forest) │                      │             │
│  └─────────────────────────┘               ┌──────▼──────────┐  │
│                                            │   Dashboard     │  │
│                                            │  (Chart.js +    │  │
│                                            │   WebSocket)    │  │
│                                            └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Phone Agent | Python 3, psutil, requests, scikit-learn |
| Network Probes | ping, urllib, socket, Termux:API |
| ML Model | scikit-learn (Isolation Forest) |
| Web Server | Flask, Flask-SocketIO |
| Database | SQLite3 |
| Dashboard | HTML5, Chart.js, Socket.IO JS |
| Platform | Android (Termux) + Linux Mint |

## 📁 Project Structure

```
network-lab/
├── phone_agent/          # 📱 Everything that runs on the phone
│   ├── setup.sh          #    One-command Termux setup
│   ├── agent.py          #    Main monitoring agent
│   ├── config.py         #    Configuration (server IP, targets)
│   ├── collectors/
│   │   ├── ping_monitor.py   # ICMP latency via subprocess ping
│   │   ├── http_monitor.py   # HTTP response time probes
│   │   ├── net_stats.py      # Interface I/O via psutil
│   │   └── wifi_info.py      # WiFi info via Termux:API
│   └── inference/
│       └── anomaly_detector.py  # Edge ML inference
│
├── server/               # 💻 Runs on the laptop
│   ├── app.py            #    Flask + SocketIO server
│   ├── database.py       #    SQLite helpers
│   ├── templates/
│   │   └── dashboard.html
│   └── static/
│       ├── css/style.css
│       └── js/dashboard.js
│
├── ml/                   # 🤖 Model training (on laptop)
│   ├── generate_sample_data.py  # Bootstrap initial training data
│   ├── train.py                 # Train Isolation Forest
│   ├── evaluate.py              # Model evaluation + plots
│   └── models/                  # Saved model artifacts
│
└── docs/
    └── architecture.md
```

## 🚀 Quick Start

### Step 1 — Laptop: Clone & Set Up Server

```bash
git clone https://github.com/YOUR_USERNAME/network-lab.git
cd network-lab/server
pip install -r requirements.txt
python app.py
```

Server starts at `http://0.0.0.0:5000`

### Step 2 — Laptop: Find Your Local IP

```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
# Example: 192.168.1.105
```

### Step 3 — Phone (Termux): Setup

```bash
pkg update && pkg upgrade -y
bash phone_agent/setup.sh
```

### Step 4 — Phone: Configure & Run

Edit `phone_agent/config.py` and set `SERVER_URL = "http://192.168.1.105:5000"`

```bash
cd phone_agent
python agent.py
```

### Step 5 — Train the ML Model

```bash
cd ml
python generate_sample_data.py   # Creates initial training data
python train.py                   # Trains model, saves to ml/models/
# Copy model to phone:
cp ml/models/anomaly_model.pkl phone_agent/inference/
```

### Step 6 — View Dashboard

Open browser: `http://localhost:5000`

---

## 📊 Dashboard Features

- **Live metrics feed** via WebSocket
- **Latency time series** chart (last 100 samples)
- **Packet loss** trend
- **Network I/O** (bytes sent/received per second)
- **WiFi signal strength** gauge
- **Anomaly alerts** highlighted in red
- **Summary statistics** (avg latency, uptime, total anomalies)

## 🤖 Machine Learning Details

**Model:** Isolation Forest (unsupervised anomaly detection)

**Features used for training/inference:**
- `latency_avg` — average ping latency (ms)
- `latency_std` — latency jitter (ms)
- `packet_loss` — percentage of dropped packets
- `http_response_time` — HTTP probe time (ms)
- `bytes_recv_rate` — download rate (bytes/s)
- `bytes_sent_rate` — upload rate (bytes/s)
- `dns_time` — DNS resolution time (ms)
- `wifi_signal` — WiFi RSSI (dBm)

**Why Isolation Forest?**
- Unsupervised — no labeled anomaly data needed
- Extremely lightweight (fits in <1MB)
- Fast inference (< 5ms on Snapdragon 425)
- Great for novelty/anomaly detection in time series

## ⚠️ Non-Root Limitations & Workarounds

| Feature | Root Needed? | Workaround Used |
|---|---|---|
| Packet capture (tcpdump) | ✅ Yes | psutil interface counters instead |
| Raw sockets | ✅ Yes | subprocess ping for ICMP |
| Monitor mode WiFi | ✅ Yes | Termux:API WiFi info |
| ARP scanning | ✅ Yes | HTTP probes to common IPs |

## 📄 License

MIT License — see [LICENSE](LICENSE)
