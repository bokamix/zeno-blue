#!/bin/bash
# ZENO - One command to rule them all
set -e

ZENO_DIR="$HOME/.zeno"
VENV_DIR="$ZENO_DIR/venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MIN_PYTHON="3.10"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "  ███████╗███████╗███╗   ██╗ ██████╗ "
echo "  ╚══███╔╝██╔════╝████╗  ██║██╔═══██╗"
echo "    ███╔╝ █████╗  ██╔██╗ ██║██║   ██║"
echo "   ███╔╝  ██╔══╝  ██║╚██╗██║██║   ██║"
echo "  ███████╗███████╗██║ ╚████║╚██████╔╝"
echo "  ╚══════╝╚══════╝╚═╝  ╚═══╝ ╚═════╝ "
echo ""

# --- Find Python >= 3.10 ---
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
    echo -e "${RED}Python >= $MIN_PYTHON not found.${NC}"
    echo ""
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
    echo ""
    echo "  Then run this script again."
    exit 1
fi

PYTHON_PATH=$(command -v "$PYTHON")
PYTHON_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo -e "  Python: ${GREEN}$PYTHON_VERSION${NC} ($PYTHON_PATH)"

# --- Create venv if needed ---
VENV_PYTHON="$VENV_DIR/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "  ${YELLOW}Creating virtual environment...${NC}"
    mkdir -p "$ZENO_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
    "$VENV_PYTHON" -m pip install --upgrade pip -q
fi

# --- Install deps if needed ---
if ! "$VENV_PYTHON" -c "import uvicorn, fastapi, anthropic" 2>/dev/null; then
    echo -e "  ${YELLOW}Installing dependencies...${NC}"
    "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" -q
fi

# --- Check npm & build frontend if needed ---
if [ ! -d "$SCRIPT_DIR/frontend/dist" ] || [ -z "$(ls -A "$SCRIPT_DIR/frontend/dist" 2>/dev/null)" ]; then
    if command -v npm &>/dev/null; then
        if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
            echo -e "  ${YELLOW}Installing frontend dependencies...${NC}"
            (cd "$SCRIPT_DIR/frontend" && npm install --silent)
        fi
        echo -e "  ${YELLOW}Building frontend...${NC}"
        (cd "$SCRIPT_DIR/frontend" && npm run build --silent)
    else
        echo -e "  ${YELLOW}npm not found - skipping frontend build.${NC}"
        echo "  Install Node.js for the UI: brew install node"
    fi
fi

echo ""

# --- Run ---
exec "$VENV_PYTHON" "$SCRIPT_DIR/zeno.py"
