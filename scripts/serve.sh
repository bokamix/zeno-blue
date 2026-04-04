#!/bin/bash
# ZENO serve - deploy with HTTPS via Caddy + systemd
# Usage:
#   zeno serve                             Auto-detect IP, use sslip.io domain
#   zeno serve --domain zeno.mysite.com   Full setup with custom domain
#   zeno serve stop                        Stop services
#   zeno serve start                       Start services
#   zeno serve status                      Show status
#   zeno serve logs                        View logs
set -e

ZENO_HOME="$HOME/.zeno"
ZENO_APP="$ZENO_HOME/app"
ZENO_ENV="$ZENO_HOME/.env"
CADDYFILE="$ZENO_HOME/Caddyfile"
ZENO_SERVICE_USER="zeno-svc"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

# --- Helpers ---
info()  { echo -e "  ${GREEN}$1${NC}"; }
warn()  { echo -e "  ${YELLOW}$1${NC}"; }
error() { echo -e "  ${RED}$1${NC}"; exit 1; }

# --- Subcommands ---

cmd_stop() {
    echo ""
    info "Stopping ZENO services..."
    sudo systemctl stop zeno.service 2>/dev/null || true
    sudo systemctl stop caddy.service 2>/dev/null || true
    info "Services stopped."
    echo ""
}

cmd_start() {
    echo ""
    info "Starting ZENO services..."
    sudo systemctl start caddy.service
    sudo systemctl start zeno.service
    info "Services started."
    echo ""
}

cmd_status() {
    echo ""
    echo -e "  ${BOLD}ZENO Service:${NC}"
    systemctl is-active zeno.service 2>/dev/null && info "  zeno.service: running" || warn "  zeno.service: stopped"
    echo -e "  ${BOLD}Caddy Service:${NC}"
    systemctl is-active caddy.service 2>/dev/null && info "  caddy.service: running" || warn "  caddy.service: stopped"
    echo ""
}

cmd_logs() {
    journalctl -u zeno.service -u caddy.service -f --no-pager
}

cmd_setup() {
    local DOMAIN=""

    # Parse args
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    if [ -z "$DOMAIN" ]; then
        info "No domain provided, detecting public IP..."
        PUBLIC_IP=$(curl -fsSL --max-time 5 https://ifconfig.me 2>/dev/null || \
                    curl -fsSL --max-time 5 https://api.ipify.org 2>/dev/null || true)
        if [ -z "$PUBLIC_IP" ]; then
            error "Could not detect public IP. Use --domain your.domain.com"
        fi
        DOMAIN="${PUBLIC_IP//./-}.sslip.io"
        info "Using auto domain: $DOMAIN"
    fi

    # Validate: Linux + systemd
    if [ "$(uname -s)" != "Linux" ]; then
        error "zeno serve requires Linux with systemd."
    fi
    if ! command -v systemctl &>/dev/null; then
        error "systemd is required. This system doesn't have systemctl."
    fi

    echo ""
    echo -e "  ${BOLD}Setting up ZENO for ${GREEN}$DOMAIN${NC}"
    echo ""

    # 1. Create dedicated service user (limited permissions, no login shell)
    if ! id "$ZENO_SERVICE_USER" &>/dev/null; then
        info "Creating service user: $ZENO_SERVICE_USER..."
        sudo useradd --system --no-create-home --shell /usr/sbin/nologin "$ZENO_SERVICE_USER"
    fi

    # Copy ~/.zeno to service user's home (/var/lib/zeno-svc)
    ZENO_SVC_HOME="/var/lib/zeno-svc"
    sudo mkdir -p "$ZENO_SVC_HOME"
    sudo cp -r "$ZENO_HOME/app" "$ZENO_SVC_HOME/"
    sudo chown -R "$ZENO_SERVICE_USER:$ZENO_SERVICE_USER" "$ZENO_SVC_HOME"
    sudo chmod 750 "$ZENO_SVC_HOME"

    SVC_ZENO_ENV="$ZENO_SVC_HOME/.env"
    SVC_CADDYFILE="$ZENO_SVC_HOME/Caddyfile"

    # 2. Install Caddy if missing
    if ! command -v caddy &>/dev/null; then
        info "Installing Caddy..."
        ARCH=$(dpkg --print-architecture 2>/dev/null || uname -m)
        case "$ARCH" in
            amd64|x86_64) ARCH="amd64" ;;
            arm64|aarch64) ARCH="arm64" ;;
            *) error "Unsupported architecture: $ARCH" ;;
        esac
        sudo curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=$ARCH" \
            -o /usr/local/bin/caddy
        sudo chmod +x /usr/local/bin/caddy
        info "Caddy installed."
    else
        info "Caddy already installed: $(caddy version 2>/dev/null || echo 'unknown')"
    fi

    # 3. Write service .env (no secrets — API key and password set via browser setup)
    info "Configuring environment..."
    sudo tee "$SVC_ZENO_ENV" > /dev/null << EOF
ZENO_HOST=0.0.0.0
BASE_URL=https://$DOMAIN
DATA_DIR=$ZENO_SVC_HOME/data
WORKSPACE_DIR=$ZENO_SVC_HOME/workspace
ARTIFACTS_DIR=$ZENO_SVC_HOME/workspace/artifacts
DB_PATH=$ZENO_SVC_HOME/data/runtime.db
SKILLS_DIR=$ZENO_SVC_HOME/app/user_container/skills
EOF
    sudo chown "$ZENO_SERVICE_USER:$ZENO_SERVICE_USER" "$SVC_ZENO_ENV"
    sudo chmod 600 "$SVC_ZENO_ENV"

    # Create data dirs for service user
    sudo mkdir -p "$ZENO_SVC_HOME/data" "$ZENO_SVC_HOME/workspace/artifacts"
    sudo chown -R "$ZENO_SERVICE_USER:$ZENO_SERVICE_USER" "$ZENO_SVC_HOME/data" "$ZENO_SVC_HOME/workspace"

    # 5. Create Caddyfile
    info "Creating Caddyfile..."
    sudo tee "$SVC_CADDYFILE" > /dev/null << EOF
$DOMAIN {
    reverse_proxy localhost:18000
}
EOF

    # 6. Create zeno.service
    info "Creating systemd service: zeno.service..."
    sudo tee /etc/systemd/system/zeno.service > /dev/null << EOF
[Unit]
Description=ZENO AI Agent
After=network.target

[Service]
Type=simple
User=$ZENO_SERVICE_USER
ExecStart=/usr/bin/env bash $ZENO_SVC_HOME/app/scripts/zeno-cli.sh
WorkingDirectory=$ZENO_SVC_HOME/app
EnvironmentFile=$SVC_ZENO_ENV
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # 7. Create caddy.service (if not exists) or reload
    if [ ! -f /etc/systemd/system/caddy.service ]; then
        info "Creating systemd service: caddy.service..."
        sudo tee /etc/systemd/system/caddy.service > /dev/null << EOF
[Unit]
Description=Caddy Web Server (ZENO)
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/caddy run --config $SVC_CADDYFILE
ExecReload=/usr/local/bin/caddy reload --config $SVC_CADDYFILE
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    else
        info "caddy.service exists, reloading config..."
        sudo systemctl reload caddy.service 2>/dev/null || true
    fi

    # 8. Enable and start services
    info "Enabling and starting services..."
    sudo systemctl daemon-reload
    sudo systemctl enable zeno.service caddy.service
    sudo systemctl restart caddy.service
    sudo systemctl restart zeno.service

    # 9. Summary
    echo ""
    echo -e "  ${GREEN}✅ ZENO is live at https://$DOMAIN${NC}"
    echo ""
    echo -e "  Open the URL and complete setup in your browser."
    echo ""
    if [[ "$DOMAIN" != *sslip.io ]]; then
        warn "Make sure your domain's DNS A record points to this server's IP."
        echo ""
    fi
    echo -e "  ${BOLD}Commands:${NC}"
    echo "    zeno serve stop     — Stop ZENO"
    echo "    zeno serve start    — Start ZENO"
    echo "    zeno serve status   — Check status"
    echo "    zeno serve logs     — View logs"
    echo ""
}

# --- Main ---
case "${1:-}" in
    stop)    cmd_stop ;;
    start)   cmd_start ;;
    status)  cmd_status ;;
    logs)    cmd_logs ;;
    *)       cmd_setup "$@" ;;
esac
