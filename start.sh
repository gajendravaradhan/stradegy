#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_PORT=8420
HEALTH_URL="http://localhost:$BACKEND_PORT/api/health"
BACKEND_PID=""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}Done.${NC}"
    exit 0
}

trap cleanup INT TERM EXIT

echo -e "${GREEN}Starting Stradegy...${NC}"

if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}Backend directory not found at $BACKEND_DIR${NC}"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}Frontend directory not found at $FRONTEND_DIR${NC}"
    exit 1
fi

if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    cd "$BACKEND_DIR"
    python3 -m venv .venv
    .venv/bin/pip install -e .
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not found. Installing...${NC}"
    cd "$FRONTEND_DIR"
    npm install
fi

echo -e "${GREEN}Starting backend on port $BACKEND_PORT...${NC}"
cd "$BACKEND_DIR"
.venv/bin/python -m stradegy.main &
BACKEND_PID=$!

echo -n "Waiting for backend"
for i in {1..60}; do
    if curl -s "$HEALTH_URL" >/dev/null 2>&1; then
        echo -e "\n${GREEN}Backend ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
    if [ $i -eq 60 ]; then
        echo ""
        echo -e "${RED}Backend failed to start within 60 seconds${NC}"
        exit 1
    fi
done

echo -e "${GREEN}Starting frontend dev server...${NC}"
cd "$FRONTEND_DIR"
npm run dev
