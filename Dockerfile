# Use a slim, fast Python base
FROM python:3.11-slim

# Ensure Python won’t buffer logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create workdir
WORKDIR /app

# Install system deps (minimal)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Copy python deps first to leverage Docker layer cache
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY server.py /app/
# If you have gtfs.py and other modules, copy them too:
# COPY gtfs.py settings.py /app/

# Cloud Run expects the container to listen on $PORT
ENV PORT=8080

# Start the Flask app with gunicorn (robust HTTP server)
# One worker is usually fine for Cloud Run; you can tweak if needed.
RUN pip install --no-cache-dir gunicorn==22.0.0
CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 server:app
