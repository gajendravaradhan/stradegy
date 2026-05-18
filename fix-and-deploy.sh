#!/bin/bash
set -e

if ! docker info >/dev/null 2>&1; then
    echo "Docker requires elevated permissions. Re-running with sudo..."
    exec sudo bash "$0" "$@"
fi

echo "========================================"
echo "Stradegy NAS Fix & Deploy Script"
echo "========================================"
echo ""

cd /volume1/docker/stradegy

echo "[1/8] Fixing Dockerfile (create /logs, chown /app for non-root user)..."
sed -i 's|mkdir -p /app/data /app/config /app/eval/traces /app/logs|mkdir -p /app/data /app/config /app/eval/traces /logs|' Dockerfile
sed -i 's|chown -R stradegy:stradegy /app/data /app/config /app/eval /app/logs|chown -R stradegy:stradegy /app/data /app/config /app/eval /logs /app|' Dockerfile

echo "[2/8] Removing stale GHCR image reference from docker-compose.yml..."
sed -i '/image: ghcr.io\/gajendravaradhan\/stradegy:latest/d' docker-compose.yml

echo "[3/8] Stopping existing containers..."
docker compose down 2>/dev/null || true

echo "[4/8] Pruning old images to avoid conflicts..."
docker image prune -f 2>/dev/null || true

echo "[5/8] Rebuilding stradegy image (this may take 5-15 minutes)..."
docker compose build --no-cache

echo "[6/8] Starting containers..."
docker compose up -d

echo "[7/8] Waiting for backend to start (max 60s)..."
for i in $(seq 1 30); do
    sleep 2
    HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8420/api/health 2>/dev/null || echo "000")
    if [ "$HEALTH" = "200" ]; then
        echo "  -> Backend is up! (attempt $i)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  -> WARNING: Backend did not become healthy within 60s"
    fi
done

echo ""
echo "[8/8] Running verification checks..."
echo ""

echo "--- Container Status ---"
docker compose ps

echo ""
echo "--- Health Check ---"
curl -s http://localhost:8420/api/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8420/api/health

echo ""
echo "--- Portfolio Metrics (new endpoint) ---"
curl -s http://localhost:8420/api/portfolio/metrics | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8420/api/portfolio/metrics

echo ""
echo "--- Secrets Endpoint (masked) ---"
curl -s http://localhost:8420/api/secrets | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8420/api/secrets

echo ""
echo "========================================"
echo "Deployment Status:"
echo "  Local:     http://192.168.1.138/"
echo "  HTTPS:     https://stradegy.duckdns.org/ (after Caddy cert is ready)"
echo "========================================"
