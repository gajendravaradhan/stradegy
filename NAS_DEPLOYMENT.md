# NAS Docker Deployment Guide

Deploy Stradegy on your Ugreen NAS using Docker without impacting the Ugreen WebUI.

## Architecture

```
Phone/Computer ──> NAS IP:3000 ──> Docker ──> Stradegy (:8420)
                    (HTTP)        (Internal)
```

Port 3000 is used to avoid conflicts with the Ugreen WebUI (ports 80/443).

## Prerequisites

- Ugreen NAS with Docker support
- SSH access to your NAS
- API keys: Alpaca, Finnhub, Discord (optional)

## Quick Start

### 1. SSH into your NAS

```bash
ssh admin@<your-nas-ip>
```

### 2. Create deployment directory

```bash
mkdir -p /volume1/docker/stradegy
cd /volume1/docker/stradegy
```

### 3. Copy the project

From your computer:

```bash
cd /path/to/stradegy
chmod +x scripts/deploy-nas.sh
NAS_IP=<your-nas-ip> ./scripts/deploy-nas.sh
```

Or manually via SCP:

```bash
cd /path/to/stradegy
rsync -avz --exclude='.venv' --exclude='node_modules' --exclude='.git' \
  . admin@<your-nas-ip>:/volume1/docker/stradegy/
```

### 4. Configure environment variables

```bash
ssh admin@<your-nas-ip>
cd /volume1/docker/stradegy
cp .env.example backend/.env
nano backend/.env
```

Fill in at minimum:

```env
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
PAPER_TRADING=true
FINNHUB_API_KEY=your_finnhub_key

DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_USER_ID=your_discord_user_id
DISCORD_GENERAL_CHANNEL_ID=your_general_channel_id
DISCORD_CHANNEL_IDS=your_scanning_channel_id
```

### 5. Start the app

Option A: Simple HTTP on port 3000
```bash
cd /volume1/docker/stradegy
docker compose -f docker-compose.simple.yml up -d --build
```

Option B: HTTP on port 3000 + HTTPS on port 8443 (with Caddy)
```bash
cd /volume1/docker/stradegy
docker compose up -d --build
```

### 6. Verify deployment

```bash
curl http://<your-nas-ip>:3000/api/health
```

Expected response: `{"status":"ok","version":"2.0.0"}`

### 7. Access the app

Open your browser to:
- `http://<your-nas-ip>:3000`
- Or `https://<your-nas-ip>:8443` (if using Caddy option)

## Port Reference

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | Stradegy HTTP | Main app access (does not conflict with Ugreen WebUI) |
| 8443 | Caddy HTTPS | Optional HTTPS access (does not conflict with Ugreen WebUI on 443) |
| 8420 | Internal | Container internal port, not exposed to host |

## Maintenance

### View logs
```bash
cd /volume1/docker/stradegy
docker compose logs -f stradegy
```

### Restart service
```bash
cd /volume1/docker/stradegy
docker compose restart stradegy
```

### Update to latest version
```bash
cd /volume1/docker/stradegy
docker compose down
git pull  # or re-copy files from your computer
docker compose up -d --build
```

### Backup database
```bash
cp /volume1/docker/stradegy/data/stradegy.db \
   /volume1/backup/stradegy_$(date +%Y%m%d).db
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Port 3000 already in use | Another service using port 3000 | Edit `docker-compose.yml` or `docker-compose.simple.yml` and change `"3000:8420"` to another port like `"3001:8420"` |
| Container exits immediately | `.env` missing or invalid | Check `docker compose logs stradegy` |
| Frontend shows blank page | Build failed | Check `docker compose logs stradegy` for build errors |
| No Discord alerts | Missing `DISCORD_CHANNEL_IDS` | Add channel IDs to scan in `.env` |
| Cannot access from outside network | Firewall blocking port 3000 | Open port 3000 on your NAS firewall |

## Files Reference

| File | Purpose |
|------|---------|
| `docker-compose.simple.yml` | Simple Docker setup (HTTP only on port 3000) |
| `docker-compose.yml` | Full setup with Caddy reverse proxy (HTTP 3000 + HTTPS 8443) |
| `Dockerfile` | Multi-stage build: Node.js frontend + Python backend |
| `Caddyfile.nas` | Caddy config for port 8443 |
| `scripts/deploy-nas.sh` | Automated deployment script |
