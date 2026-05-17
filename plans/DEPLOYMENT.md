# Deployment — Ugreen NAS + Docker

This guide walks through deploying Stradegy to a Ugreen NAS using Docker. The NAS stays on 24/7 with minimal power draw, making it ideal for an always-on trading bot.

## What You Need

- Ugreen NAS with Docker support (UGOS 2.0 or newer)
- Your NAS IP address and admin SSH credentials
- A computer with `git` and `ssh`
- (Optional) Cloudflare account + domain for remote HTTPS access

## Architecture

```
Phone ──> Cloudflare Tunnel ──> NAS Docker ──> Stradegy (:8420)
                (HTTPS)          (Local)
```

Without Cloudflare, you access the app directly on your local network at `http://<nas-ip>:8420`.

---

## Step 1: Prepare Your NAS

SSH into your NAS and create the deployment directory:

```bash
ssh admin@<your-nas-ip>
mkdir -p /volume1/docker/stradegy
cd /volume1/docker/stradegy
```

Create persistent data directories:

```bash
mkdir -p data config cloudflared logs
chmod 777 data config cloudflared logs
```

## Step 2: Copy the Project to Your NAS

**Option A — Git clone (recommended)**

On your NAS:

```bash
cd /volume1/docker/stradegy
git clone https://github.com/gajendravaradhan/stradegy.git .
```

**Option B — SCP from your computer**

On your computer:

```bash
cd /path/to/stradegy
cp .env.example backend/.env
scp -r . admin@<nas-ip>:/volume1/docker/stradegy/
```

## Step 3: Configure Environment Variables

On your NAS, create the env file:

```bash
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
DISCORD_GENERAL_CHANNEL_ID=your_channel_id
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

## Step 4: Build and Start

```bash
cd /volume1/docker/stradegy

# Build the image (this takes 5–15 minutes on a NAS)
docker compose build

# Start the app
docker compose up -d

# Watch the logs
docker compose logs -f stradegy
```

Wait for the healthcheck to pass. You should see:

```
Stradegy backend ready on 0.0.0.0:8420
```

## Step 5: Verify It Works

From any device on your home network:

```
http://<your-nas-ip>:8420
```

You should see the Stradegy PWA login screen or dashboard.

Test the API:

```bash
curl http://<your-nas-ip>:8420/api/health
# Expected: {"status":"ok","version":"0.1.0"}
```

## Step 6: (Optional) Cloudflare Tunnel for Remote Access

If you want to access Stradegy from outside your home network:

1. Install `cloudflared` on your NAS (via Docker or binary)
2. Authenticate: `cloudflared tunnel login`
3. Create a tunnel: `cloudflared tunnel create stradegy`
4. Copy the tunnel credentials JSON to `/volume1/docker/stradegy/config/cloudflared/`
5. Create `/volume1/docker/stradegy/config/cloudflared/config.yml`:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /etc/cloudflared/<tunnel-id>.json

ingress:
  - hostname: stradegy.yourdomain.com
    service: http://stradegy:8420
  - service: http_status:404
```

6. Start the tunnel:

```bash
docker compose --profile tunnel up -d cloudflared
```

7. In Cloudflare dashboard, add a CNAME record: `stradegy` → `<tunnel-id>.cfargotunnel.com`

8. Visit `https://stradegy.yourdomain.com` from your phone.

---

## Maintenance

### Check Status

```bash
docker compose ps
docker compose logs --tail=50 stradegy
```

### Update to Latest Version

```bash
cd /volume1/docker/stradegy
docker compose down
git pull
docker compose build --no-cache
docker compose up -d
```

### Backup Your Data

The SQLite database lives in `./data/`:

```bash
cp /volume1/docker/stradegy/data/stradegy.db \
   /volume1/backup/stradegy_$(date +%Y%m%d).db
```

### Monitor Resource Usage

```bash
docker stats stradegy
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Container exits immediately | `.env` missing or invalid keys | Check `docker compose logs stradegy` |
| Frontend shows blank page | Static files not found | Verify `frontend/dist` exists in the built image |
| API timeout / no data | Finnhub or Alpaca keys missing | Fill in `backend/.env` and restart |
| Can't reach from phone | Firewall blocking port 8420 | Open port 8420 on your NAS firewall |
| Cloudflare tunnel fails | `config.yml` path or credentials wrong | Check `docker compose logs cloudflared` |
| Build fails on ARM NAS | Missing ARM wheels for torch | The Dockerfile uses `--platform` flags; if it still fails, build on an x86 machine and push to a registry |

---

## File Reference

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build: Node frontend + Python backend |
| `docker-compose.yml` | Orchestrates app + optional Cloudflare tunnel |
| `backend/.env` | All API keys and configuration |
| `.env.example` | Template showing all available settings |
| `data/` | Persistent SQLite database |
| `config/` | Runtime config and Cloudflare tunnel credentials |
| `logs/` | Application logs (auto-rotated) |
