import os
import datetime as dt
from functools import wraps
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import yaml

# Optional local GTFS helper (safe if not present)
try:
    from gtfs import GTFS  # your module, if/when you wire it in
except Exception:
    GTFS = None

# --- Config from env ---
API_KEY = os.getenv("API_KEY", "").strip()
LIVE_URL = os.getenv("LIVE_URL", "").strip()
REDIS_URL = os.getenv("REDIS_URL", "").strip()
DEFAULT_MINUTES = int(os.getenv("MINUTES", "30"))

app = Flask(__name__)
CORS(app)

# --- Decorators ---
def require_api_key(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if API_KEY and request.headers.get("x-api-key") != API_KEY:
            # Contract: still HTTP 200, but body indicates 401
            return jsonify([{"error": "unauthorized"}, 401]), 200
        return fn(*args, **kwargs)
    return wrapped

def format_response(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        data = fn(*args, **kwargs)
        accept = (request.headers.get("Accept") or "application/json").lower()
        if "application/yaml" in accept:
            return Response(yaml.dump(data, default_flow_style=False), mimetype="application/yaml")
        return jsonify(data)
    return wrapped

# --- Lazy GTFS init (optional) ---
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

# --- Routes ---
@app.route("/", methods=["GET"])
def root():
    return "app is running", 200

@app.route("/healthz", methods=["GET"])
def healthz():
    # lightweight OK so Cloud Run health checks pass immediately
    return "ok", 200

@app.route("/api/v1/arrivals", methods=["GET"])
@require_api_key
@format_response
def arrivals():
    # Query shape: /api/v1/arrivals?stop=7602&stop=7603
    stops = request.args.getlist("stop")
    if not stops:
        return {}

    # If GTFS module not available yet, return stable empty structure
    if GTFS is None:
        return {s: {"stop_name": "", "arrivals": []} for s in stops}

    # Otherwise try real data
    try:
        gtfs = get_gtfs()
        now = dt.datetime.now()
        out = {}
        for stop in stops:
            try:
                if gtfs.is_valid_stop_number(stop):
                    out[stop] = {
                        "stop_name": gtfs.get_stop_name(stop),
                        "arrivals": gtfs.get_scheduled_arrivals(
                            stop, now, dt.timedelta(minutes=DEFAULT_MINUTES)
                        ),
                    }
                else:
                    out[stop] = {"stop_name": "", "arrivals": []}
            except Exception:
                out[stop] = {"stop_name": "", "arrivals": []}
        return out
    except Exception:
        # Fallback so API remains stable
        return {s: {"stop_name": "", "arrivals": []} for s in stops}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
