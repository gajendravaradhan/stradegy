# Deployment — Ugreen NAS + Docker + Cloudflare Tunnel

## Overview

The Stradegy backend runs as a single Docker container on your Ugreen NAS. Your phone
connects to it via Cloudflare Tunnel (secure HTTPS, no port forwarding needed).
The NAS runs 24/7 with minimal power consumption.

## Architecture

```
Internet ──> Cloudflare ──> cloudflared ──> Docker Container (FastAPI :8420)
               Tunnel         (on NAS)      │                 │
               (HTTPS)                       │ Serves API + PWA │
                                             └─────────────────┘
```

---

## Prerequisites

### 1. Ugreen NAS Requirements

Your Ugreen NAS must support Docker. Ugreen NAS devices typically run UGOS (Linux-based)
which supports Docker Engine.

**Verify Docker is available:**
- Open the Ugreen NAS web interface
- Navigate to App Center → search for "Docker"
- Install if not already present

### 2. Cloudflare Account (Free)

Create a free Cloudflare account at https://dash.cloudflare.com/sign-up if you
don't already have one.

### 3. Domain Name (Optional but Recommended)

Cloudflare Tunnel requires a domain name managed by Cloudflare. You have several options:
- **Buy a domain through Cloudflare** ($10-15/year — e.g., `stradegy-bot.com`)
- **Use a free subdomain** from a service like DuckDNS or FreeDNS
- **Use Cloudflare Tunnel with localhost only** (limits remote access — PWA won't work)

---

## Step-by-Step Setup

### Step 1: Prepare the NAS

```bash
# SSH into your Ugreen NAS
ssh admin@<nas-ip-address>

# Create the project directory
mkdir -p /volume1/docker/stradegy
cd /volume1/docker/stradegy

# Create persistent directories
mkdir -p data  # For SQLite database
mkdir -p config  # For settings files
```

### Step 2: Copy the Project to NAS

```bash
# From your development machine
scp -r /path/to/stradegy/* admin@<nas-ip>:/volume1/docker/stradegy/

# Or use git on the NAS
ssh admin@<nas-ip>
cd /volume1/docker/stradegy
# Copy over the project files
```

### Step 3: Configure Environment Variables

```bash
# On the NAS
cd /volume1/docker/stradegy
cp .env.example .env
nano .env  # Fill in your API keys
```

Required environment variables:
```
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
ALPACA_PAPER=true  # Start with paper trading
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
FINNHUB_API_KEY=your_finnhub_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=stradegy/1.0
```

### Step 4: Build and Start the Container

```bash
cd /volume1/docker/stradegy

# Build the Docker image
docker compose build

# Start the container in detached mode
docker compose up -d

# Check logs
docker compose logs -f
```

### Step 5: Set Up Cloudflare Tunnel

```bash
# Install cloudflared on the NAS
# Option A: Docker (recommended — add to docker-compose.yml)
# Option B: Direct install
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Authenticate
cloudflared tunnel login

# Create a tunnel
cloudflared tunnel create stradegy

# Configure the tunnel (config.yml)
# Copy the tunnel credentials to /volume1/docker/stradegy/config/

# Route traffic
cloudflared tunnel route dns stradegy stradegy.yourdomain.com

# Run the tunnel
cloudflared tunnel run stradegy
```

### Step 6: Verify

```bash
# Check container is running
docker compose ps

# Check logs for errors
docker compose logs stradegy

# Test API from your phone browser
# Visit: https://stradegy.yourdomain.com/api/health
# Should return: {"status": "ok"}
```

---

## Docker Compose Configuration

```yaml
# docker-compose.yml
version: "3.8"

services:
  stradegy:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: stradegy
    restart: unless-stopped
    ports:
      - "8420:8420"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
      - ./eval:/app/eval
    env_file:
      - .env
    environment:
      - CONFIG_DIR=/app/config

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: stradegy-tunnel
    restart: unless-stopped
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - ./config/cloudflared:/etc/cloudflared
    depends_on:
      - stradegy
    profiles:
      - production
```

```dockerfile
# Dockerfile (multi-stage build)
# ---- Build Stage ----
FROM node:22-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---- Runtime Stage ----
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./
COPY backend/src/ ./src/
RUN pip install --no-cache-dir .

COPY --from=builder /app/dist /app/frontend/dist

RUN mkdir -p /app/data /app/config /app/eval/traces

EXPOSE 8420

CMD ["python", "-m", "stradegy.main"]
```

---

## Installing the PWA on Your Phone

### Android (Chrome)
1. Open Chrome and visit `https://stradegy.yourdomain.com`
2. Wait a few seconds for the PWA to register
3. Tap the three-dot menu → "Add to Home Screen"
4. Name it "Stradegy" → tap "Add"
5. The app icon appears on your home screen

### iPhone (Safari)
1. Open Safari and visit `https://stradegy.yourdomain.com`
2. Tap the Share button (square with arrow)
3. Scroll down → "Add to Home Screen"
4. Name it "Stradegy" → tap "Add"
5. The app icon appears on your home screen

### PWA Features
- **Offline support:** Last-known data is cached. App shows stale data with "Offline" badge.
- **Push notifications:** Gem alerts delivered even when the app is closed (requires enabling).
- **Full-screen mode:** App opens without browser chrome (address bar hidden).

---

## Auto-Start on NAS Boot

```bash
# Ensure Docker starts on boot
sudo systemctl enable docker

# The docker-compose.yml has restart: unless-stopped
# Containers will auto-start after NAS reboot
```

---

## Maintenance

### Update the Application
```bash
cd /volume1/docker/stradegy
git pull
docker compose down
docker compose build --no-cache
docker compose up -d
```

### View Logs
```bash
docker compose logs -f stradegy  # Real-time
docker compose logs --tail=100 stradegy  # Last 100 lines
```

### Backup Database
```bash
# SQLite is a single file — just copy it
cp /volume1/docker/stradegy/data/stradegy.db \
   /volume1/backup/stradegy_$(date +%Y%m%d).db
```

### Monitor Resource Usage
```bash
docker stats stradegy
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Can't reach the app | Is the container running? `docker compose ps` |
| Cloudflare Tunnel not working | Is cloudflared running? `docker compose logs cloudflared` |
| API errors | Check stradegy logs: `docker compose logs stradegy` |
| Database errors | Check volume mount permissions: `ls -la data/` |
| PWA won't install | Must be served over HTTPS. Check Cloudflare Tunnel. |
