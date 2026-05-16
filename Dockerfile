# ---- Build Stage ----
FROM node:22-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---- Runtime Stage ----
FROM python:3.13-slim
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
