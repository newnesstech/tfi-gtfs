cat > Dockerfile <<'DOCK'
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "server.py"]
DOCK
