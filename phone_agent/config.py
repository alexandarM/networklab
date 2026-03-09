# Edit SERVER_URL to match your laptop's local IP address

# Server
SERVER_URL = "http://192.168.1.105:5000"   # CHANGE to your PCs IP 
API_ENDPOINT = "/api/metrics"
SEND_INTERVAL = 30       # seconds between each data push to server

# Device 
DEVICE_ID = "huawei-y6-2018"

# ── Ping targets ───────────────────────────────────────────
PING_TARGETS = [
    "8.8.8.8",        # Google DNS
    "1.1.1.1",        # Cloudflare DNS
    "9.9.9.9",        # Quad9
]
PING_COUNT = 5         # pings per target per cycle
PING_TIMEOUT = 3       # seconds

# HTTP probe targets 
HTTP_TARGETS = [
    "https://www.google.com",
    "https://www.cloudflare.com",
    "https://httpbin.org/get",
]
HTTP_TIMEOUT = 5       # seconds

# DNS probe targets 
DNS_TARGETS = [
    "google.com",
    "cloudflare.com",
    "github.com",
]
DNS_SERVER = "8.8.8.8"

# ML model 
MODEL_PATH = "inference/anomaly_model.pkl"
SCALER_PATH = "inference/scaler.pkl"

# Logging 
LOG_LEVEL = "INFO"     # DEBUG | INFO | WARNING | ERROR
LOG_FILE = "agent.log"

# Feature names (same order as training feats) 
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
