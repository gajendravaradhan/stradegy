FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Build TA-Lib from source (not available in Debian Trixie)
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

WORKDIR /app

COPY backend/pyproject.toml .
COPY backend/src ./src

RUN pip install --no-cache-dir -e .

COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

RUN mkdir -p data config logs eval strategies

EXPOSE 8420

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8420/api/health || exit 1

CMD ["python", "-m", "uvicorn", "stradegy.main:app", "--host", "0.0.0.0", "--port", "8420", "--app-dir", "src"]
