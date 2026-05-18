#!/bin/bash
set -e

echo "========================================"
echo "Remove Stradegy + Restore UGreen WebUI"
echo "========================================"
echo ""

echo "[1/6] Stopping all Stradegy containers..."
docker stop stradegy stradegy-caddy stradegy-tunnel 2>/dev/null || echo "  No Stradegy containers running"

echo "[2/6] Removing all Stradegy containers..."
docker rm stradegy stradegy-caddy stradegy-tunnel 2>/dev/null || echo "  No Stradegy containers to remove"

echo "[3/6] Removing Stradegy images..."
docker rmi stradegy caddy:2-alpine cloudflare/cloudflared:latest 2>/dev/null || echo "  Images already removed or not found"

echo "[4/6] Pruning Docker build cache and volumes..."
docker builder prune -af 2>/dev/null || true
docker volume prune -f 2>/dev/null || true

echo "[5/6] Verifying ports 80 and 443 are now free..."
FREE_80=$(netstat -tlnp 2>/dev/null | grep ':80 ' | grep -v grep | wc -l || echo "0")
FREE_443=$(netstat -tlnp 2>/dev/null | grep ':443 ' | grep -v grep | wc -l || echo "0")
if [ "$FREE_80" = "0" ] && [ "$FREE_443" = "0" ]; then
    echo "  -> Ports 80 and 443 are now FREE"
else
    echo "  -> WARNING: Something is still using ports 80/443"
    netstat -tlnp 2>/dev/null | grep -E ':80 |:443 ' || true
fi

echo ""
echo "[6/6] Checking UGreen WebUI status..."
if command -v systemctl >/dev/null 2>&1; then
    systemctl status ugos-web 2>/dev/null || systemctl status nginx 2>/dev/null || echo "  UGreen WebUI service status unknown"
    echo ""
    echo "  If WebUI is still unreachable, try restarting it:"
    echo "    sudo systemctl restart ugos-web"
    echo "    sudo systemctl restart nginx"
else
    echo "  systemctl not available — please restart your NAS from the physical power button if WebUI is still unreachable"
fi

echo ""
echo "========================================"
echo "ACTION REQUIRED ON YOUR ROUTER:"
echo "  Remove port forwarding rules for:"
echo "    TCP 80  -> 192.168.1.138"
echo "    TCP 443 -> 192.168.1.138"
echo "========================================"
echo ""
echo "After removing router port forwarding:"
echo "  - Access UGreen NAS WebUI at: http://192.168.1.138/"
echo "  - Or use UGreen's mobile app"
echo ""
echo "To remove Stradegy files from NAS:"
echo "  sudo rm -rf /volume1/docker/stradegy"
echo "========================================"
