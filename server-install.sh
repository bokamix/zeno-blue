#!/bin/bash
# ZENO installer
# curl -fsSL https://raw.githubusercontent.com/bokamix/zeno-blue/main/server-install.sh | bash
set -e

ZENO_HOME="$HOME/.zeno"
ZENO_APP="$ZENO_HOME/app"
ZENO_BIN="$ZENO_HOME/bin"
TARBALL_API="https://api.github.com/repos/bokamix/zeno-blue/releases/latest"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo "  ███████╗███████╗███╗   ██╗ ██████╗ "
echo "  ╚══███╔╝██╔════╝████╗  ██║██╔═══██╗"
echo "    ███╔╝ █████╗  ██╔██╗ ██║██║   ██║"
echo "   ███╔╝  ██╔══╝  ██║╚██╗██║██║   ██║"
echo "  ███████╗███████╗██║ ╚████║╚██████╔╝"
echo "  ╚══════╝╚══════╝╚═╝  ╚═══╝ ╚═════╝ "
echo ""

# --- Detect OS ---
OS="$(uname -s)"
HAS_SYSTEMD=false
IS_SERVER=false

case "$OS" in
    Darwin)
        MODE="local"
        ;;
    Linux)
        if command -v systemctl &>/dev/null && systemctl is-system-running &>/dev/null 2>&1; then
            HAS_SYSTEMD=true
        fi
        # Server mode: Linux + systemd + not WSL
        if $HAS_SYSTEMD && [ -z "${WSL_DISTRO_NAME:-}" ]; then
            MODE="server"
        else
            MODE="local"
        fi
        ;;
    MINGW*|MSYS*|CYGWIN*)
        echo -e "  ${RED}Windows is not supported.${NC}"
        echo ""
        echo "  Please use WSL (Windows Subsystem for Linux):"
        echo -e "  ${GREEN}wsl --install${NC}"
        exit 1
        ;;
    *)
        echo -e "  ${RED}Unsupported OS: $OS${NC}"
        exit 1
        ;;
esac

if [ "$MODE" = "server" ]; then
    echo -e "  ${BOLD}Server Install${NC} (Linux + systemd detected)"
else
    echo -e "  ${BOLD}Local Install${NC}"
fi
echo ""

# --- Install uv ---
if command -v uv &>/dev/null; then
    echo -e "  uv:      ${GREEN}$(uv --version)${NC}"
else
    echo -e "  Installing ${BOLD}uv${NC}..."
    curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        echo -e "  ${RED}Failed to install uv.${NC}"
        exit 1
    fi
    echo -e "  uv:      ${GREEN}$(uv --version)${NC}"
fi

echo ""

# --- Download ZENO ---
echo -e "  ${BOLD}Downloading ZENO...${NC}"

tmpfile=$(mktemp)
trap 'rm -f "$tmpfile"' EXIT

asset_url=$(curl -fsSL "$TARBALL_API" | grep -o '"browser_download_url":\s*"[^"]*zeno-release\.tar\.gz"' | cut -d'"' -f4)
if [ -z "$asset_url" ]; then
    echo -e "  ${RED}Failed to find release asset. Check https://github.com/bokamix/zeno-blue/releases${NC}"
    exit 1
fi
curl -fsSL "$asset_url" -o "$tmpfile"

rm -rf "$ZENO_APP"
mkdir -p "$ZENO_APP"
tar xzf "$tmpfile" -C "$ZENO_APP"

echo -e "  Installed to ${GREEN}~/.zeno/app/${NC}"

# --- Create launcher ---
mkdir -p "$ZENO_BIN"
cat > "$ZENO_BIN/zeno" << 'LAUNCHER'
#!/bin/bash
exec bash "$HOME/.zeno/app/scripts/zeno-cli.sh" "$@"
LAUNCHER
chmod +x "$ZENO_BIN/zeno"

# --- Add to PATH ---
_add_to_path() {
    local line='export PATH="$HOME/.zeno/bin:$PATH"'
    local shell_name profile_file
    shell_name="$(basename "$SHELL")"
    case "$shell_name" in
        zsh)  profile_file="$HOME/.zshrc" ;;
        bash)
            if [ -f "$HOME/.bash_profile" ]; then
                profile_file="$HOME/.bash_profile"
            else
                profile_file="$HOME/.bashrc"
            fi
            ;;
        fish)
            local fish_config="$HOME/.config/fish/config.fish"
            mkdir -p "$(dirname "$fish_config")"
            if ! grep -qF '.zeno/bin' "$fish_config" 2>/dev/null; then
                echo 'set -gx PATH $HOME/.zeno/bin $PATH' >> "$fish_config"
            fi
            return
            ;;
        *) profile_file="$HOME/.profile" ;;
    esac
    if ! grep -qF '.zeno/bin' "$profile_file" 2>/dev/null; then
        echo "" >> "$profile_file"
        echo '# ZENO' >> "$profile_file"
        echo "$line" >> "$profile_file"
    fi
}
_add_to_path
export PATH="$ZENO_BIN:$PATH"

echo ""

# --- Server mode: Caddy + systemd ---
if [ "$MODE" = "server" ]; then
    echo -e "  ${BOLD}Setting up server...${NC}"
    exec bash "$ZENO_APP/scripts/serve.sh"
fi

# --- Local mode: just run ---
echo -e "  ${GREEN}✅ ZENO installed!${NC}"
echo ""
echo -e "  Run:    ${BOLD}zeno${NC}"
echo -e "  Update: ${BOLD}zeno update${NC}"
echo ""

if [ ! -t 0 ]; then
    shell_name="$(basename "$SHELL")"
    echo -e "  ${YELLOW}To start using zeno now, run:${NC}"
    case "$shell_name" in
        zsh)  echo -e "  ${GREEN}source ~/.zshrc && zeno${NC}" ;;
        fish) echo -e "  ${GREEN}source ~/.config/fish/config.fish && zeno${NC}" ;;
        bash)
            if [ -f "$HOME/.bash_profile" ]; then
                echo -e "  ${GREEN}source ~/.bash_profile && zeno${NC}"
            else
                echo -e "  ${GREEN}source ~/.bashrc && zeno${NC}"
            fi
            ;;
        *)    echo -e "  ${GREEN}source ~/.profile && zeno${NC}" ;;
    esac
    echo ""
else
    zeno
fi
