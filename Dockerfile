# Use a small, secure Python base
FROM python:3.11-slim

# System setup (no cache to keep image small)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Add the app code
COPY . /app

# Add a tiny entrypoint that reads $PORT and starts Waitress
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Cloud Run will pass PORT; expose for local runs too
EXPOSE 8080

# Start with Waitress (no shell to keep PID 1 clean)
CMD ["/entrypoint.sh"]
CMD ["python", "-c", "from server import app; from waitress import serve; serve(app, host='0.0.0.0', port=8080)"]
