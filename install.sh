#!/bin/bash
# ZENO installer
# curl -fsSL https://raw.githubusercontent.com/bokamix/zeno-blue/main/install.sh | bash && export PATH="$HOME/.zeno/bin:$PATH"
set -e

ZENO_HOME="$HOME/.zeno"
ZENO_APP="$ZENO_HOME/app"
ZENO_BIN="$ZENO_HOME/bin"
TARBALL_URL="https://github.com/bokamix/zeno-blue/archive/refs/heads/main.tar.gz"

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
echo -e "  ${BOLD}Installer${NC}"
echo ""

# --- Detect OS ---
OS="$(uname -s)"
case "$OS" in
    Darwin) OS_NAME="macOS" ;;
    Linux)  OS_NAME="Linux" ;;
    MINGW*|MSYS*|CYGWIN*)
        echo -e "  ${RED}Windows is not supported.${NC}"
        echo ""
        echo "  Please use WSL (Windows Subsystem for Linux):"
        echo -e "  ${GREEN}wsl --install${NC}"
        echo "  Then run this installer inside WSL."
        exit 1
        ;;
    *)
        echo -e "  ${RED}Unsupported OS: $OS${NC}"
        exit 1
        ;;
esac

# --- Install uv (Python manager) ---
if command -v uv &>/dev/null; then
    UV_VERSION=$(uv --version 2>/dev/null)
    echo -e "  uv:      ${GREEN}$UV_VERSION${NC}"
else
    echo -e "  Installing ${BOLD}uv${NC} (Python manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        echo -e "  ${RED}Failed to install uv.${NC}"
        echo "  Install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    echo -e "  uv:      ${GREEN}$(uv --version)${NC}"
fi

# --- Check Node.js/npm ---
if command -v npm &>/dev/null; then
    NODE_VERSION=$(node --version 2>/dev/null || echo "unknown")
    echo -e "  Node.js: ${GREEN}$NODE_VERSION${NC}"
else
    echo -e "  Node.js: ${YELLOW}not found${NC} (needed for frontend build on first run)"
    if [ "$OS_NAME" = "macOS" ]; then
        echo -e "           Install later: ${GREEN}brew install node${NC}"
    else
        echo -e "           Install later: ${GREEN}sudo apt install nodejs npm${NC}"
    fi
fi

echo ""

# --- Download and extract ---
echo -e "  ${BOLD}Downloading ZENO...${NC}"

tmpfile=$(mktemp)
trap 'rm -f "$tmpfile"' EXIT

curl -fsSL "$TARBALL_URL" -o "$tmpfile"

# Remove old app code (user data in ~/.zeno/.env, data/, workspace/ is preserved)
rm -rf "$ZENO_APP"
mkdir -p "$ZENO_APP"

tar xzf "$tmpfile" --strip-components=1 -C "$ZENO_APP"

echo -e "  Installed to ${GREEN}~/.zeno/app/${NC}"

# --- Create launcher script ---
mkdir -p "$ZENO_BIN"

cat > "$ZENO_BIN/zeno" << 'LAUNCHER'
#!/bin/bash
ZENO_APP="$HOME/.zeno/app"

# Auto-sync from git repo in Codespaces / dev environments
_auto_sync() {
    # Find the git repo (Codespaces clone or any local checkout)
    local repo=""
    for candidate in "/workspaces/zeno-blue" "/workspaces/toolsmith-ai"; do
        if [ -d "$candidate/.git" ]; then
            repo="$candidate"
            break
        fi
    done
    [ -z "$repo" ] && return

    # Pull latest changes
    (cd "$repo" && git pull --ff-only 2>/dev/null) || true

    # Sync app code (exclude user data dirs)
    rsync -a --delete \
        --exclude 'frontend/node_modules' \
        --exclude 'frontend/dist' \
        --exclude 'workspace/' \
        --exclude 'data/' \
        --exclude '.env' \
        "$repo/" "$ZENO_APP/"

    # Rebuild frontend if source changed
    local dist="$ZENO_APP/frontend/dist/index.html"
    local needs_build=0
    if [ ! -f "$dist" ]; then
        needs_build=1
    else
        # Check if any frontend source file is newer than dist
        local newer=$(find "$ZENO_APP/frontend/src" "$ZENO_APP/frontend/package.json" -newer "$dist" 2>/dev/null | head -1)
        [ -n "$newer" ] && needs_build=1
    fi

    if [ "$needs_build" = "1" ] && command -v npm &>/dev/null; then
        echo "  🔨 Rebuilding frontend..."
        (cd "$ZENO_APP/frontend" && npm install --silent 2>/dev/null && npm run build --silent 2>/dev/null)
    fi
}

case "${1:-}" in
    update)
        echo ""
        echo "  Updating ZENO..."
        tmpfile=$(mktemp)
        trap 'rm -f "$tmpfile"' EXIT
        curl -fsSL "https://github.com/bokamix/zeno-blue/archive/refs/heads/main.tar.gz" -o "$tmpfile"

        # Preserve node_modules for faster frontend rebuild
        if [ -d "$ZENO_APP/frontend/node_modules" ]; then
            mv "$ZENO_APP/frontend/node_modules" "/tmp/_zeno_node_modules_$$"
        fi

        rm -rf "$ZENO_APP"
        mkdir -p "$ZENO_APP"
        tar xzf "$tmpfile" --strip-components=1 -C "$ZENO_APP"

        # Restore node_modules
        if [ -d "/tmp/_zeno_node_modules_$$" ]; then
            mv "/tmp/_zeno_node_modules_$$" "$ZENO_APP/frontend/node_modules"
        fi

        # Rebuild frontend
        if command -v npm &>/dev/null && [ -f "$ZENO_APP/frontend/package.json" ]; then
            echo "  Building frontend..."
            (cd "$ZENO_APP/frontend" && npm install --silent 2>/dev/null && npm run build --silent 2>/dev/null)
            echo "  Frontend ready."
        fi

        echo "  ✅ ZENO updated!"
        echo ""
        ;;
    serve)
        exec bash "$ZENO_APP/scripts/serve.sh" "${@:2}"
        ;;
    *)
        _auto_sync
        exec uv run --python 3.12 "$ZENO_APP/zeno.py" "$@"
        ;;
esac
LAUNCHER

chmod +x "$ZENO_BIN/zeno"

# --- Add to PATH ---
add_to_path() {
    local line='export PATH="$HOME/.zeno/bin:$PATH"'
    local shell_name profile_file

    # Detect current shell
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
            # Fish uses a different syntax
            local fish_line='set -gx PATH $HOME/.zeno/bin $PATH'
            local fish_config="$HOME/.config/fish/config.fish"
            mkdir -p "$(dirname "$fish_config")"
            if [ ! -f "$fish_config" ] || ! grep -qF '.zeno/bin' "$fish_config"; then
                echo "$fish_line" >> "$fish_config"
                echo -e "  Added to ${GREEN}$fish_config${NC}"
            fi
            return
            ;;
        *)
            profile_file="$HOME/.profile"
            ;;
    esac

    if [ ! -f "$profile_file" ] || ! grep -qF '.zeno/bin' "$profile_file"; then
        echo "" >> "$profile_file"
        echo '# ZENO' >> "$profile_file"
        echo "$line" >> "$profile_file"
        echo -e "  Added to ${GREEN}$profile_file${NC}"
    fi
}

add_to_path

# --- Done ---
echo ""
echo -e "  ${GREEN}✅ ZENO installed!${NC}"
echo ""
echo -e "  Run:    ${BOLD}zeno${NC}"
echo -e "  Update: ${BOLD}zeno update${NC}"
echo ""

# When running via pipe (curl | bash), PATH changes don't persist in parent shell
if [ ! -t 0 ]; then
    shell_name="$(basename "$SHELL")"
    echo -e "  ${YELLOW}To start using zeno now, run:${NC}"
    case "$shell_name" in
        zsh)  echo -e "  ${GREEN}source ~/.zshrc${NC}" ;;
        fish) echo -e "  ${GREEN}source ~/.config/fish/config.fish${NC}" ;;
        bash)
            if [ -f "$HOME/.bash_profile" ]; then
                echo -e "  ${GREEN}source ~/.bash_profile${NC}"
            else
                echo -e "  ${GREEN}source ~/.bashrc${NC}"
            fi
            ;;
        *)    echo -e "  ${GREEN}source ~/.profile${NC}" ;;
    esac
    echo ""
else
    export PATH="$ZENO_BIN:$PATH"
fi
