FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./
COPY backend/src/ ./src/
RUN pip install --no-cache-dir -e .

COPY frontend/dist /app/frontend/dist

RUN mkdir -p /app/data /app/config /app/eval/traces /logs
RUN groupadd -r stradegy && useradd -r -g stradegy -d /app stradegy \
    && chown -R stradegy:stradegy /app/data /app/config /app/eval /logs /app
USER stradegy

EXPOSE 8420

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8420/api/health || exit 1

CMD ["python", "-m", "stradegy.main"]
