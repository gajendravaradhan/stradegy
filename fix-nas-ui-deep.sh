#!/bin/bash
set -e

echo "========================================"
echo "UGreen WebUI Deep Fix"
echo "========================================"
echo ""

echo "[1/8] Full status of ugos-web service:"
systemctl status ugos-web --no-pager 2>/dev/null || echo "  ugos-web service not found"
echo ""

echo "[2/8] Full status of nginx service:"
systemctl status nginx --no-pager 2>/dev/null || echo "  nginx service not found"
echo ""

echo "[3/8] Is nginx masked?"
systemctl is-enabled nginx 2>/dev/null || echo "  nginx enable status unknown"
systemctl is-active nginx 2>/dev/null || echo "  nginx is not active"
echo ""

echo "[4/8] Checking if nginx binary exists..."
which nginx 2>/dev/null || find /usr -name nginx -type f 2>/dev/null | head -1 || echo "  nginx binary not found"
echo ""

echo "[5/8] Unmasking and starting nginx..."
systemctl unmask nginx 2>/dev/null || true
systemctl enable nginx 2>/dev/null || true
systemctl start nginx 2>/dev/null || true
sleep 2
echo ""

echo "[6/8] Re-checking port 80..."
netstat -tlnp 2>/dev/null | grep ':80 ' || ss -tlnp 2>/dev/null | grep ':80 ' || echo "  Port 80 still empty"
echo ""

echo "[7/8] If nginx won't start, try direct binary..."
if ! ss -tlnp | grep -q ':80 '; then
    echo "  Nginx not responding. Trying direct start..."
    nginx -t 2>/dev/null || echo "  Nginx config test failed"
    nginx 2>/dev/null &
    sleep 2
    netstat -tlnp 2>/dev/null | grep ':80 ' || echo "  Direct nginx start failed"
fi
echo ""

echo "[8/8] Final test..."
sleep 1
HTTP80=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://localhost:80/ 2>/dev/null || echo "000")
echo "  http://localhost:80/ -> HTTP $HTTP80"
echo ""

echo "========================================"
if [ "$HTTP80" = "200" ] || [ "$HTTP80" = "301" ] || [ "$HTTP80" = "302" ]; then
    echo "SUCCESS! WebUI should now be reachable at:"
    echo "  http://192.168.1.138/"
else
    echo "FAILED. UGreen WebUI service appears damaged."
    echo ""
    echo "LAST RESORT OPTIONS:"
    echo "  1. Reboot NAS from physical power button"
    echo "  2. If reboot fails, factory reset via UGreen mobile app"
    echo "  3. Or: ssh Nasama-Pochu@192.168.1.138 'sudo reboot'"
fi
echo "========================================"
