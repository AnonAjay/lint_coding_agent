# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

ARG BASE_IMAGE=ghcr.io/meta-pytorch/openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . /app/env

WORKDIR /app/env

# Install 'uv' for high-performance dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Sync dependencies into a virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-editable

# --- Runtime Stage ---
FROM ${BASE_IMAGE}

# Set Hugging Face required environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    ENABLE_WEB_INTERFACE=true

WORKDIR /app/env

# Copy the virtual environment and code from builder
COPY --from=builder /app/env/.venv /app/env/.venv
COPY --from=builder /app/env /app/env

# Set PATH to use the virtual environment
ENV PATH="/app/env/.venv/bin:$PATH"
# Ensure the root of the project is in PYTHONPATH
ENV PYTHONPATH="/app/env:/app/env/server:$PYTHONPATH"

# Hugging Face Spaces run with a non-root user (1000). Ensure permissions are correct.
RUN chmod -R 777 /app/env

# Standard HF Port exposure
EXPOSE 7860

# Updated Healthcheck to use the correct port
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start the server on 7860 with proxy support
# 'proxy_headers' is vital for HF reverse proxies to handle WebSockets correctly
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]

WORKDIR /app/env
COPY . .
# This places QUESTIONS.json at /app/env/server/QUESTIONS.json