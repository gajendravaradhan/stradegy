#!/bin/bash
# Health Monitor for Stradegy
# Checks if the app is responding and restarts if needed
# Run every minute via cron

HEALTH_URL="http://localhost:8420/api/health"
LOG_FILE="/home/gaja/stradegy/logs/health-monitor.log"

# Check backend health
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" != "200" ]; then
    echo "$(date): Backend unhealthy (HTTP $HTTP_CODE). Restarting..." >> "$LOG_FILE"
    sudo systemctl restart stradegy
    sleep 5
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" 2>/dev/null || echo "000")
    echo "$(date): After restart: HTTP $HTTP_CODE" >> "$LOG_FILE"
fi

# Check Caddy is running
if ! docker ps | grep -q stradegy-caddy; then
    echo "$(date): Caddy container not running. Starting..." >> "$LOG_FILE"
    cd /home/gaja/stradegy && docker compose -f caddy-compose.yml up -d
fi

# Check disk space (warn at 90%)
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "$(date): WARNING: Disk usage at ${DISK_USAGE}%" >> "$LOG_FILE"
    # Clean old logs
    find /home/gaja/stradegy/logs -name "*.log.*" -type f -mtime +7 -delete 2>/dev/null
fi

# Check memory (warn if available < 200MB)
MEM_AVAILABLE=$(free -m | awk '/Mem:/ {print $7}')
if [ "$MEM_AVAILABLE" -lt 200 ]; then
    echo "$(date): WARNING: Low memory. Available: ${MEM_AVAILABLE}MB" >> "$LOG_FILE"
fi
