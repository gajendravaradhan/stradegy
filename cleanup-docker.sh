#!/bin/bash
set -e

echo "========================================"
echo "Docker Space Cleanup Script"
echo "========================================"
echo ""

echo "Current disk usage:"
df -h /volume1 /root /var 2>/dev/null | head -10
echo ""

echo "Docker disk usage before cleanup:"
docker system df
echo ""

echo "[1/6] Stopping all containers..."
docker stop $(docker ps -q) 2>/dev/null || echo "  No running containers"

echo "[2/6] Removing all containers..."
docker rm $(docker ps -aq) 2>/dev/null || echo "  No containers to remove"

echo "[3/6] Removing all images..."
docker rmi $(docker images -q) --force 2>/dev/null || echo "  No images to remove"

echo "[4/6] Removing all volumes..."
docker volume rm $(docker volume ls -q) --force 2>/dev/null || echo "  No volumes to remove"

echo "[5/6] Removing all networks..."
docker network rm $(docker network ls -q) 2>/dev/null || echo "  No networks to remove"

echo "[6/6] Pruning build cache..."
docker builder prune -f 2>/dev/null || echo "  No build cache to prune"

echo ""
echo "Docker disk usage after cleanup:"
docker system df
echo ""

echo "Disk usage after cleanup:"
df -h /volume1 /root /var 2>/dev/null | head -10
echo ""

echo "========================================"
echo "Cleanup complete. Re-run fix-and-deploy.sh now."
echo "========================================"
