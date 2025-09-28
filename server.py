import os, datetime
from functools import wraps
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import yaml
from gtfs import GTFS

API_KEY = os.getenv("API_KEY", "")
LIVE_URL = os.getenv("LIVE_URL")
REDIS_URL = os.getenv("REDIS_URL")
DEFAULT_MINUTES = int(os.getenv("MINUTES", "30"))

app = Flask(__name__)
CORS(app)

_GTFS = None
def get_gtfs():
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

def format_response(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        data = fn(*args, **kwargs)
        accept = (request.headers.get("Accept") or "application/json").lower()
        if "application/yaml" in accept:
            return Response(yaml.dump(data, default_flow_style=False),
                            mimetype="application/yaml")
        return jsonify(data)
    return wrapped

@app.route("/")
def root():
    return "app is running"

@app.route("/healthz")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/v1/arrivals")
@format_response
def arrivals():
    if request.headers.get("x-api-key") != API_KEY:
        return {"error": "unauthorized"}, 401
    stops = request.args.getlist("stop")
    minutes = int(request.args.get("minutes", DEFAULT_MINUTES))
    gtfs = get_gtfs()
    return gtfs.get_arrivals(stops, datetime.timedelta(minutes=minutes))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
