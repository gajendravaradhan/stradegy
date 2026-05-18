#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Stradegy Deployment Script ==="
echo ""

deploy_local() {
    echo "[1/4] Pulling latest code from GitHub..."
    git pull origin main

    echo "[2/4] Stopping existing containers..."
    docker compose down

    echo "[3/4] Building new image locally..."
    docker compose build --no-cache

    echo "[4/4] Starting containers..."
    docker compose up -d

    echo ""
    echo "=== Deployment Complete ==="
    echo "App should be available at:"
    echo "  - Local:    http://localhost:8420"
    echo "  - HTTPS:    https://stradegy.duckdns.org"
    echo ""
    echo "Check status: docker compose ps"
    echo "View logs:    docker compose logs -f stradegy"
}

deploy_pull() {
    echo "[1/3] Pulling latest pre-built image from GitHub Container Registry..."
    docker compose pull

    echo "[2/3] Stopping existing containers..."
    docker compose down

    echo "[3/3] Starting containers..."
    docker compose up -d

    echo ""
    echo "=== Deployment Complete ==="
    echo "App should be available at:"
    echo "  - Local:    http://localhost:8420"
    echo "  - HTTPS:    https://stradegy.duckdns.org"
    echo ""
    echo "Check status: docker compose ps"
    echo "View logs:    docker compose logs -f stradegy"
}

show_help() {
    echo "Usage: $0 [local|pull|help]"
    echo ""
    echo "  local  - Pull latest code from GitHub and build image locally (default)"
    echo "  pull   - Pull pre-built image from GitHub Container Registry (faster)"
    echo "  help   - Show this help message"
    echo ""
    echo "Prerequisites:"
    echo "  - Docker and Docker Compose installed on the NAS"
    echo "  - For 'local': Git must be configured and repo cloned"
    echo "  - For 'pull': NAS must have internet access to ghcr.io"
    echo "  - secrets/.env must contain valid API keys"
}

case "${1:-local}" in
    local)
        deploy_local
        ;;
    pull)
        deploy_pull
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
