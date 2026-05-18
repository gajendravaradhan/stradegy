#!/bin/bash
set -e

echo "========================================"
echo "Docker Buildx + Root FS Cleanup"
echo "========================================"
echo ""

echo "[1/5] Disk usage overview:"
df -h
echo ""

echo "[2/5] Docker Buildx disk usage:"
docker buildx du 2>/dev/null || echo "  Buildx not available"
echo ""

echo "[3/5] Pruning Docker build cache..."
docker builder prune -af 2>/dev/null || echo "  No build cache to prune"
echo ""

echo "[4/5] Removing Docker buildx metadata..."
rm -rf /root/.docker/buildx/refs/default/* 2>/dev/null || true
rm -rf /root/.docker/buildx/activity/* 2>/dev/null || true
echo ""

echo "[5/5] Checking if /root/.docker is the culprit..."
du -sh /root/.docker 2>/dev/null || echo "  /root/.docker not found"
du -sh /root/ 2>/dev/null || echo "  /root not accessible"
echo ""

echo "========================================"
echo "Now re-run fix-and-deploy.sh"
echo "========================================"
