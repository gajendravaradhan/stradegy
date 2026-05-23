#!/bin/bash
# DuckDNS Updater for Stradegy
# Run every 5 minutes via cron to keep DuckDNS in sync with public IP
# Requires DUCKDNS_TOKEN environment variable

set -e

DOMAIN="${DUCKDNS_DOMAIN:-stradegy}"
TOKEN="${DUCKDNS_TOKEN:-}"

if [ -z "$TOKEN" ]; then
    echo "ERROR: DUCKDNS_TOKEN not set. Edit this script or export it in ~/.bashrc"
    exit 1
fi

# Force IPv4
IPV4=$(curl -4 -s --max-time 10 ifconfig.me)
if [ -z "$IPV4" ]; then
    echo "ERROR: Could not determine public IPv4"
    exit 1
fi

# Update DuckDNS
RESPONSE=$(curl -s --max-time 10 "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=${IPV4}")

if [ "$RESPONSE" = "OK" ]; then
    echo "$(date): DuckDNS updated to $IPV4"
else
    echo "$(date): DuckDNS update failed: $RESPONSE"
    exit 1
fi
