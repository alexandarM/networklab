"""
Usage:
    python ml/train.py                     # Train on generated data
    python ml/train.py --data custom.csv   # Train on your own CSV

Output:
    ml/models/anomaly_model.pkl   ← copy to phone_agent/inference/
    ml/models/scaler.pkl          ← copy to phone_agent/inference/
    ml/models/training_report.txt ← training summary
"""

import os
import sys
import csv
import argparse
import datetime
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, confusion_matrix,
    precision_score, recall_score, f1_score,
    roc_auc_score,
)

# Config
FEATURE_NAMES = [
    "latency_avg",
    "latency_std",
    "latency_min",
    "latency_max",
    "packet_loss",
    "http_response_time",
    "bytes_sent_rate",
    "bytes_recv_rate",
    "dns_time",
    "wifi_signal",
]

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
DEFAULT_TRAIN = os.path.join(DATA_DIR, "training_data.csv")
MODEL_PATH    = os.path.join(MODELS_DIR, "anomaly_model.pkl")
SCALER_PATH   = os.path.join(MODELS_DIR, "scaler.pkl")
REPORT_PATH   = os.path.join(MODELS_DIR, "training_report.txt")


# Load data
def load_csv(filepath: str) -> tuple:

    X, y = [], []
    skipped = 0

    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                features = [float(row.get(f, -1) or -1) for f in FEATURE_NAMES]
                label = int(row.get("is_anomaly", 0))
                X.append(features)
                y.append(label)
            except (ValueError, KeyError):
                skipped += 1

    if skipped:
        print(f"Skipped {skipped} rows")

    return np.array(X), np.array(y)


# Train model
def train(X_train: np.ndarray, contamination: float) -> tuple:

    # Fit scaler on training feats
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    model = IsolationForest(
        n_estimators=200,
        max_samples="auto",
        contamination=contamination,
        max_features=1.0,
        bootstrap=False,
        n_jobs=-1,
        random_state=42,
        verbose=0,
    )
    model.fit(X_scaled)
    return model, scaler


def evaluate(model, scaler, X_test, y_test) -> dict:

    X_scaled = scaler.transform(X_test)

    # predict: 1=normal, -1=anomaly  →  convert to 0/1
    raw_preds = model.predict(X_scaled)
    y_pred = (raw_preds == -1).astype(int)

    raw_scores = model.decision_function(X_scaled)
    y_scores = 0.5 - raw_scores   # Normalize to ~0–1

    metrics = {
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall":    recall_score(y_test, y_pred, zero_division=0),
        "f1":        f1_score(y_test, y_pred, zero_division=0),
    }

    try:
        metrics["roc_auc"] = roc_auc_score(y_test, y_scores)
    except ValueError:
        metrics["roc_auc"] = None

    metrics["confusion_matrix"] = confusion_matrix(y_test, y_pred).tolist()
    metrics["report"] = classification_report(
        y_test, y_pred, target_names=["Normal", "Anomaly"]
    )

    return metrics



def main():
    parser = argparse.ArgumentParser(description="Train model")
    parser.add_argument("--data", default=DEFAULT_TRAIN,
                        help=f"Training CSV path (default: {DEFAULT_TRAIN})")
    parser.add_argument("--contamination", type=float, default=None,
                        help="Expected anomaly ratio (auto-detected if not set)")
    args = parser.parse_args()

    # Load data
    if not os.path.exists(args.data):
        print(f"Data file not found: {args.data}")
        print("Run first: python ml/generate_sample_data.py")
        sys.exit(1)

    print(f"Loading data from: {args.data}")
    X, y = load_csv(args.data)
    print(f"  Samples:  {len(X)}")
    print(f"  Features: {len(FEATURE_NAMES)}")
    n_anomalies = y.sum()
    print(f"  Anomalies: {n_anomalies} ({n_anomalies/len(y)*100:.1f}%)")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nSplit: {len(X_train)} train / {len(X_test)} test")

    #
    contamination = args.contamination
    if contamination is None:
        contamination = max(0.01, min(0.5, y_train.sum() / len(y_train)))
        print(f"Auto contamination: {contamination:.4f}")

    # Training
    print()
    model, scaler = train(X_train, contamination)
    print("Model trained")

    # Evaluate model
    print("\nEvaluating on test set")
    metrics = evaluate(model, scaler, X_test, y_test)

    print(f"\n{'─'*50}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1 Score:  {metrics['f1']:.4f}")
    if metrics.get("roc_auc"):
        print(f"  ROC-AUC:   {metrics['roc_auc']:.4f}")
    print(f"{'─'*50}")
    print("\nClassification Report:")
    print(metrics["report"])
    print(f"Confusion Matrix:")
    cm = metrics["confusion_matrix"]
    print(f"  TN={cm[0][0]}  FP={cm[0][1]}")
    print(f"  FN={cm[1][0]}  TP={cm[1][1]}")

    # Save model
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"\nModel saved: {MODEL_PATH}")
    print(f"Scaler saved: {SCALER_PATH}")

    # Save report
    report_text = f"""Model Training Report
Generated: {datetime.datetime.now().isoformat()}
{'='*50}
Training data:  {args.data}
Train samples:  {len(X_train)}
Test samples:   {len(X_test)}
Features:       {', '.join(FEATURE_NAMES)}

Model: IsolationForest
  n_estimators={model.n_estimators}
  contamination={model.contamination}
  random_state=42

Results:
  Precision: {metrics['precision']:.4f}
  Recall:    {metrics['recall']:.4f}
  F1 Score:  {metrics['f1']:.4f}
  ROC-AUC:   {metrics.get('roc_auc', 'N/A')}

{metrics['report']}
Confusion Matrix:
  TN={cm[0][0]}  FP={cm[0][1]}
  FN={cm[1][0]}  TP={cm[1][1]}
"""
    with open(REPORT_PATH, "w") as f:
        f.write(report_text)
    print(f"Report saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
