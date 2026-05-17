FROM --platform=$BUILDPLATFORM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./
COPY backend/src/ ./src/
RUN pip install --no-cache-dir -e .

COPY --from=builder /app/dist /app/frontend/dist

RUN mkdir -p /app/data /app/config /app/eval/traces /app/logs
RUN groupadd -r stradegy && useradd -r -g stradegy -d /app stradegy \
    && chown -R stradegy:stradegy /app/data /app/config /app/eval /app/logs
USER stradegy

EXPOSE 8420

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8420/api/health || exit 1

CMD ["python", "-m", "stradegy.main"]
