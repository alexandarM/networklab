# NetworkLab

Network monitoring project running on an old Android phone (Huawei Y6 2018) through Termux, without root.

The idea was to use the phone as some kind of network monitoring device since it was just sitting around doing nothing. It collects network metrics, runs a small ML model locally on the phone, and sends everything to a Flask server on my laptop where you can see it on a dashboard.

---

## What it does

- Pings a few DNS servers every 30 seconds and measures latency/packet loss
- Measures HTTP response times to a few websites
- Reads network interface stats (download/upload speeds) directly from /proc/net/dev
- Gets WiFi signal strength through Termux:API
- Runs an Isolation Forest model locally on the phone to detect if something looks off with the network
- Sends all of this to a Flask server running on my laptop
- The server saves everything in SQLite and shows it on a live dashboard

---

## Architecture

```
  PHONE (Termux, no root)              LAPTOP (Linux Mint)

  collectors/
    ping_monitor.py   ──────────►   Flask server (app.py)
    http_monitor.py      HTTP            |
    net_stats.py         POST       SQLite database
    wifi_info.py                         |
                                    Dashboard (Chart.js
  inference/                         + WebSocket)
    anomaly_detector.py
    (runs model.pkl locally)
         ^
         |
         model.pkl (trained on laptop, copied to phone)
```

---

## Tech stack

- Phone agent: Python, requests, scikit-learn (psutil dropped due to Android incompatibility)
- Network probes: subprocess ping, urllib, socket, Termux:API
- ML: scikit-learn Isolation Forest
- Server: Flask, Flask-SocketIO
- Database: SQLite
- Dashboard: plain HTML, Chart.js, Socket.IO

---

## Project structure

```
networklab/
├── phone_agent/
│   ├── agent.py              # main script, this is what you run on the phone
│   ├── config.py             # put your laptop IP here before running
│   ├── setup.sh              # installs everything needed in Termux
│   ├── collectors/
│   │   ├── ping_monitor.py
│   │   ├── http_monitor.py
│   │   ├── net_stats.py
│   │   └── wifi_info.py
│   └── inference/
│       └── anomaly_detector.py
│
├── server/
│   ├── app.py
│   ├── database.py
│   └── templates/
│       └── dashboard.html
│
└── ml/
    ├── generate_sample_data.py
    ├── train.py
    ├── evaluate.py
    └── models/
```

---

## Setup

Full step-by-step instructions are in [SETUP_GUIDE.md](SETUP_GUIDE.md). Short version below.

### Laptop

```bash
git clone https://github.com/YOUR_USERNAME/networklab.git
cd networklab

# install server dependencies
pip install -r server/requirements.txt

# generate training data and train the model
pip install -r ml/requirements.txt
python ml/generate_sample_data.py
python ml/train.py

# find your local IP (you'll need this for the phone config)
ip addr show | grep "inet " | grep -v 127.0.0.1

# start the server
python server/app.py
```

Dashboard will be at `http://localhost:5000`

### Phone (Termux)

```bash
pkg update && pkg upgrade -y
pkg install git -y

git clone https://github.com/YOUR_USERNAME/networklab.git
cd networklab

bash phone_agent/setup.sh
```

Edit `phone_agent/config.py` and change `SERVER_URL` to your laptop's IP address.

Copy the trained model to the phone (easiest way is a quick HTTP server):

```bash
# on laptop:
cd ml/models
python -m http.server 8888

# on phone (Termux):
cd ~/networklab/phone_agent/inference
curl http://YOUR_LAPTOP_IP:8888/anomaly_model.pkl -o anomaly_model.pkl
curl http://YOUR_LAPTOP_IP:8888/scaler.pkl -o scaler.pkl
```

Then start the agent:

```bash
cd ~/networklab/phone_agent
python agent.py
```

---

## ML model

Uses Isolation Forest from scikit-learn. It's unsupervised so there's no need to label data, it just learns what "normal" network traffic looks like and flags anything that deviates from that.

Features: latency avg/std/min/max, packet loss, HTTP response time, bytes sent/recv rate, DNS time, WiFi signal.

The model is trained on the laptop and the .pkl file is copied to the phone. Inference runs fully offline on the phone, takes under 5ms on the Snapdragon 425.

---

## No-root limitations

Some things don't work without root, so workarounds were used:

| What | Root needed | What I used instead |
|---|---|---|
| tcpdump / packet capture | yes | /proc/net/dev directly |
| raw sockets | yes | subprocess ping |
| WiFi monitor mode | yes | Termux:API |
| ARP scan | yes | HTTP probes |

---

## Notes

- Phone needs to be on the same WiFi network as the laptop
- Termux:API app needs to be installed separately from F-Droid (not Play Store)
- psutil doesn't work on Android so net_stats.py reads /proc/net/dev directly instead — same data, no package needed
- The generated training data is synthetic — after collecting a few hours of real data from the phone you can retrain the model on that instead, it'll be more accurate

---

## License

MIT