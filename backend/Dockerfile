# Multi-stage build keeps the final image small.
# Stage 1: install dependencies in a builder.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Install exactly the pinned dependencies for reproducible images.
# The application package itself is run from the source copied below,
# so there's no need to build/install a wheel.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: runtime image with only the runtime dependencies.
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=app:app . .

USER app

EXPOSE 8000

# Health check for container orchestrators
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
