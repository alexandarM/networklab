# Setup Guide

Everything is split into two parts — stuff you do on the laptop and stuff you do on the phone. Do it in order because the ML model needs to be trained on the laptop before you can copy it to the phone.

Phone and laptop need to be on the same WiFi network.

---

## Part 1 — Laptop

### 1. Make a GitHub repo

Go to https://github.com/new and create a new repo called `networklab`. Set it to public. Don't add a README or .gitignore, we already have those.

### 2. Initialize git and push

Unzip the project folder somewhere on your laptop, then open a terminal in that folder.

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/networklab.git
git push -u origin main
```

### 3. Install server dependencies

```bash
cd server
pip install -r requirements.txt
```

This installs Flask, Flask-SocketIO, Flask-CORS and eventlet.

### 4. Generate training data and train the ML model

```bash
# from the networklab/ root folder:
pip install -r ml/requirements.txt

python ml/generate_sample_data.py
# creates ml/data/training_data.csv and ml/data/test_data.csv

python ml/train.py
# creates ml/models/anomaly_model.pkl and ml/models/scaler.pkl
```

Optionally you can run `python ml/evaluate.py` after training to get some plots, but it's not required.

### 5. Find your laptop's local IP address

You'll need this to configure the phone agent.

```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
# look for something like: inet 192.168.1.105/24 ...
# the IP is 192.168.1.105 in this example, yours will be different
```

Write it down.

### 6. Start the Flask server

```bash
cd server
python app.py
```

Open http://localhost:5000 in a browser. The dashboard will be empty for now, that's fine.

Leave this terminal open, the server needs to keep running.

---

## Part 2 — Phone (Termux)

### 7. Install Termux

Install from F-Droid, not the Play Store. The Play Store version is outdated and some packages won't install correctly.

- Termux: https://f-droid.org/packages/com.termux/
- Termux:API: https://f-droid.org/packages/com.termux.api/

After installing Termux:API, open it once and grant it location and WiFi permissions.

### 8. First time setup in Termux

```bash
pkg update && pkg upgrade -y
# this takes a while the first time, just let it run

pkg install git -y
```

### 9. Clone the project

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/networklab.git
cd networklab
```

### 10. Run the setup script

```bash
bash phone_agent/setup.sh
```

This installs all the Python packages the agent needs (requests, scikit-learn, numpy...). It can take 10-20 minutes on the phone, scikit-learn especially takes a while to compile.

### 11. Install psutil

psutil is used to read network interface stats. Try installing it normally first:

```bash
pkg install clang make
pip install psutil
```

**If that fails with "platform android is not supported"**, there is a known Termux compiler bug. The fix below is based on https://github.com/termux/termux-packages/issues/20039#issuecomment-2096494418

First find the sysconfig file (the exact filename varies by device and Python version):

```bash
find $PREFIX/lib/python3.13 -name "_sysconfigdata*.py"
```

It should print a path like `/data/data/com.termux/files/usr/lib/python3.13/_sysconfigdata__android_aarch64-linux-android.py`. Copy that path, then run:

```bash
_file="PASTE_THE_PATH_HERE"
rm -rf $PREFIX/lib/python3.13/__pycache__
cp $_file "$_file".backup
sed -i 's|-fno-openmp-implicit-rpath||g' "$_file"
```

Then try again:

```bash
pip install psutil
```

**If it still fails**, skip psutil entirely and use the fallback version of net_stats.py that reads directly from `/proc/net/dev` instead. Replace the contents of `phone_agent/collectors/net_stats.py` with this:

```python
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
        "bytes_sent_rate":    round(max(0, (snap2["bytes_sent"]   - snap1["bytes_sent"])   / dt), 1),
        "bytes_recv_rate":    round(max(0, (snap2["bytes_recv"]   - snap1["bytes_recv"])   / dt), 1),
        "packets_sent_rate":  round(max(0, (snap2["packets_sent"] - snap1["packets_sent"]) / dt), 1),
        "packets_recv_rate":  round(max(0, (snap2["packets_recv"] - snap1["packets_recv"]) / dt), 1),
        "bytes_sent_total":   snap2["bytes_sent"],
        "bytes_recv_total":   snap2["bytes_recv"],
        "errors_in":          0,
        "errors_out":         0,
        "drops_in":           0,
        "dns_time":           dns_time,
        "active_connections": -1,
    }
```

This does exactly the same thing as psutil on Android — psutil reads `/proc/net/dev` under the hood anyway. No other files need to change.

### 12. Set the server URL

```bash
nano phone_agent/config.py
```

Find this line near the top:

```python
SERVER_URL = "http://192.168.1.105:5000"
```

Change the IP to your laptop's IP from step 5. Save with Ctrl+X, then Y, then Enter.

---

## Part 3 — Copy the ML model to the phone

The model was trained on your laptop and needs to be transferred to the phone. The easiest way is to serve it over HTTP.

### 13. Open port 8888 on the laptop temporarily

```bash
sudo ufw allow 8888
```

### 14. Serve the model files from your laptop

Open a new terminal tab on the laptop (keep the Flask server running in the other one). Make sure you cd into the models folder specifically, otherwise you'll be serving the whole project directory.

```bash
cd networklab/ml/models
python -m http.server 8888
```

Open `http://YOUR_LAPTOP_IP:8888` in a browser to verify — you should see only the two .pkl files listed. If you see a bunch of folders instead, you're running the server from the wrong directory.

### 15. Download the model on the phone

```bash
# in Termux:
cd ~/networklab/phone_agent/inference

curl http://YOUR_LAPTOP_IP:8888/anomaly_model.pkl -o anomaly_model.pkl
curl http://YOUR_LAPTOP_IP:8888/scaler.pkl -o scaler.pkl

# check they're there:
ls -lh
# anomaly_model.pkl should be around 1MB
# scaler.pkl will be tiny, around 1KB
```

### 16. Close port 8888

Stop the HTTP server on the laptop (Ctrl+C) then remove the firewall rule:

```bash
sudo ufw delete allow 8888
sudo ufw status
# port 8888 should no longer be listed
```

Port 5000 stays open since the agent still needs that to talk to Flask.

---

## Part 4 — Run everything

### 17. Start the agent on the phone

```bash
cd ~/networklab/phone_agent
python agent.py
```

You should see it collecting metrics and after the first cycle it will print something like:

```
Latency:      avg=34.5ms  std=4.2ms
Packet Loss:  0.0%
HTTP Time:    312ms
Network Normal    score=0.123
Metrics sent [200]
Next cycle in 30s...
```

### 18. Check the dashboard

Go to http://localhost:5000 on your laptop. After the first cycle finishes you'll see data starting to appear on the graphs.

---

## Extra agent options

```bash
python agent.py --once        # run one cycle and exit, useful for testing
python agent.py --dry-run     # collect metrics but don't send to server
python agent.py --no-ml       # skip ML inference
python agent.py --debug       # verbose logging
python agent.py --interval 10 # send every 10s instead of 30s
```

---

## Common problems

**Cannot reach server**
Check that the IP in config.py is correct. Make sure both devices are on the same WiFi. If it still doesn't work, open the port:
```bash
sudo ufw allow 5000
```

**ping: command not found**
```bash
pkg install iputils
```

**termux-wifi-connectioninfo not found**
Make sure the Termux:API app is installed from F-Droid and that you gave it permissions. Then:
```bash
pkg install termux-api
```

**curl: failed to connect to laptop IP on port 8888**
The firewall is blocking it. Run `sudo ufw allow 8888` on the laptop, try the curl again, then close the port afterwards with `sudo ufw delete allow 8888`.

**psutil: platform android is not supported**
See step 11 for the two workarounds.

**Dashboard loads but no data appears**
Look at the Termux terminal to see if the agent is actually sending data. Look at the Flask terminal on the laptop to see if it's receiving anything. Usually it's the IP address in config.py being wrong.

**Model not found warning on the phone**
The agent still works without it, just without anomaly detection. Follow steps 13-16 to copy the model over.