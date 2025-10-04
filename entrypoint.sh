#!/usr/bin/env bash
set -euo pipefail

# Cloud Run sets $PORT; default to 8080 for local dev
PORT="${PORT:-8080}"

# Start Waitress serving the Flask app object named "app" in server.py
exec python -m waitress --listen="0.0.0.0:${PORT}" "server:app"
