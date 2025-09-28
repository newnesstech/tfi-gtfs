import os
import datetime as dt
from functools import wraps
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import yaml

# Optional local module; app still works without it
try:
    from gtfs import GTFS
except Exception:
    GTFS = None

# Environment variables
API_KEY = os.getenv("API_KEY", "").strip()
LIVE_URL = os.getenv("LIVE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
DEFAULT_MINUTES = int(os.getenv("MINUTES", "30"))

# Flask app setup
app = Flask(__name__)
CORS(app)

# API key check decorator
def require_api_key(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if API_KEY and request.headers.get("x-api-key") != API_KEY:
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapped

# Root route
@app.route("/")
def index():
    return "app is running"

# Health check route
@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

# API route: arrivals
@app.route("/api/v1/arrivals")
@require_api_key
def arrivals():
    stop_ids = request.args.getlist("stop")
    minutes = int(request.args.get("minutes", DEFAULT_MINUTES))

    # Example response (replace with GTFS logic if needed)
    arrivals_data = []
    now = dt.datetime.utcnow()
    for stop in stop_ids:
        arrivals_data.append({
            "stop_id": stop,
            "arrivals": [
                {
                    "route": "100",
                    "destination": "Downtown",
                    "expected": (now + dt.timedelta(minutes=5)).isoformat()
                },
                {
                    "route": "200",
                    "destination": "Airport",
                    "expected": (now + dt.timedelta(minutes=12)).isoformat()
                }
            ]
        })
    return jsonify(arrivals_data)

# API route: config (returns YAML)
@app.route("/api/v1/config")
@require_api_key
def config():
    config_data = {
        "live_url": LIVE_URL,
        "redis_url": REDIS_URL,
        "minutes": DEFAULT_MINUTES
    }
    return Response(yaml.dump(config_data), mimetype="application/x-yaml")

# Entrypoint
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
