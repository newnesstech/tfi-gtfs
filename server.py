import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# -------- helpers --------
def normalize_stop_id(s: str) -> str:
    """
    Accept short pole codes like '1348' and convert to a full TFI stop_id.
    Dublin Bus pattern is '8220DB00' + 4-digit, zero-padded.
    If the caller already passes a full id (starts with 8220), return as-is.
    """
    s = (s or "").strip()
    if not s:
        return s
    if s.startswith("8220"):
        return s  # already full TFI stop_id
    if s.isdigit():
        return f"8220DB00{int(s):04d}"
    return s

# -------- app setup --------
app = Flask(__name__)
CORS(app)

API_KEY = (os.getenv("API_KEY") or "").strip()
DEFAULT_MINUTES = int(os.getenv("MINUTES", "30"))

# mode:
#   ROLE=public  -> this service proxies to a "core" upstream
#   ROLE=core    -> this service computes locally (here: demo data placeholder)
ROLE = (os.getenv("ROLE") or "core").lower()
LIVE_URL = (os.getenv("LIVE_URL") or "").strip()  # upstream base URL when ROLE=public

# -------- core logic --------
def compute_arrivals(stop_id: str, minutes: int):
    """
    Return a list of dicts: [{route, destination, expected (ISO), stop_id}, ...]
    """
    if not stop_id:
        return []

    # PUBLIC role: proxy to upstream /api/v1/arrivals
    if ROLE == "public" and LIVE_URL:
        try:
            url = f"{LIVE_URL}/api/v1/arrivals?stop={stop_id}&minutes={minutes}"
            r = requests.get(url, headers={"x-api-key": API_KEY}, timeout=10)
            if r.status_code == 200:
                return r.json().get("arrivals", [])
            print("Upstream error:", r.status_code, r.text)
            return []
        except Exception as e:
            print("Upstream call failed:", e)
            return []

    # CORE role: local compute (replace with your real GTFS logic later)
    now = datetime.now(timezone.utc).replace(microsecond=0, second=0)
    return [
        {"route": "9",  "destination": "Charlestown",    "expected": now.isoformat(), "stop_id": stop_id},
        {"route": "16", "destination": "Dublin Airport", "expected": now.isoformat(), "stop_id": stop_id},
        {"route": "68", "destination": "Poolbeg St",     "expected": now.isoformat(), "stop_id": stop_id},
    ]

# -------- routes --------
@app.route("/")
def root():
    return "App is running"

@app.route("/health")
@app.route("/healthz")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/api/v1/arrivals")
def secure_arrivals():
    # normalize the stop id here
    stop_raw = (request.args.get("stop") or request.args.get("stopId") or "").strip()
    stop = normalize_stop_id(stop_raw)
    try:
        minutes = int(request.args.get("minutes", DEFAULT_MINUTES))
    except ValueError:
        minutes = DEFAULT_MINUTES

    # API key required
    header_key = request.headers.get("x-api-key", "")
    if not API_KEY or header_key != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({"arrivals": compute_arrivals(stop, minutes)})

@app.route("/public/arrivals")
def public_arrivals():
    # normalize the stop id here
    stop_raw = (request.args.get("stop") or request.args.get("stopId") or "").strip()
    stop = normalize_stop_id(stop_raw)
    try:
        minutes = int(request.args.get("minutes", DEFAULT_MINUTES))
    except ValueError:
        minutes = DEFAULT_MINUTES

    return jsonify({"arrivals": compute_arrivals(stop, minutes)})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
