# server.py
import os
import datetime as dt
from functools import wraps
from typing import Dict, Any, List

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import yaml

# Optional local module; app still works without it.
try:
    from gtfs import GTFS  # your real module (if/when present in the image)
except Exception:
    GTFS = None

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
API_KEY = (os.getenv("API_KEY") or "").strip()
LIVE_URL = os.getenv("LIVE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
DEFAULT_MINUTES = int(os.getenv("MINUTES", "30"))
PORT = int(os.getenv("PORT", "8080"))

app = Flask(__name__)
CORS(app)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def require_api_key(fn):
    """Require x-api-key header if API_KEY is set."""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if API_KEY and request.headers.get("x-api-key") != API_KEY:
            # Keep the envelope style you've been using in tests
            return jsonify([{"error": "unauthorized"}, 401]), 200
        return fn(*args, **kwargs)
    return wrapped


def format_response(fn):
    """Return YAML if client asks for it via Accept header."""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        data = fn(*args, **kwargs)
        accept = (request.headers.get("Accept") or "application/json").lower()
        if "application/yaml" in accept or "text/yaml" in accept:
            return Response(
                yaml.dump(data, default_flow_style=False),
                mimetype="application/yaml"
            )
        return jsonify(data)
    return wrapped


_GTFS = None
def get_gtfs():
    """Lazy-init GTFS if available; otherwise raise to trigger fallback."""
    global _GTFS
    if _GTFS is None:
        if GTFS is None or not LIVE_URL:
            raise RuntimeError("GTFS not available yet")
        _GTFS = GTFS(
            live_url=LIVE_URL,
            api_key=API_KEY or None,
            redis_url=REDIS_URL or None,
            filter_stops=None,
            profile_memory=False,
        )
    return _GTFS


def _dummy_arrivals(stops: List[str]) -> Dict[str, Any]:
    """Safe fallback shape until GTFS is fully wired."""
    return {s: {"stop_name": "", "arrivals": []} for s in stops}


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.route("/", methods=["GET"])
def root():
    return "app is running", 200


@app.route("/healthz", methods=["GET"])
def healthz():
    # If you later want to add deeper checks, do them here,
    # but always return 200 so Cloud Run doesn't flap.
    return "ok", 200


@app.route("/api/v1/arrivals", methods=["GET"])
@require_api_key
@format_response
def arrivals():
    # Accept multiple ?stop=... params
    stops = request.args.getlist("stop")
    if not stops:
        return {}

    # Try GTFS; on any error, return a dummy (no 503s)
    try:
        gtfs = get_gtfs()
        now = dt.datetime.now()
        out: Dict[str, Any] = {}
        for s in stops:
            if hasattr(gtfs, "is_valid_stop_number") and not gtfs.is_valid_stop_number(s):
                # keep contract: skip invalids silently
                continue
            stop_name = (
                gtfs.get_stop_name(s) if hasattr(gtfs, "get_stop_name") else ""
            )
            arrivals = []
            if hasattr(gtfs, "get_scheduled_arrivals"):
                arrivals = gtfs.get_scheduled_arrivals(
                    s, now, dt.timedelta(minutes=DEFAULT_MINUTES)
                )
            out[s] = {"stop_name": stop_name, "arrivals": arrivals}
        # If nothing got filled (e.g., GTFS methods missing), fall back
        if not out:
            out = _dummy_arrivals(stops)
        return out
    except Exception:
        # Fallback shape until GTFS is fully wired
        return _dummy_arrivals(stops)


if __name__ == "__main__":
    # Flask dev server is fine on Cloud Run for this tiny app
    app.run(host="0.0.0.0", port=PORT)
