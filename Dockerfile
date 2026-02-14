FROM python:3.12-bookworm

# Install system dependencies
# pandoc -> text conversion
# libreoffice-headless -> docx to pdf conversion
# poppler-utils -> pdf to image conversion
# nodejs/npm -> for JS based skills and frontend build
# git, curl -> basic tools

# Use HTTPS for apt (fixes hash mismatch issues with some ISP proxies)
RUN sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    libreoffice \
    libreoffice-java-common \
    poppler-utils \
    nodejs \
    npm \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install global NPM packages
# docx -> required by docx skill for JS generation
RUN npm install -g docx

# Ensure global node modules are found by node
ENV NODE_PATH=/usr/local/lib/node_modules:/usr/lib/node_modules

# Install uv (pinned version to avoid cache invalidation)
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /bin/uv

# Install Bun (fast JS/TS runtime for scripts)
# Install to /opt/bun so sandbox user can access it (not /root/.bun which is root-only)
ENV BUN_INSTALL=/opt/bun
RUN curl -fsSL https://bun.sh/install | bash && \
    ln -s /opt/bun/bin/bun /usr/local/bin/bun && \
    chmod -R o+rx /opt/bun

# Install Playwright and Chromium for browser automation
# Install to /opt/playwright so sandbox user can access (not /root/.cache which is root-only)
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN uv pip install --system playwright && \
    playwright install chromium --with-deps && \
    chmod -R o+rx /opt/playwright

# Set up workspace
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

# Build arguments for Sentry (frontend needs at build time)
ARG VITE_SENTRY_DSN=""
ARG VITE_SENTRY_ENVIRONMENT="production"

# Build frontend
COPY frontend/package.json frontend/
RUN --mount=type=cache,target=/root/.npm \
    cd frontend && npm install

COPY frontend/ frontend/
# Pass build version and Sentry config to Vite
RUN cd frontend && \
    VITE_BUILD_VERSION=${BUILD_VERSION} \
    VITE_SENTRY_DSN=${VITE_SENTRY_DSN} \
    VITE_SENTRY_ENVIRONMENT=${VITE_SENTRY_ENVIRONMENT} \
    npm run build

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Build arguments for versioning - placed here to avoid invalidating earlier cache layers
ARG BUILD_VERSION=dev
ARG BUILD_TIME=unknown
ARG GIT_HASH=unknown
ENV BUILD_VERSION=${BUILD_VERSION}
ENV BUILD_TIME=${BUILD_TIME}
ENV GIT_HASH=${GIT_HASH}

# Create sandbox user for running user commands (security)
RUN useradd -m -u 1000 -s /bin/bash sandbox

# Create directories and set permissions
RUN mkdir -p /workspace /data && \
    chown -R sandbox:sandbox /workspace /data

# Entrypoint script to fix permissions on startup
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run the application
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "user_container/app.py"]
