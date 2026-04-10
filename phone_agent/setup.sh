#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# setup.sh — One-command Termux setup for NetworkLab agent
# Run from the network-lab root:  bash phone_agent/setup.sh
# ============================================================

set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   NetworkLab — Termux Setup Script   ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Update package index ────────────────────────────────
echo "[1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# ── 2. Install system dependencies ────────────────────────
echo "[2/6] Installing system packages..."
pkg install -y python python-pip iputils nmap dnsutils termux-api

# ── 3. Install Python packages ─────────────────────────────
echo "[3/6] Installing Python packages..."
pip install --upgrade pip
pip install \
    requests==2.31.0 \
    psutil==5.9.8 \
    scikit-learn==1.3.2 \
    numpy==1.26.4 \
    joblib==1.3.2 \
    colorlog==6.8.2

# ── 4. Create inference model directory ───────────────────
echo "[4/6] Setting up directories..."
mkdir -p phone_agent/inference

# ── 5. Termux:API check ────────────────────────────────────
echo "[5/6] Checking Termux:API..."
if command -v termux-wifi-connectioninfo &> /dev/null; then
    echo "    ✅ Termux:API is available"
else
    echo "    ⚠️  Termux:API not found."
    echo "       Install 'Termux:API' app from F-Droid, then:"
    echo "       pkg install termux-api"
fi

# ── 6. Grant permissions reminder ─────────────────────────
echo "[6/6] Permission reminder..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅ Setup complete!"
echo ""
echo " Next steps:"
echo "   1. Edit phone_agent/config.py"
echo "      → Set SERVER_URL to your laptop's IP"
echo ""
echo "   2. Copy the trained model from your laptop:"
echo "      scp ml/models/anomaly_model.pkl <phone_ip>:~/network-lab/phone_agent/inference/"
echo "      scp ml/models/scaler.pkl        <phone_ip>:~/network-lab/phone_agent/inference/"
echo ""
echo "   3. Start the agent:"
echo "      cd phone_agent && python agent.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
