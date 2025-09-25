# Minimal Cloud Run–friendly Flask server for GTFS arrivals

import os
import datetime
from functools import wraps
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import yaml

from gtfs import GTFS  # uses your existing module

# --- Environment ---
API_KEY = os.getenv("API_KEY", "")            # set on Cloud Run
LIVE_URL = os.getenv("LIVE_URL")              # optional
REDIS_URL = os.getenv("REDIS_URL")            # optional
DEFAULT_MINUTES = int(os.getenv("MINUTES", "30"))

# --- App setup ---
app = Flask(__name__)
CORS(app)

# Lazy singleton for GTFS so we only init once
_GTFS = None
def get_gtfs() -> GTFS:
    global _GTFS
    if _GTFS is None:
        _GTFS = GTFS(
            live_url=LIVE_URL,
            api_key=API_KEY,
            redis_url=REDIS_URL,
            filter_stops=None,
            profile_memory=False,
        )
    return _GTFS

# Utility: content negotiation for a plain dict
def format_response(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        data = fn(*args, **kwargs)
        accept = request.headers.get("Accept", "application/json")
        if "application/yaml" in accept:
            return Response(yaml.dump(data, default_flow_style=False),
                            mimetype="application/yaml")
        elif "text/plain" in accept:
            # very simple text view
            lines = []
            for stop_no, stop in data.items():
                for arr in stop["arrivals"]:
                    lines.append(
                        f'{stop_no} | {stop["stop_name"]} | {arr["route"]} '
                        f'{arr["headsign"]} | {arr["agency"]} | '
                        f'{arr["scheduled_arrival"]} | {arr.get("real_time_arrival")}'
                    )
            return Response("\n".join(lines), mimetype="text/plain")
        else:
            return jsonify(data)
    return wrapped

# --- Health & probe ---
@app.route("/")
def index():
    return "app is running", 200

@app.route("/healthz")
def healthz():
    return "ok", 200

# --- API ---
@app.route("/api/v1/arrivals")
@format_response
def arrivals():
    # simple API key check
    if request.headers.get("x-api-key") != API_KEY:
        return {"error": "unauthorized"}, 401

    gtfs = get_gtfs()
    now = datetime.datetime.now()
    minutes = DEFAULT_MINUTES

    stop_numbers = request.args.getlist("stop")
    out = {}
    for stop in stop_numbers:
        if gtfs.is_valid_stop_number(stop):
            out[stop] = {
                "stop_name": gtfs.get_stop_name(stop),
                "arrivals": gtfs.get_scheduled_arrivals(
                    stop, now, datetime.timedelta(minutes=minutes)
                ),
            }
    return out

# --- Cloud Run entrypoint ---
if __name__ == "__main__":
    # Cloud Run provides PORT env var
    port = int(os.getenv("PORT", "8080"))
    # Bind to 0.0.0.0 so Cloud Run can reach it
    app.run(host="0.0.0.0", port=port)
