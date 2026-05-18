#!/bin/bash
set -e

echo "========================================"
echo "Stradegy VM Quick Setup"
echo "========================================"
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS. This script supports Ubuntu/Debian."
    exit 1
fi

echo "[1/7] Detected OS: $OS"
echo ""

# Install Docker
echo "[2/7] Installing Docker..."
if ! command -v docker >/dev/null 2>&1; then
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y ca-certificates curl gnupg
            install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            chmod a+r /etc/apt/keyrings/docker.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            systemctl start docker
            systemctl enable docker
            ;;
        *)
            echo "Unsupported OS: $OS"
            echo "Please install Docker manually: https://docs.docker.com/engine/install/"
            exit 1
            ;;
    esac
else
    echo "  Docker already installed"
fi

# Add current user to docker group
echo "[3/7] Adding user to docker group..."
usermod -aG docker $SUDO_USER 2>/dev/null || true

echo "[4/7] Cloning Stradegy repository..."
STRADEGY_DIR="/opt/stradegy"
if [ -d "$STRADEGY_DIR/.git" ]; then
    cd "$STRADEGY_DIR"
    git pull origin main
else
    git clone https://github.com/gajendravaradhan/stradegy.git "$STRADEGY_DIR"
fi

echo "[5/7] Setting up secrets..."
mkdir -p "$STRADEGY_DIR/secrets"
if [ ! -f "$STRADEGY_DIR/secrets/.env" ]; then
    cp "$STRADEGY_DIR/.env.example" "$STRADEGY_DIR/secrets/.env"
    chmod 600 "$STRADEGY_DIR/secrets/.env"
    echo "  Created secrets/.env from template. EDIT THIS FILE WITH YOUR API KEYS."
fi

echo "[6/7] Building and starting Stradegy..."
cd "$STRADEGY_DIR"
docker compose -f docker-compose.vm.yml up -d --build

echo "[7/7] Waiting for health check..."
for i in $(seq 1 30); do
    sleep 2
    HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8420/api/health 2>/dev/null || echo "000")
    if [ "$HEALTH" = "200" ]; then
        echo "  -> Stradegy is up and healthy!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  -> WARNING: Health check failed. Check logs: docker compose -f docker-compose.vm.yml logs"
    fi
done

VM_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================"
echo "Stradegy VM Setup Complete!"
echo ""
echo "Access Stradegy:"
echo "  - From VM:     http://localhost:8420"
echo "  - From host:   http://$VM_IP:8420"
echo ""
echo "IMPORTANT: Edit your API keys first!"
echo "  sudo nano $STRADEGY_DIR/secrets/.env"
echo "  Then restart: docker compose -f docker-compose.vm.yml restart"
echo ""
echo "Management commands:"
echo "  cd $STRADEGY_DIR"
echo "  docker compose -f docker-compose.vm.yml logs -f    # View logs"
echo "  docker compose -f docker-compose.vm.yml down         # Stop"
echo "  docker compose -f docker-compose.vm.yml up -d        # Start"
echo "========================================"
