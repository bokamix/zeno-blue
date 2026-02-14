#!/bin/bash
# Build ZENO.app - self-contained macOS application
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${GREEN}Building ZENO.app...${NC}"
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

PYTHON_CMD=$(find_python)
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Python >= 3.10 not found.${NC}"
    echo "  brew install python@3.12"
    exit 1
fi

if ! command -v npm &>/dev/null; then
    echo -e "${RED}npm not found. Install Node.js first.${NC}"
    echo "  brew install node"
    exit 1
fi

PYTHON_VERSION=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo -e "  Python: ${GREEN}$PYTHON_VERSION${NC} ($(command -v $PYTHON_CMD))"

# Clean previous build venv if Python version changed
BUILD_VENV="$SCRIPT_DIR/.build-venv"
if [ -f "$BUILD_VENV/bin/python" ]; then
    VENV_VER=$("$BUILD_VENV/bin/python" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "")
    CMD_VER=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ "$VENV_VER" != "$CMD_VER" ]; then
        echo -e "  ${YELLOW}Recreating build venv (Python version changed)...${NC}"
        rm -rf "$BUILD_VENV"
    fi
fi

# Setup build venv
if [ ! -f "$BUILD_VENV/bin/python" ]; then
    echo -e "${YELLOW}[1/4] Creating build environment...${NC}"
    "$PYTHON_CMD" -m venv "$BUILD_VENV"
    "$BUILD_VENV/bin/pip" install --upgrade pip -q
fi
PIP="$BUILD_VENV/bin/pip"
PYTHON="$BUILD_VENV/bin/python"

# Install deps + PyInstaller
echo -e "${YELLOW}[2/4] Installing dependencies...${NC}"
$PIP install -r requirements.txt -q
$PIP install pyinstaller -q

# Build frontend
echo -e "${YELLOW}[3/4] Building frontend...${NC}"
(cd frontend && npm install --silent && npm run build --silent)

# Bundle with PyInstaller
echo -e "${YELLOW}[4/4] Packaging app...${NC}"
$PYTHON -m PyInstaller zeno.spec --clean --noconfirm 2>&1 | tail -5

echo ""
if [ -d "dist/ZENO.app" ]; then
    SIZE=$(du -sh "dist/ZENO.app" | cut -f1)
    echo -e "${GREEN}✅ Built: dist/ZENO.app ($SIZE)${NC}"
    echo ""
    echo "  To run:  open dist/ZENO.app"
    echo "  To distribute: create a DMG or zip dist/ZENO.app"
else
    echo -e "${RED}❌ Build failed. Check output above.${NC}"
    exit 1
fi
