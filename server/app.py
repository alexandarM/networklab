# server/app.py
"""
NetworkLab — Flask Web Server
─────────────────────────────────────────────────────────────────
Receives metrics from phone agent, stores them in SQLite,
and serves a real-time dashboard via WebSocket.

Endpoints:
  GET  /                    → Dashboard HTML
  POST /api/metrics         → Receive metrics from phone agent
  GET  /api/data            → Recent metrics (JSON, for charts)
  GET  /api/stats           → Summary statistics
  GET  /api/anomalies       → Recent anomaly events
  GET  /api/health          → Server health check

Run:
  python app.py
  → http://localhost:5000
"""

import os
import sys
import logging
from flask import Flask, render_template, request, jsonify, abort
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime

# Add parent dir to path for relative imports during dev
sys.path.insert(0, os.path.dirname(__file__))
import database as db

# ── App setup ──────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "networklab-dev-secret-2025")
app.config["JSON_SORT_KEYS"] = False

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("server")


# ── HTML Routes ────────────────────────────────────────────
@app.route("/")
def dashboard():
    """Serve the main dashboard."""
    return render_template("dashboard.html")


# ── REST API ───────────────────────────────────────────────
@app.route("/api/metrics", methods=["POST"])
def receive_metrics():
    """
    Accept a metrics JSON payload from the phone agent.
    Stores it in SQLite and broadcasts to all connected dashboard clients.
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Empty payload"}), 400

    # Validate required field
    if "timestamp" not in data:
        data["timestamp"] = datetime.utcnow().isoformat() + "Z"

    row_id = db.insert_metrics(data)
    if row_id is None:
        return jsonify({"error": "Database write failed"}), 500

    # Broadcast to all dashboard clients via WebSocket
    data["id"] = row_id
    socketio.emit("new_metrics", data)

    # Emit anomaly alert if detected
    if data.get("is_anomaly"):
        socketio.emit("anomaly_alert", {
            "timestamp": data["timestamp"],
            "score": data.get("anomaly_score"),
            "reason": data.get("anomaly_reason"),
        })

    logger.info(
        f"📥 Metrics from [{data.get('device_id', '?')}] "
        f"latency={data.get('latency_avg')}ms "
        f"anomaly={bool(data.get('is_anomaly'))} "
        f"(row_id={row_id})"
    )

    return jsonify({"status": "ok", "id": row_id})


@app.route("/api/data")
def get_data():
    """
    Return recent metrics for chart rendering.
    Query params:
      limit (int, default=100) — number of most recent rows
      device (str, optional)   — filter by device_id
    """
    limit = request.args.get("limit", 100, type=int)
    limit = min(limit, 500)  # cap
    device = request.args.get("device", None)
    rows = db.get_recent_metrics(limit=limit, device_id=device)
    return jsonify(rows)


@app.route("/api/stats")
def get_stats():
    """Return aggregate summary statistics."""
    device = request.args.get("device", None)
    stats = db.get_summary_stats(device_id=device)
    return jsonify(stats)


@app.route("/api/anomalies")
def get_anomalies():
    """Return recent anomaly events."""
    limit = request.args.get("limit", 20, type=int)
    anomalies = db.get_anomaly_history(limit=limit)
    return jsonify(anomalies)


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
    })


# ── WebSocket events ───────────────────────────────────────
@socketio.on("connect")
def on_connect():
    logger.info(f"🔌 Dashboard client connected: {request.sid}")
    # Send last 10 rows immediately on connect
    rows = db.get_recent_metrics(limit=10)
    emit("history", rows)


@socketio.on("disconnect")
def on_disconnect():
    logger.info(f"🔌 Dashboard client disconnected: {request.sid}")


# ── Entry point ────────────────────────────────────────────
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════╗
║  NetworkLab Server  v1.0                 ║
║  Dashboard → http://localhost:5000       ║
║  API       → http://localhost:5000/api   ║
╚══════════════════════════════════════════╝
""")
    db.init_db()
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False,
    )
