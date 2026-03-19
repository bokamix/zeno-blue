#!/bin/bash
ZENO_APP="$HOME/.zeno/app"
ZENO_LAUNCHER="$HOME/.zeno/bin/zeno"

# --- Ensure launcher is the thin wrapper ---
_ensure_thin_launcher() {
    if [ -f "$ZENO_LAUNCHER" ]; then
        if ! grep -q "zeno-cli.sh" "$ZENO_LAUNCHER" 2>/dev/null; then
            cat > "$ZENO_LAUNCHER" << 'WRAPPER'
#!/bin/bash
exec bash "$HOME/.zeno/app/scripts/zeno-cli.sh" "$@"
WRAPPER
            chmod +x "$ZENO_LAUNCHER"
        fi
    fi
}

case "${1:-}" in
    update)
        echo ""
        echo "  Updating ZENO..."
        tmpfile=$(mktemp)
        trap 'rm -f "$tmpfile"' EXIT
        # Get tarball URL from latest GitHub release (tag varies per build)
        asset_url=$(curl -fsSL "https://api.github.com/repos/bokamix/zeno-blue/releases/latest" | grep -o '"browser_download_url":\s*"[^"]*zeno-release\.tar\.gz"' | cut -d'"' -f4)
        if [ -z "$asset_url" ]; then
            echo "  Failed to find release asset URL"
            exit 1
        fi
        curl -fsSL "$asset_url" -o "$tmpfile"

        rm -rf "$ZENO_APP"
        mkdir -p "$ZENO_APP"
        tar xzf "$tmpfile" -C "$ZENO_APP"

        # Migrate launcher to thin wrapper (for old installations)
        _ensure_thin_launcher

        echo "  ✅ ZENO updated!"
        echo ""
        ;;
    serve)
        exec bash "$ZENO_APP/scripts/serve.sh" "${@:2}"
        ;;
    *)
        exec uv run --python 3.12 "$ZENO_APP/zeno.py" "$@"
        ;;
esac
