#!/bin/bash
# ZENO serve - deploy with HTTPS via Caddy + systemd
# Usage:
#   zeno serve --domain zeno.mysite.com   Full setup (Caddy + systemd + start)
#   zeno serve stop                        Stop services
#   zeno serve start                       Start services
#   zeno serve status                      Show status
#   zeno serve logs                        View logs
set -e

ZENO_HOME="$HOME/.zeno"
ZENO_APP="$ZENO_HOME/app"
ZENO_ENV="$ZENO_HOME/.env"
CADDYFILE="$ZENO_HOME/Caddyfile"

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
        error "Usage: zeno serve --domain your.domain.com"
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

    # 1. Install Caddy if missing
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

    # 2. Update .env
    info "Configuring environment..."
    touch "$ZENO_ENV"

    # Remove old host/base_url lines
    sed -i '/^ZENO_HOST=/d' "$ZENO_ENV" 2>/dev/null || true
    sed -i '/^BASE_URL=/d' "$ZENO_ENV" 2>/dev/null || true

    echo "ZENO_HOST=0.0.0.0" >> "$ZENO_ENV"
    echo "BASE_URL=https://$DOMAIN" >> "$ZENO_ENV"

    # 3. Create Caddyfile
    info "Creating Caddyfile..."
    cat > "$CADDYFILE" << EOF
$DOMAIN {
    reverse_proxy localhost:18000
}
EOF

    # 4. Create zeno.service
    info "Creating systemd service: zeno.service..."
    CURRENT_USER=$(whoami)
    CURRENT_HOME="$HOME"

    sudo tee /etc/systemd/system/zeno.service > /dev/null << EOF
[Unit]
Description=ZENO AI Agent
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
ExecStart=$ZENO_HOME/bin/zeno
WorkingDirectory=$ZENO_APP
Restart=always
RestartSec=5
Environment=ZENO_HOST=0.0.0.0

[Install]
WantedBy=multi-user.target
EOF

    # 5. Create caddy.service (if not exists) or just reload
    if [ ! -f /etc/systemd/system/caddy.service ]; then
        info "Creating systemd service: caddy.service..."
        sudo tee /etc/systemd/system/caddy.service > /dev/null << EOF
[Unit]
Description=Caddy Web Server (ZENO)
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/caddy run --config $CADDYFILE
ExecReload=/usr/local/bin/caddy reload --config $CADDYFILE
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    else
        info "caddy.service exists, reloading config..."
        sudo systemctl reload caddy.service 2>/dev/null || true
    fi

    # 6. Enable and start services
    info "Enabling and starting services..."
    sudo systemctl daemon-reload
    sudo systemctl enable zeno.service caddy.service
    sudo systemctl restart caddy.service
    sudo systemctl restart zeno.service

    # 7. Summary
    echo ""
    echo -e "  ${GREEN}ZENO is live at https://$DOMAIN${NC}"
    echo ""
    warn "Make sure your domain's DNS A record points to this server's IP."
    echo ""
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
