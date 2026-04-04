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
CURRENT_USER="$(whoami)"

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
        # Force IPv4 (sslip.io doesn't support IPv6 as domain name)
        PUBLIC_IP=$(curl -4 -fsSL --max-time 5 https://ifconfig.me 2>/dev/null || \
                    curl -4 -fsSL --max-time 5 https://api.ipify.org 2>/dev/null || true)
        if [ -z "$PUBLIC_IP" ]; then
            error "Could not detect public IPv4. Use --domain your.domain.com"
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

    # 1. Make uv available system-wide
    if ! /usr/local/bin/uv --version &>/dev/null 2>&1; then
        UV_BIN=$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")
        if [ -f "$UV_BIN" ]; then
            info "Installing uv system-wide..."
            sudo cp "$UV_BIN" /usr/local/bin/uv
            sudo chmod +x /usr/local/bin/uv
        else
            info "Installing uv..."
            curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null
            sudo cp "$HOME/.local/bin/uv" /usr/local/bin/uv
            sudo chmod +x /usr/local/bin/uv
        fi
        info "uv installed system-wide: $(/usr/local/bin/uv --version)"
    else
        info "uv: $(/usr/local/bin/uv --version)"
    fi

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
        info "Caddy: $(caddy version 2>/dev/null || echo 'unknown')"
    fi

    # 3. Write .env (BASE_URL + host, no secrets)
    info "Configuring environment..."
    touch "$ZENO_ENV"
    sed -i '/^ZENO_HOST=/d' "$ZENO_ENV" 2>/dev/null || true
    sed -i '/^BASE_URL=/d' "$ZENO_ENV" 2>/dev/null || true
    echo "ZENO_HOST=0.0.0.0" >> "$ZENO_ENV"
    echo "BASE_URL=https://$DOMAIN" >> "$ZENO_ENV"

    # 4. Create Caddyfile
    info "Creating Caddyfile..."
    cat > "$CADDYFILE" << EOF
$DOMAIN {
    reverse_proxy localhost:18000
}
EOF

    # 5. Create zeno.service (runs as current user, uses their ~/.zeno)
    info "Creating systemd service: zeno.service..."
    sudo tee /etc/systemd/system/zeno.service > /dev/null << EOF
[Unit]
Description=ZENO AI Agent
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
ExecStart=$ZENO_HOME/bin/zeno
WorkingDirectory=$ZENO_APP
Environment=HOME=$HOME
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # 6. Create caddy.service (if not exists) or reload
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
Environment=HOME=$HOME

[Install]
WantedBy=multi-user.target
EOF
    else
        info "Updating caddy.service config..."
        sudo sed -i "s|ExecStart=.*caddy run.*|ExecStart=/usr/local/bin/caddy run --config $CADDYFILE|" \
            /etc/systemd/system/caddy.service 2>/dev/null || true
    fi

    # 7. Enable and start services
    info "Enabling and starting services..."
    sudo systemctl daemon-reload
    sudo systemctl enable zeno.service caddy.service
    sudo systemctl restart caddy.service
    sudo systemctl restart zeno.service

    # 8. Summary
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
