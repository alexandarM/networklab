"""
Usage:
    python ml/evaluate.py
    python ml/evaluate.py --data ml/data/test_data.csv
"""

import os
import sys
import argparse
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import csv
import joblib

try:
    import matplotlib
    matplotlib.use("Agg")  
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from sklearn.metrics import (
    roc_curve, auc, precision_recall_curve,
    confusion_matrix, classification_report,
)

# Paths
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
PLOTS_DIR  = os.path.join(os.path.dirname(__file__), "plots")
MODEL_PATH  = os.path.join(MODELS_DIR, "anomaly_model.pkl")
SCALER_PATH = os.path.join(MODELS_DIR, "scaler.pkl")
DEFAULT_TEST = os.path.join(DATA_DIR, "test_data.csv")

FEATURE_NAMES = [
    "latency_avg", "latency_std", "latency_min", "latency_max",
    "packet_loss", "http_response_time", "bytes_sent_rate", "bytes_recv_rate",
    "dns_time", "wifi_signal",
]

# COlors
DARK_BG   = "#0d1117"
CARD_BG   = "#161b22"
BORDER    = "#30363d"
TEXT      = "#e6edf3"
TEXT2     = "#8b949e"
BLUE      = "#58a6ff"
GREEN     = "#3fb950"
RED       = "#f85149"
ORANGE    = "#d29922"


def load_csv(filepath):
    X, y = [], []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                X.append([float(row.get(f, -1) or -1) for f in FEATURE_NAMES])
                y.append(int(row.get("is_anomaly", 0)))
            except (ValueError, KeyError):
                pass
    return np.array(X), np.array(y)


def plot_all(model, scaler, X_test, y_test):
    os.makedirs(PLOTS_DIR, exist_ok=True)
    X_scaled = scaler.transform(X_test)
    raw_scores = model.decision_function(X_scaled)
    y_scores = 0.5 - raw_scores
    y_pred = (model.predict(X_scaled) == -1).astype(int)

    plt.rcParams.update({
        "figure.facecolor":  DARK_BG,
        "axes.facecolor":    CARD_BG,
        "axes.edgecolor":    BORDER,
        "axes.labelcolor":   TEXT,
        "xtick.color":       TEXT2,
        "ytick.color":       TEXT2,
        "text.color":        TEXT,
        "grid.color":        BORDER,
        "grid.alpha":        0.5,
    })

    fig = plt.figure(figsize=(14, 10), facecolor=DARK_BG)
    fig.suptitle("NetworkLab — Model Evaluation", fontsize=16, color=TEXT, y=0.98)
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    # ROC Curve
    ax1 = fig.add_subplot(gs[0, 0])
    fpr, tpr, _ = roc_curve(y_test, y_scores)
    roc_auc = auc(fpr, tpr)
    ax1.plot(fpr, tpr, color=BLUE, lw=2, label=f"AUC = {roc_auc:.3f}")
    ax1.plot([0, 1], [0, 1], color=TEXT2, lw=1, linestyle="--")
    ax1.set_xlabel("False Positive Rate"); ax1.set_ylabel("True Positive Rate")
    ax1.set_title("ROC Curve", color=TEXT); ax1.legend(); ax1.grid(True)

    # Precision-Recall Curve
    ax2 = fig.add_subplot(gs[0, 1])
    prec, rec, _ = precision_recall_curve(y_test, y_scores)
    pr_auc = auc(rec, prec)
    ax2.plot(rec, prec, color=GREEN, lw=2, label=f"PR-AUC = {pr_auc:.3f}")
    ax2.set_xlabel("Recall"); ax2.set_ylabel("Precision")
    ax2.set_title("Precision-Recall Curve", color=TEXT); ax2.legend(); ax2.grid(True)

    # Confusion Matrix
    ax3 = fig.add_subplot(gs[0, 2])
    cm = confusion_matrix(y_test, y_pred)
    im = ax3.imshow(cm, interpolation="nearest", cmap="Blues")
    ax3.set_title("Confusion Matrix", color=TEXT)
    labels = ["Normal", "Anomaly"]
    ax3.set_xticks([0, 1]); ax3.set_yticks([0, 1])
    ax3.set_xticklabels(labels); ax3.set_yticklabels(labels)
    ax3.set_xlabel("Predicted"); ax3.set_ylabel("Actual")
    for i in range(2):
        for j in range(2):
            ax3.text(j, i, str(cm[i][j]), ha="center", va="center",
                     color="white", fontsize=14, fontweight="bold")

    # Anomaly Score Distribution
    ax4 = fig.add_subplot(gs[1, 0:2])
    normal_scores  = y_scores[y_test == 0]
    anomaly_scores = y_scores[y_test == 1]
    bins = np.linspace(0, 1, 40)
    ax4.hist(normal_scores, bins=bins, alpha=0.7, color=GREEN, label="Normal")
    ax4.hist(anomaly_scores, bins=bins, alpha=0.7, color=RED, label="Anomaly")
    ax4.axvline(0.5, color=ORANGE, linestyle="--", label="Threshold (0.5)")
    ax4.set_xlabel("Anomaly Score"); ax4.set_ylabel("Count")
    ax4.set_title("Score Distribution", color=TEXT)
    ax4.legend(); ax4.grid(True, axis="y")

    # Feature means: normal vs anomaly
    ax5 = fig.add_subplot(gs[1, 2])
    X_norm = scaler.transform(X_test[y_test == 0])
    X_anom = scaler.transform(X_test[y_test == 1])
    means_norm = X_norm.mean(axis=0)
    means_anom = X_anom.mean(axis=0)
    short_names = [f.replace("_", "\n")[:10] for f in FEATURE_NAMES]
    x = np.arange(len(FEATURE_NAMES))
    w = 0.35
    ax5.bar(x - w/2, means_norm, w, color=GREEN, alpha=0.8, label="Normal")
    ax5.bar(x + w/2, means_anom, w, color=RED,   alpha=0.8, label="Anomaly")
    ax5.set_xticks(x)
    ax5.set_xticklabels(short_names, fontsize=7)
    ax5.set_title("Feature Means (scaled)", color=TEXT)
    ax5.legend(fontsize=8); ax5.grid(True, axis="y")

    out_path = os.path.join(PLOTS_DIR, "evaluation.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    print(f"  ✅ Plot saved: {out_path}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=DEFAULT_TEST)
    args = parser.parse_args()

    if not os.path.exists(MODEL_PATH):
        print(f"Model not found: {MODEL_PATH}")
        print("   Run: python ml/train.py")
        sys.exit(1)

    print("Loading model & scaler")
    model  = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    print(f"Loading test data: {args.data}")
    X, y = load_csv(args.data)
    print(f"  {len(X)} samples, {y.sum()} anomalies\n")

    X_scaled = scaler.transform(X)
    y_pred   = (model.predict(X_scaled) == -1).astype(int)
    raw_scores = model.decision_function(X_scaled)
    y_scores = 0.5 - raw_scores

    print(classification_report(y, y_pred, target_names=["Normal", "Anomaly"]))

    plot_all(model, scaler, X, y)


if __name__ == "__main__":
    main()
