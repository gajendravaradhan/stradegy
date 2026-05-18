#!/bin/bash
set -euo pipefail

NAS_IP="192.168.1.138"
NAS_USER="Nasama-Pochu"

echo "========================================"
echo "Stradegy Cloudflare Tunnel Setup"
echo "========================================"
echo ""

read -p "Do you already own a domain? (y/n): " has_domain

if [[ "$has_domain" == "y" || "$has_domain" == "Y" ]]; then
    read -p "Enter your domain (e.g., stradegy.com): " DOMAIN
else
    echo "You need a domain. Options:"
    echo "  1. Buy one at https://dash.cloudflare.com (recommended, ~$10/year)"
    echo "  2. Use a free subdomain from DuckDNS or FreeDNS"
    echo ""
    read -p "Enter the domain you'll use: " DOMAIN
fi

echo ""
echo "Creating Cloudflare tunnel on your NAS..."

ssh -o StrictHostKeyChecking=no "${NAS_USER}@${NAS_IP}" "which cloudflared || (curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb)" 2>/dev/null || true

echo ""
echo "Step 1: Authenticating with Cloudflare..."
echo "A browser window will open. Log in to your Cloudflare account."
read -p "Press Enter when ready..."

ssh -o StrictHostKeyChecking=no "${NAS_USER}@${NAS_IP}" "cloudflared tunnel login" 2>/dev/null || {
    echo "ERROR: Could not authenticate. Make sure cloudflared is installed."
    exit 1
}

TUNNEL_NAME="stradegy"
echo ""
echo "Step 2: Creating tunnel '${TUNNEL_NAME}'..."
TUNNEL_ID=$(ssh -o StrictHostKeyChecking=no "${NAS_USER}@${NAS_IP}" "cloudflared tunnel create ${TUNNEL_NAME} 2>&1 | grep -oP 'Created tunnel \K[^\s]+' || echo ''")

if [ -z "$TUNNEL_ID" ]; then
    echo "Tunnel may already exist. Fetching existing tunnel ID..."
    TUNNEL_ID=$(ssh -o StrictHostKeyChecking=no "${NAS_USER}@${NAS_IP}" "cloudflared tunnel list | grep ${TUNNEL_NAME} | awk '{print \\$1}'")
fi

echo "Tunnel ID: ${TUNNEL_ID}"

echo ""
echo "Step 3: Writing tunnel configuration..."
ssh -o StrictHostKeyChecking=no "${NAS_USER}@${NAS_IP}" "cat > /volume1/docker/stradegy/secrets/cloudflared/config.yml << EOF
tunnel: ${TUNNEL_ID}
credentials-file: /etc/cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: ${DOMAIN}
    service: http://stradegy:8420
  - service: http_status:404
EOF"

ssh -o StrictHostKeyChecking=no "${NAS_USER}@${NAS_IP}" "sudo cp ~/.cloudflared/${TUNNEL_ID}.json /volume1/docker/stradegy/secrets/cloudflared/ && sudo chmod 600 /volume1/docker/stradegy/secrets/cloudflared/${TUNNEL_ID}.json"

echo ""
echo "Step 4: Creating DNS route..."
ssh -o StrictHostKeyChecking=no "${NAS_USER}@${NAS_IP}" "cloudflared tunnel route dns ${TUNNEL_NAME} ${DOMAIN}"

echo ""
echo "Step 5: Starting the tunnel..."
ssh -o StrictHostKeyChecking=no "${NAS_USER}@${NAS_IP}" "cd /volume1/docker/stradegy && sudo docker compose up -d stradegy-tunnel"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Your Stradegy app is now available at:"
echo "  https://${DOMAIN}"
echo ""
echo "To verify it's working:"
echo "  curl https://${DOMAIN}/api/health"
echo ""
