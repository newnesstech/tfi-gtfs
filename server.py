import os
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
        return s  # already a full TFI stop_id
    if s.isdigit():
        return f"8220DB00{int(s):04d}"
    return s
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# --- Config ---
API_KEY = (os.getenv("API_KEY") or "").strip()
DEFAULT_MINUTES = int(os.getenv("MINUTES", "30"))
LIVE_URL = (os.getenv("LIVE_URL") or "").strip()   # e.g. https://tfi-gtfs-XXXX.run.app
USE_FAKE = LIVE_URL == ""                          # fallback to demo data


ROLE = (os.getenv("ROLE") or "core").lower()   # "core" or "public"
LIVE_URL = (os.getenv("LIVE_URL") or "").strip()

def compute_arrivals(stop_id: str, minutes: int):
    stop_raw = (request.args.get("stop") or request.args.get("stopId") or "").strip()
stop = normalize_stop_id(stop_raw)
    """
    If ROLE == 'public' and LIVE_URL is set -> proxy upstream /api/v1/arrivals with x-api-key.
    Otherwise (ROLE == 'core') -> compute locally (for now: demo data).
    """
    if not stop_id:
        return []

    # PUBLIC: proxy to upstream core
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

    # CORE: local compute (replace with your real GTFS logic when ready)
    now = datetime.now(timezone.utc).replace(microsecond=0, second=0)
    return [
        {"route": "9",  "destination": "Charlestown",    "expected": now.isoformat(), "stop_id": stop_id},
        {"route": "16", "destination": "Dublin Airport", "expected": now.isoformat(), "stop_id": stop_id},
        {"route": "68", "destination": "Poolbeg St",     "expected": now.isoformat(), "stop_id": stop_id},
    ]


    # --- live fetch ---
    try:
        url = f"{LIVE_URL}/api/v1/arrivals?stop={stop_id}&minutes={minutes}"
        resp = requests.get(url, headers={"x-api-key": API_KEY}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("arrivals", [])
        else:
            print(f"Upstream error {resp.status_code}: {resp.text}")
            return []
    except Exception as e:
        print(f"Upstream call failed: {e}")
        return []


# --- Routes ---
@app.route("/")
def root():
    return "App is running"


@app.route("/health")
@app.route("/healthz")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/v1/arrivals")
def secure_arrivals():
    stop = (request.args.get("stop") or request.args.get("stopId") or "").strip()
    minutes = int(request.args.get("minutes", DEFAULT_MINUTES))
    header_key = request.headers.get("x-api-key", "")
    if not API_KEY or header_key != API_KEY:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"arrivals": compute_arrivals(stop, minutes)})


@app.route("/public/arrivals")
def public_arrivals():
    stop = (request.args.get("stop") or request.args.get("stopId") or "").strip()
    if not stop:
        return jsonify({"arrivals": []})
    try:
        minutes = int(request.args.get("minutes", DEFAULT_MINUTES))
    except ValueError:
        minutes = DEFAULT_MINUTES
    return jsonify({"arrivals": compute_arrivals(stop, minutes)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
