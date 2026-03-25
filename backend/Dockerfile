# Build context: repo root (set Docker Root Directory to / in Render, Dockerfile Path to backend/Dockerfile)
# ── Stage 1: install dependencies ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt lives at the repo root — copy it from there
COPY requirements.txt ./
RUN pip install --upgrade pip --quiet && \
    pip install --no-cache-dir -r requirements.txt


# ── Stage 2: slim runtime image ───────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only the backend source code
COPY backend/ ./

# Create storage directories (mount a Render Disk here for persistence)
RUN mkdir -p storage/uploads storage/reports

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
