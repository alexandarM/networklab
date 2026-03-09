# 🛠️ NetworkLab — Complete Setup Guide (Step by Step)

Sve korake koje treba da uradiš, redom. Označeno gdje se izvršava: 📱 **TELEFON** ili 💻 **LAPTOP**.

---

## FAZA 1 — Priprema laptop-a (VS Code / Linux Mint)

### 💻 Korak 1 — Kloniraj/Napravi projekt

```bash
# Na laptopу — otvori terminal
cd ~/Projects   # ili gdje želiš

# Kloniraj sa GitHuba (ako si već push-ovao):
git clone https://github.com/TVOJ_USERNAME/network-lab.git
cd network-lab

# ILI ako još nisi napravioGitHub repo, samo raspakuj zip koji si dobio
```

### 💻 Korak 2 — Napravi GitHub repo

1. Idi na https://github.com/new
2. Ime repo-a: `network-lab`
3. Opis: `Phone-powered network monitoring + ML anomaly detection (Termux + Flask)`
4. Postavi na **Public**
5. **Nemoj** dodavati README (već ga imamo)
6. Klikni "Create repository"

```bash
# U terminalu, u network-lab/ folderu:
git init
git add .
git commit -m "Initial commit: NetworkLab phone agent + Flask server + ML pipeline"
git branch -M main
git remote add origin https://github.com/TVOJ_USERNAME/network-lab.git
git push -u origin main
```

### 💻 Korak 3 — Instaliraj server zavisnosti

```bash
# U network-lab/server/
cd server
pip install -r requirements.txt
```

Instalirat će se: Flask, Flask-SocketIO, Flask-CORS, eventlet

### 💻 Korak 4 — Napravi i treniraj ML model

```bash
# U network-lab/
cd ..

# 4a. Instaliraj ML zavisnosti
pip install -r ml/requirements.txt

# 4b. Generiši sintetičke podatke za trening
python ml/generate_sample_data.py
# → Pravi ml/data/training_data.csv (2000 uzoraka)
# → Pravi ml/data/test_data.csv    (400 uzoraka)

# 4c. Treniraj model
python ml/train.py
# → Snima ml/models/anomaly_model.pkl
# → Snima ml/models/scaler.pkl
# → Pravi ml/models/training_report.txt

# 4d. (Opcionalno) Evaluacija sa grafovima
python ml/evaluate.py
# → Pravi ml/plots/evaluation.png
```

### 💻 Korak 5 — Pronađi svoju lokalnu IP adresu

```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
# Primjer output-a:
#    inet 192.168.1.105/24 brd 192.168.1.255 scope global wlan0
# Zapamti ovu adresu! (192.168.1.105 u primjeru)
```

### 💻 Korak 6 — Pokrenite Flask server

```bash
cd server
python app.py
# ╔══════════════════════════════════════════╗
# ║  NetworkLab Server  v1.0                 ║
# ║  Dashboard → http://localhost:5000       ║
# ╚══════════════════════════════════════════╝
```

Otvori browser: **http://localhost:5000** — vidiš dashboard (prazan za sada).

---

## FAZA 2 — Priprema telefona (Termux)

> **Preduvjet**: Telefon i laptop su na **istoj WiFi mreži**!

### 📱 Korak 7 — Instaliraj Termux aplikacije

Na telefonu installiraj sa **F-Droid** (ne Play Store — zastarjele verzije!):
1. **Termux** — https://f-droid.org/packages/com.termux/
2. **Termux:API** — https://f-droid.org/packages/com.termux.api/

Dozvoli **sve permissions** za Termux:API (lokacija, WiFi).

### 📱 Korak 8 — Početno podešavanje Termux-a

```bash
# U Termux aplikaciji:
pkg update && pkg upgrade -y
# (može potrajati 5-10 minuta pri prvom pokretanju)

# Instaliraj git
pkg install git -y
```

### 📱 Korak 9 — Kloniraj projekt na telefon

```bash
# U Termux:
cd ~
git clone https://github.com/TVOJ_USERNAME/network-lab.git
cd network-lab
```

### 📱 Korak 10 — Pokreni setup skriptu

```bash
# U Termux, u network-lab/ folderu:
bash phone_agent/setup.sh
# Ovo instalira sve Python pakete (može potrajati 10-15 min)
# psutil, requests, scikit-learn, numpy...
```

### 📱 Korak 11 — Podesi konfiguraciju

```bash
# U Termux:
nano phone_agent/config.py
```

Promijeni ovu liniju:
```python
SERVER_URL = "http://192.168.1.105:5000"   # ← Stavi SVOJU IP adresu laptopa
```

Sačuvaj: `Ctrl+X`, zatim `Y`, zatim `Enter`

---

## FAZA 3 — Prebaci ML model na telefon

### 💻 Korak 12 — Posluži model fajlove sa laptopa (HTTP server)

```bash
# Na laptopу — novi terminal tab:
cd network-lab/ml/models
python -m http.server 8888
# Serving HTTP on 0.0.0.0 port 8888...
```

### 📱 Korak 13 — Preuzmi model na telefon

```bash
# U Termux:
cd ~/network-lab/phone_agent/inference

# Preuzmi model (zamijeni IP sa IP-om svog laptopa):
curl http://192.168.1.105:8888/anomaly_model.pkl -o anomaly_model.pkl
curl http://192.168.1.105:8888/scaler.pkl -o scaler.pkl

# Provjeri:
ls -lh *.pkl
# anomaly_model.pkl   ~1.0 MB
# scaler.pkl          ~1 KB
```

---

## FAZA 4 — Pokretanje sistema

### 📱 Korak 14 — Pokrenite agent na telefonu

```bash
# U Termux:
cd ~/network-lab/phone_agent
python agent.py

# Output koji treba da vidiš:
#   _   _      _   _____ ___ _   _ _  __
#  | \ | | ___| |_|_   _|_ _| \ | | |/ /
#  ...
#  NetworkLab Agent v1.0
#  Device: huawei-y6-2018
#  Server: http://192.168.1.105:5000
#
#  ═══ Cycle #1 ═══
#  ⏱  Starting metric collection cycle...
#  ✅ Collection done in 8234ms
#  ─────────────────────────────────────
#    📊 METRICS — 2025-01-15T14:30:00Z
#    Latency:      avg=34.5ms  std=4.2ms
#    Packet Loss:  0.0%
#    HTTP Time:    312ms
#    ✅ Network Normal    score=0.123
#  ─────────────────────────────────────
#  📤 Metrics sent → http://192.168.1.105:5000/api/metrics [200]
#  ⏳ Next cycle in 30s...
```

### 💻 Korak 15 — Pogledaj dashboard

Otvori: **http://localhost:5000**

Trebalo bi vidjeti live podatke sa telefona!

---

## Korisni dodatni argumenti agenta

```bash
# Jedno prikupljanje (za testiranje)
python agent.py --once

# Bez slanja na server (debug mode)
python agent.py --dry-run

# Bez ML inferensa (ako model nije preuzet)
python agent.py --no-ml

# Detaljni logovi
python agent.py --debug

# Brži interval (svakih 10s umjesto 30s)
python agent.py --interval 10
```

## Česte greške i rješenja

| Problem | Rješenje |
|---|---|
| `Cannot reach server` | Provjeri IP u config.py, provjeri da su oba uređaja na istom WiFi |
| `ping: command not found` | `pkg install iputils` |
| `termux-wifi-connectioninfo` ne radi | Instaliraj Termux:API app, dozvoli lokaciju |
| `ModuleNotFoundError: psutil` | `pip install psutil` |
| Dashboard pust | Provjeri da agent šalje podatke (vidi log u Termuxu) |
| Model not found warning | Kopirati model.pkl na telefon (Korak 12-13) |

## Napomena za firewall

Ako Flask server nije dostupan sa telefona, možda trebaš otvoriti port:

```bash
# Na laptopу:
sudo ufw allow 5000
```
