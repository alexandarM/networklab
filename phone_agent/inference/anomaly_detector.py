import os
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import joblib
    _LOADER = joblib
except ImportError:
    import pickle as _LOADER


class AnomalyDetector:

    def __init__(self, model_path: str, scaler_path: str, feature_names: list):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.feature_names = feature_names
        self.model = None
        self.scaler = None
        self.loaded = False
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.model_path):
                self.model = _LOADER.load(self.model_path)
                logger.info(f"Model loaded from {self.model_path}")
            else:
                logger.warning(
                    f"Model not found at {self.model_path}. "
                    "Running in passthrough mode — no anomaly detection."
                )

            if os.path.exists(self.scaler_path):
                self.scaler = _LOADER.load(self.scaler_path)
                logger.info(f"Scaler loaded from {self.scaler_path}")

            self.loaded = self.model is not None
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.loaded = False

    def _prepare_features(self, metrics: dict) -> Optional[np.ndarray]:

        try:
            features = []
            for name in self.feature_names:
                val = metrics.get(name)
                if val is None or val != val: 
                    val = -1.0
                features.append(float(val))
            return np.array(features).reshape(1, -1)
        except Exception as e:
            logger.error(f"Feature preparation failed: {e}")
            return None

    def predict(self, metrics: dict) -> dict:

        default = {
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "confidence": "unknown",
            "reason": "Model not loaded",
        }

        if not self.loaded:
            return default

        X = self._prepare_features(metrics)
        if X is None:
            return default

        try:

            if self.scaler is not None:
                X_scaled = self.scaler.transform(X)
            else:
                X_scaled = X

            # 1 good, -1 anomaly 
            pred = self.model.predict(X_scaled)[0]


            # normalize to 0,1
            raw_score = self.model.decision_function(X_scaled)[0]
            anomaly_score = float(max(0.0, min(1.0, 0.5 - raw_score)))

            is_anomaly = pred == -1

            # confidence hcc
            if anomaly_score > 0.7:
                confidence = "high"
            elif anomaly_score > 0.5:
                confidence = "medium"
            else:
                confidence = "low"

  
            reason = self._explain(metrics, is_anomaly, anomaly_score)

            result = {
                "is_anomaly": bool(is_anomaly),
                "anomaly_score": round(anomaly_score, 4),
                "confidence": confidence,
                "reason": reason,
            }

            if is_anomaly:
                logger.warning(
                    f"ANOMALY DETECTED — score={anomaly_score:.3f} "
                    f"({confidence}) — {reason}"
                )

            return result

        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return default

    def _explain(self, metrics: dict, is_anomaly: bool, score: float) -> str:

        reasons = []

        latency = metrics.get("latency_avg")
        loss = metrics.get("packet_loss")
        http_time = metrics.get("http_response_time")
        dns_time = metrics.get("dns_time")
        signal = metrics.get("wifi_signal")

        if latency and latency > 200:
            reasons.append(f"high latency ({latency:.0f}ms)")
        if loss and loss > 10:
            reasons.append(f"packet loss ({loss:.1f}%)")
        if http_time and http_time > 2000:
            reasons.append(f"slow HTTP ({http_time:.0f}ms)")
        if dns_time and dns_time > 500:
            reasons.append(f"slow DNS ({dns_time:.0f}ms)")
        if signal and signal < -80:
            reasons.append(f"weak WiFi ({signal}dBm)")

        if not is_anomaly:
            return "Network conditions normal"
        if reasons:
            return "Anomaly: " + ", ".join(reasons)
        return f"Statistical anomaly detected (score={score:.3f})"
