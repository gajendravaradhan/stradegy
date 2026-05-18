#!/bin/bash
set -e

echo "========================================"
echo "UGreen NAS WebUI Recovery"
echo "========================================"
echo ""

echo "[1/10] Checking what is listening on port 80..."
netstat -tlnp 2>/dev/null | grep ':80 ' || ss -tlnp 2>/dev/null | grep ':80 ' || echo "  No process found on port 80"
echo ""

echo "[2/10] Checking what is listening on port 443..."
netstat -tlnp 2>/dev/null | grep ':443 ' || ss -tlnp 2>/dev/null | grep ':443 ' || echo "  No process found on port 443"
echo ""

echo "[3/10] Checking what is listening on port 5000..."
netstat -tlnp 2>/dev/null | grep ':5000 ' || ss -tlnp 2>/dev/null | grep ':5000 ' || echo "  No process found on port 5000"
echo ""

echo "[4/10] Checking all Docker containers (should be none)..."
docker ps -a 2>/dev/null || echo "  Docker not available or no containers"
echo ""

echo "[5/10] Checking UGreen WebUI services..."
for svc in ugos-web nginx apache2 httpd lighttpd caddy ugreen ugos; do
    systemctl status $svc 2>/dev/null | head -3 && echo "  -> Found service: $svc" && break
done
echo ""

echo "[6/10] Checking if UGreen WebUI uses a custom port..."
grep -r "listen.*80" /etc/nginx/ 2>/dev/null | head -3 || true
grep -r "listen.*443" /etc/nginx/ 2>/dev/null | head -3 || true
echo ""

echo "[7/10] Killing any process still using port 80..."
PID80=$(lsof -t -i:80 2>/dev/null || fuser 80/tcp 2>/dev/null || echo "")
if [ -n "$PID80" ]; then
    echo "  Killing PID(s): $PID80"
    kill -9 $PID80 2>/dev/null || true
else
    echo "  Port 80 is clear"
fi
echo ""

echo "[8/10] Killing any process still using port 443..."
PID443=$(lsof -t -i:443 2>/dev/null || fuser 443/tcp 2>/dev/null || echo "")
if [ -n "$PID443" ]; then
    echo "  Killing PID(s): $PID443"
    kill -9 $PID443 2>/dev/null || true
else
    echo "  Port 443 is clear"
fi
echo ""

echo "[9/10] Restarting all web services..."
for svc in ugos-web nginx apache2 httpd lighttpd caddy ugreen ugos; do
    if systemctl is-active $svc >/dev/null 2>&1; then
        echo "  Restarting $svc..."
        systemctl restart $svc 2>/dev/null || true
    fi
done
echo ""

echo "[10/10] Testing access..."
sleep 2
HTTP200=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:80/ 2>/dev/null || echo "000")
HTTP5000=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:5000/ 2>/dev/null || echo "000")

echo "  http://localhost:80/     -> HTTP $HTTP200"
echo "  http://localhost:5000/   -> HTTP $HTTP5000"
echo ""

echo "========================================"
echo "DIAGNOSIS:"
if [ "$HTTP200" = "200" ] || [ "$HTTP200" = "301" ] || [ "$HTTP200" = "302" ]; then
    echo "  -> WebUI is responding on port 80"
    echo "  -> Try: http://192.168.1.138/"
elif [ "$HTTP5000" = "200" ]; then
    echo "  -> WebUI is responding on port 5000"
    echo "  -> Try: http://192.168.1.138:5000/"
else
    echo "  -> WebUI is NOT responding locally"
    echo "  -> The UGreen WebUI service may be crashed or disabled"
    echo ""
    echo "  NEXT STEPS:"
    echo "    1. Check UGreen's mobile app - can you see the NAS?"
    echo "    2. Reboot NAS from physical power button"
    echo "    3. After reboot, try: http://192.168.1.138:5000/"
    echo "    4. If still down, factory reset may be needed"
fi
echo ""
echo "  IMPORTANT: Remove port forwarding from your router:"
echo "    Delete TCP 80  -> 192.168.1.138"
echo "    Delete TCP 443 -> 192.168.1.138"
echo "========================================"
