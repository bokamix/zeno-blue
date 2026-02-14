#!/bin/bash
set -e

# Fix permissions on workspace (user files need sandbox access)
chown -R sandbox:sandbox /workspace 2>/dev/null || true

# Fix permissions on /data, but EXCLUDE uv-cache (60k+ files, slows startup by ~80s)
# uv-cache only needs directory ownership - sandbox can create new files, existing are read-only (OK for cache)
chown sandbox:sandbox /data 2>/dev/null || true
chown -R sandbox:sandbox /data/chroma 2>/dev/null || true
chown sandbox:sandbox /data/*.db 2>/dev/null || true

# Ensure UV cache directory exists with correct permissions (non-recursive for speed)
mkdir -p /home/sandbox/.cache/uv
chown sandbox:sandbox /home/sandbox/.cache /home/sandbox/.cache/uv 2>/dev/null || true

# Ensure secrets.json is root-only
if [ -f /app/secrets.json ]; then
    chmod 600 /app/secrets.json
    chown root:root /app/secrets.json
fi

# Run the main application
exec "$@"
