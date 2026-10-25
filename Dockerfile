# ==============================================================================
# Multi-Stage Production Dockerfile for SecureDeploy ML
# Experiment 4: Production-ready Docker packaging (multi-stage, non-root)
# Cloud Computing Lab DJS23ALMD701
# ==============================================================================

# ------------------------------------------------------------------------------
# STAGE 1: Builder
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies if needed and create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency specifications first to leverage Docker layer caching
COPY requirements.txt .

# Install production dependencies (including gunicorn on Linux)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and training dataset into builder stage
COPY train.py .
COPY data/ ./data/

# Bake the trained model artifact into the build stage (no external download at runtime)
RUN python train.py --data data/headlines.csv --output /build/model.joblib

# ------------------------------------------------------------------------------
# STAGE 2: Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Security: Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=5000

WORKDIR /app

# Create dedicated non-root system user and group (UID/GID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -M appuser

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv

# Copy baked model from builder stage
COPY --from=builder --chown=appuser:appgroup /build/model.joblib /app/model.joblib

# Copy application assets and code
COPY --chown=appuser:appgroup app.py /app/
COPY --chown=appuser:appgroup templates/ /app/templates/
COPY --chown=appuser:appgroup static/ /app/static/

# Set file permissions explicitly
RUN chmod -R 550 /app && \
    chmod 440 /app/model.joblib

# Switch to non-root user
USER 10001:10001

# Expose service port
EXPOSE 5000

# Container Healthcheck (uses native Python standard library; no curl/wget required)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health').read()"]

# Run with production WSGI server Gunicorn (2 worker processes, 30s timeout)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]
