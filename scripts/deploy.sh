#!/bin/bash
set -e

echo "=== Stradegy Deployment Script ==="
echo ""

echo "[1/4] Building frontend..."
cd frontend
npm install
npm run build
cd ..

VM_USER="${VM_USER:-root}"
VM_HOST="${VM_HOST:-stradegy.duckdns.org}"
VM_PATH="${VM_PATH:-/opt/stradegy}"

echo "[2/4] Syncing to VM ($VM_USER@$VM_HOST:$VM_PATH)..."
rsync -avz --exclude='.venv' --exclude='node_modules' --exclude='.git' \
  --exclude='logs' --exclude='data/*.db' --exclude='eval' \
  backend/ $VM_USER@$VM_HOST:$VM_PATH/backend/

rsync -avz frontend/dist/ $VM_USER@$VM_HOST:$VM_PATH/frontend/dist/

echo "[3/4] Restarting backend on VM..."
ssh $VM_USER@$VM_HOST "cd $VM_PATH/backend && source .venv/bin/activate && pip install -e . > /dev/null 2>&1 && sudo systemctl restart stradegy"

echo "[4/4] Deployment complete!"
echo ""
echo "App: https://stradegy.duckdns.org"
echo ""
echo "Post-deployment:"
echo "  1. Verify FINNHUB_API_KEY, ALPACA_API_KEY, ALPACA_SECRET_KEY in backend/.env"
echo "  2. Run: curl https://stradegy.duckdns.org/api/health"
echo "  3. Logs: ssh $VM_USER@$VM_HOST 'tail -f $VM_PATH/logs/stradegy.log'"
