# Python 3.12 slim Debian Bookworm
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    APP_ROOT=/app \
    HF_HUB_OFFLINE=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Install runtime system packages for audio, CPU PyTorch OpenMP, and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libasound2 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications first for optimal Docker layer caching
COPY backend/requirements.lock.txt /app/backend/requirements.lock.txt
COPY backend/pyproject.toml /app/backend/pyproject.toml

# Install dependencies strictly from lockfile
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/backend/requirements.lock.txt && \
    pip install --no-cache-dir --no-deps -e /app/backend

# Copy backend source code, scripts, and product catalog data
COPY backend/app /app/backend/app
COPY scripts /app/scripts
COPY data /app/data

# Expose backend port
EXPOSE 8000

# Healthcheck against liveness endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health/live || exit 1

# Start uvicorn server (1 worker to prevent memory duplication of CPU models)
CMD ["uvicorn", "app.main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
