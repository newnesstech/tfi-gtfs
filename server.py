import os
import datetime as dt
from functools import wraps
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import yaml

# Optional: if gtfs.py exists in your repo
try:
    from gtfs import GTFS
except Exception:
    GTFS = None

# -------- Config --------
API_KEY = os.getenv("API_KEY", "").strip()
LIVE_URL = os.getenv("LIVE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
DEFAULT_MINUTES = int(os.getenv("MINUTES", "30"))

app = Flask(__name__)
CORS(app)

# -------- Helpers --------
def require_api_key(fn):
    """Decorator to enforce API key header"""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if API_KEY and request.headers.get("x-api-key") != API_KEY:
            return jsonify([{"error": "unauthorized"}, 401]), 200
        return fn(*args, **kwargs)
    return wrapped

def format_response(fn):
    """Decorator to allow YAML if Accept header includes application/yaml"""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        data = fn(*args, **kwargs)
        accept = (request.headers.get("Accept") or "application/json").lower()
        if "application/yaml" in accept:
            return Response(yaml.dump(data, default_flow_style=False),
                            mimetype="application/yaml")
        return jsonify(data)
    return wrapped

# Lazy GTFS init
_GTFS = None
def get_gtfs():
    global _GTFS
    if _GTFS is None:
        if GTFS is None:
            raise RuntimeError("gtfs module not available in image")
        _GTFS = GTFS(
            live_url=LIVE_URL or None,
            api_key=API_KEY or None,
            redis_url=REDIS_URL or None,
            filter_stops=None,
            profile_memory=False,
        )
    return _GTFS

# -------- Routes --------
@app.route("/", methods=["GET"])
def root():
    return "app is running", 200

@app.route("/healthz", methods=["GET"])
def healthz():
    return "ok", 200

@app.route("/api/v1/arrivals", methods=["GET"])
@require_api_key
@format_response
def arrivals():
    stops = request.args.getlist("stop")
    if not stops:
        return {}

    try:
        gtfs = get_gtfs()
        now = dt.datetime.now()
        out = {}
        for stop in stops:
            if gtfs.is_valid_stop_number(stop):
                out[stop] = {
                    "stop_name": gtfs.get_stop_name(stop),
                    "arrivals": gtfs.get_scheduled_arrivals(
                        stop, now, dt.timedelta(minutes=DEFAULT_MINUTES)
                    ),
                }
        return out
    except Exception:
        # fallback: empty arrivals so API works even if GTFS not wired yet
        return {s: {"stop_name": "", "arrivals": []} for s in stops}

# -------- Entrypoint --------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
