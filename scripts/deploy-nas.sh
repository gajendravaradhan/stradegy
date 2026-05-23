#!/bin/bash
set -euo pipefail

NAS_IP="${NAS_IP:-192.168.1.100}"
NAS_SSH_PORT="${NAS_SSH_PORT:-22}"
NAS_USER="${NAS_USER:-admin}"
NAS_PATH="${NAS_PATH:-/volume1/docker/stradegy}"

SSH_CMD="ssh -p $NAS_SSH_PORT"
RSYNC_RSH="ssh -p $NAS_SSH_PORT"

echo "=== Stradegy NAS Docker Deployment ==="
echo "Target: $NAS_USER@$NAS_IP (port $NAS_SSH_PORT)"
echo "Path:   $NAS_PATH"
echo ""

echo "[1/5] Creating remote directory structure..."
$SSH_CMD $NAS_USER@$NAS_IP "mkdir -p $NAS_PATH/{data,logs,config,eval}"

echo "[2/5] Copying project files to NAS..."
rsync -avz -e "$RSYNC_RSH" \
  --exclude='.venv' --exclude='node_modules' --exclude='.git' \
  --exclude='__pycache__' --exclude='.pytest_cache' \
  --exclude='*.pyc' --exclude='frontend/.vite' \
  . $NAS_USER@$NAS_IP:$NAS_PATH/

echo "[3/5] Checking environment file..."
$SSH_CMD $NAS_USER@$NAS_IP "
  if [ ! -f $NAS_PATH/backend/.env ]; then
    echo 'WARNING: backend/.env not found. Copying from .env.example...'
    cp $NAS_PATH/.env.example $NAS_PATH/backend/.env
    echo 'Please edit $NAS_PATH/backend/.env with your API keys!'
  fi
"

echo "[4/5] Building and starting containers..."
$SSH_CMD $NAS_USER@$NAS_IP "cd $NAS_PATH && docker compose up -d --build"

echo "[5/5] Waiting for health check..."
sleep 15
HEALTH=$($SSH_CMD $NAS_USER@$NAS_IP "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/health" 2>/dev/null || echo "000")

if [ "$HEALTH" = "200" ]; then
  echo ""
  echo "Deployment successful!"
  echo ""
  echo "Access the app at:"
  echo "  http://$NAS_IP:3000"
  echo ""
  echo "View logs:"
  echo "  $SSH_CMD $NAS_USER@$NAS_IP 'cd $NAS_PATH && docker compose logs -f stradegy'"
else
  echo ""
  echo "WARNING: Health check returned HTTP $HEALTH"
  echo "Check docker build status:"
  echo "  $SSH_CMD $NAS_USER@$NAS_IP 'cd $NAS_PATH && docker compose ps'"
  echo "Check logs:"
  echo "  $SSH_CMD $NAS_USER@$NAS_IP 'cd $NAS_PATH && docker compose logs stradegy'"
  exit 1
fi
