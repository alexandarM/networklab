# Generate random data

import os
import csv
import random
import math
import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
TRAIN_FILE = os.path.join(OUTPUT_DIR, "training_data.csv")
TEST_FILE  = os.path.join(OUTPUT_DIR, "test_data.csv")

FEATURES = [
    "timestamp", "latency_avg", "latency_std", "latency_min", "latency_max",
    "packet_loss", "http_response_time", "bytes_sent_rate", "bytes_recv_rate",
    "dns_time", "wifi_signal", "is_anomaly",
]


def generate_normal_sample(ts: str) -> dict:

    lat_avg = random.gauss(35, 10)   
    lat_std = random.uniform(1, 8)
    lat_min = max(1, lat_avg - lat_std * 2)
    lat_max = lat_avg + lat_std * 2

    return {
        "timestamp":         ts,
        "latency_avg":       round(max(5, lat_avg), 2),
        "latency_std":       round(max(0.5, lat_std), 2),
        "latency_min":       round(lat_min, 2),
        "latency_max":       round(lat_max, 2),
        "packet_loss":       round(max(0, random.gauss(0.5, 0.5)), 2),
        "http_response_time": round(random.uniform(80, 600), 1),
        "bytes_sent_rate":   round(random.uniform(100, 50000), 0),
        "bytes_recv_rate":   round(random.uniform(500, 500000), 0),
        "dns_time":          round(random.uniform(15, 120), 1),
        "wifi_signal":       random.randint(-65, -40),
        "is_anomaly":        0,
    }


def generate_anomaly_sample(ts: str, anomaly_type: int = None) -> dict:

    sample = generate_normal_sample(ts)
    sample["is_anomaly"] = 1

    atype = anomaly_type or random.randint(0, 4)

    if atype == 0:
        # Latency spike
        sample["latency_avg"]  = round(random.uniform(200, 800), 2)
        sample["latency_std"]  = round(random.uniform(30, 100), 2)
        sample["latency_max"]  = sample["latency_avg"] + sample["latency_std"] * 3
    elif atype == 1:
        # Packet loss
        sample["packet_loss"]  = round(random.uniform(15, 100), 1)
        sample["latency_avg"]  = round(random.uniform(80, 300), 2)
    elif atype == 2:
        # HTTP degradation
        sample["http_response_time"] = round(random.uniform(2000, 8000), 1)
        sample["dns_time"]           = round(random.uniform(400, 2000), 1)
    elif atype == 3:
        # Poor WiFi
        sample["wifi_signal"] = random.randint(-95, -80)
        sample["latency_avg"] = round(random.uniform(100, 400), 2)
        sample["packet_loss"] = round(random.uniform(5, 30), 1)
    elif atype == 4:
        # Traffic flood
        sample["bytes_recv_rate"] = round(random.uniform(5e6, 20e6), 0)
        sample["bytes_sent_rate"] = round(random.uniform(2e6, 10e6), 0)

    return sample


def generate_dataset(n_samples: int, anomaly_ratio: float = 0.05) -> list:

    samples = []
    base_time = datetime.datetime(2025, 1, 1, 0, 0, 0)

    for i in range(n_samples):
        ts = (base_time + datetime.timedelta(seconds=30 * i)).isoformat() + "Z"
        is_anomaly = random.random() < anomaly_ratio
        if is_anomaly:
            samples.append(generate_anomaly_sample(ts))
        else:
            samples.append(generate_normal_sample(ts))

    return samples


def write_csv(filepath: str, samples: list):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURES)
        writer.writeheader()
        writer.writerows(samples)
    print(f"Written: {filepath} ({len(samples)} rows)")


if __name__ == "__main__":
    print("Generating sample network data for ML training")
    print()

    random.seed(42)

    # Training set: 2000 samples, 5% anomalies
    train = generate_dataset(2000, anomaly_ratio=0.05)
    write_csv(TRAIN_FILE, train)

    # Test set: 400 samples, 15% anomalies (harder)
    test = generate_dataset(400, anomaly_ratio=0.15)
    write_csv(TEST_FILE, test)

    n_train_anomalies = sum(s["is_anomaly"] for s in train)
    n_test_anomalies  = sum(s["is_anomaly"] for s in test)

    print()
    print("Dataset summary:")
    print(f"  Training: {len(train)} samples, {n_train_anomalies} anomalies "
          f"({n_train_anomalies/len(train)*100:.1f}%)")
    print(f"  Test:     {len(test)} samples, {n_test_anomalies} anomalies "
          f"({n_test_anomalies/len(test)*100:.1f}%)")
    print()
    print("Next step:")
    print("  python ml/train.py")
