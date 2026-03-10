# Setup Guide

Everything is split into two parts — stuff you do on the laptop and stuff you do on the phone. Do it in order because the ML model needs to be trained on the laptop before you can copy it to the phone.

Phone and laptop need to be on the same WiFi network.

---

## Part 1 — Laptop

### 1. Make a GitHub repo

Go to https://github.com/new and create a new repo called `network-lab`. Set it to public. Don't add a README or .gitignore, we already have those.

### 2. Initialize git and push

Unzip the project folder somewhere on your laptop, then open a terminal in that folder.

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/network-lab.git
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
# from the network-lab/ root folder:
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
git clone https://github.com/YOUR_USERNAME/network-lab.git
cd network-lab
```

### 10. Run the setup script

```bash
bash phone_agent/setup.sh
```

This installs all the Python packages the agent needs (psutil, requests, scikit-learn, numpy...). It can take 10-20 minutes on the phone, scikit-learn especially takes a while to compile.

### 11. Set the server URL

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

### 12. Serve the model files from your laptop

Open a new terminal tab on your laptop (keep the Flask server running in the other one):

```bash
cd network-lab/ml/models
python -m http.server 8888
```

### 13. Download the model on the phone

```bash
# in Termux:
cd ~/network-lab/phone_agent/inference

curl http://YOUR_LAPTOP_IP:8888/anomaly_model.pkl -o anomaly_model.pkl
curl http://YOUR_LAPTOP_IP:8888/scaler.pkl -o scaler.pkl

# check they're there:
ls -lh
# anomaly_model.pkl should be around 1MB
# scaler.pkl will be tiny, around 1KB
```

You can stop the HTTP server on the laptop after this (Ctrl+C).

---

## Part 4 — Run everything

### 14. Start the agent on the phone

```bash
cd ~/network-lab/phone_agent
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

### 15. Check the dashboard

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
Check that the IP in config.py is correct. Make sure both devices are on the same WiFi. If it still doesn't work, try opening the port:
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

**ModuleNotFoundError: psutil (or any other package)**
```bash
pip install psutil
```

**Dashboard loads but no data appears**
Look at the Termux terminal to see if the agent is actually sending data. Look at the Flask terminal on the laptop to see if it's receiving anything. Usually it's the IP address in config.py being wrong.

**Model not found warning on the phone**
The agent still works without it, just without anomaly detection. Follow steps 12-13 to copy the model over.