# ── AITIS Playwright Execution Container ─────────────────────────────
# Isolated, sandboxed environment for running Playwright test scripts.
# This image is pulled/spawned by the execution worker for each job.
# ─────────────────────────────────────────────────────────────────────

FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

# Metadata
LABEL maintainer="AITIS Platform"
LABEL description="Isolated Playwright execution container for AITIS automation"
LABEL org.opencontainers.image.source="https://github.com/aitis/platform"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies for Playwright browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for Chromium
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libxshmfence1 \
    # Required for Firefox
    libdbus-glib-1-2 libxt6 \
    # Required for WebKit
    libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 \
    # Utilities
    curl wget jq \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for test execution
RUN groupadd -r playwright-runner && \
    useradd -r -g playwright-runner -d /home/runner -s /sbin/nologin playwright-runner && \
    mkdir -p /home/runner && \
    chown playwright-runner:playwright-runner /home/runner

# Create workspace directories
RUN mkdir -p /workspace/tests /workspace/results /workspace/artifacts && \
    chown -R playwright-runner:playwright-runner /workspace

# Copy runner script
COPY runner.py /workspace/runner.py
COPY run_tests.sh /workspace/run_tests.sh

RUN chmod +x /workspace/run_tests.sh && \
    chown playwright-runner:playwright-runner /workspace/runner.py /workspace/run_tests.sh

# Install Python test dependencies
RUN pip install --no-cache-dir \
    pytest>=8.0 \
    pytest-asyncio>=0.23 \
    pytest-json-report>=1.5 \
    allure-pytest>=2.13 \
    python-dotenv>=1.0

# Switch to non-root user
USER playwright-runner
WORKDIR /workspace

# Health check — verify Playwright is installed
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "from playwright.sync_api import sync_playwright; print('ok')" || exit 1

# Default: run the test runner script
ENTRYPOINT ["/workspace/run_tests.sh"]
