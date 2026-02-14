#!/bin/bash
# ZENO installer - curl -fsSL https://raw.githubusercontent.com/bokamix/zeno-blue/main/install.sh | bash
set -e

ZENO_HOME="$HOME/.zeno"
ZENO_APP="$ZENO_HOME/app"
ZENO_BIN="$ZENO_HOME/bin"
TARBALL_URL="https://github.com/bokamix/zeno-blue/archive/refs/heads/main.tar.gz"
MIN_PYTHON="3.10"

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

# --- Check Python >= 3.10 ---
find_python() {
    for cmd in python3.13 python3.12 python3.11 python3.10 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            if [ -n "$version" ]; then
                major=$(echo "$version" | cut -d. -f1)
                minor=$(echo "$version" | cut -d. -f2)
                if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                    echo "$cmd"
                    return 0
                fi
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python)

if [ -z "$PYTHON" ]; then
    echo -e "  ${RED}Python >= $MIN_PYTHON not found.${NC}"
    echo ""
    if [ "$OS_NAME" = "macOS" ]; then
        if command -v brew &>/dev/null; then
            echo "  Install with Homebrew:"
            echo -e "  ${GREEN}brew install python@3.12${NC}"
        else
            echo "  Install Homebrew first:"
            echo -e "  ${GREEN}/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${NC}"
            echo ""
            echo "  Then install Python:"
            echo -e "  ${GREEN}brew install python@3.12${NC}"
        fi
    else
        echo "  Install Python:"
        echo -e "  ${GREEN}sudo apt update && sudo apt install python3.12 python3.12-venv${NC}"
    fi
    echo ""
    echo "  Then run this installer again."
    exit 1
fi

PYTHON_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo -e "  Python:  ${GREEN}$PYTHON_VERSION${NC} ($(command -v "$PYTHON"))"

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

find_python() {
    for cmd in python3.13 python3.12 python3.11 python3.10 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            if [ -n "$version" ]; then
                major=$(echo "$version" | cut -d. -f1)
                minor=$(echo "$version" | cut -d. -f2)
                if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                    echo "$cmd"
                    return 0
                fi
            fi
        fi
    done
    return 1
}

case "${1:-}" in
    update)
        echo ""
        echo "  Updating ZENO..."
        tmpfile=$(mktemp)
        trap 'rm -f "$tmpfile"' EXIT
        curl -fsSL "https://github.com/bokamix/zeno-blue/archive/refs/heads/main.tar.gz" -o "$tmpfile"
        rm -rf "$ZENO_APP"
        mkdir -p "$ZENO_APP"
        tar xzf "$tmpfile" --strip-components=1 -C "$ZENO_APP"
        echo "  ✅ ZENO updated!"
        echo ""
        ;;
    *)
        PYTHON=$(find_python)
        if [ -z "$PYTHON" ]; then
            echo "  ❌ Python >= 3.10 not found."
            echo "  Install: brew install python@3.12"
            exit 1
        fi
        exec "$PYTHON" "$ZENO_APP/zeno.py" "$@"
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

# Check if ~/.zeno/bin is already in current PATH
if ! echo "$PATH" | tr ':' '\n' | grep -qF "$ZENO_BIN"; then
    echo -e "  ${YELLOW}Restart your terminal or run:${NC}"
    shell_name="$(basename "$SHELL")"
    case "$shell_name" in
        zsh)  echo -e "  ${GREEN}source ~/.zshrc${NC}" ;;
        bash)
            if [ -f "$HOME/.bash_profile" ]; then
                echo -e "  ${GREEN}source ~/.bash_profile${NC}"
            else
                echo -e "  ${GREEN}source ~/.bashrc${NC}"
            fi
            ;;
        fish) echo -e "  ${GREEN}source ~/.config/fish/config.fish${NC}" ;;
        *)    echo -e "  ${GREEN}source ~/.profile${NC}" ;;
    esac
    echo ""
fi
