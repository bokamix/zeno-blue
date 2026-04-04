#!/bin/bash
ZENO_APP="$HOME/.zeno/app"
ZENO_LAUNCHER="$HOME/.zeno/bin/zeno"

_current_version() {
    local build_info="$ZENO_APP/.build_info"
    if [ -f "$build_info" ]; then
        grep '^BUILD_VERSION=' "$build_info" | cut -d'=' -f2
    else
        echo "dev"
    fi
}

_latest_version() {
    curl -fsSL --max-time 5 "https://api.github.com/repos/bokamix/zeno-blue/releases/latest" \
        2>/dev/null | grep -o '"tag_name":\s*"[^"]*"' | cut -d'"' -f4
}

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
        CURRENT=$(_current_version)
        echo "  Checking for updates..."
        LATEST=$(_latest_version)

        if [ -z "$LATEST" ]; then
            echo "  Could not reach GitHub. Check your connection."
            echo ""
            exit 1
        fi

        # Tag format: build-{sha} or semver
        LATEST_SHORT="${LATEST#build-}"

        if [ "$CURRENT" = "$LATEST_SHORT" ] || [ "$CURRENT" = "$LATEST" ]; then
            echo "  ✅ Already up to date ($CURRENT)"
            echo ""
            exit 0
        fi

        echo "  Updating $CURRENT → $LATEST_SHORT..."

        tmpfile=$(mktemp)
        trap 'rm -f "$tmpfile"' EXIT
        asset_url=$(curl -fsSL "https://api.github.com/repos/bokamix/zeno-blue/releases/latest" | grep -o '"browser_download_url":\s*"[^"]*zeno-release\.tar\.gz"' | cut -d'"' -f4)
        if [ -z "$asset_url" ]; then
            echo "  Failed to find release asset URL"
            exit 1
        fi
        curl -fsSL "$asset_url" -o "$tmpfile"

        rm -rf "$ZENO_APP"
        mkdir -p "$ZENO_APP"
        tar xzf "$tmpfile" -C "$ZENO_APP"

        _ensure_thin_launcher

        echo "  ✅ Updated to $LATEST_SHORT"
        echo ""
        ;;
    serve)
        exec bash "$ZENO_APP/scripts/serve.sh" "${@:2}"
        ;;
    reset-password)
        echo ""
        while true; do
            echo -n "  New password: "
            read -rs NEW_PASSWORD
            echo ""
            echo -n "  Confirm password: "
            read -rs NEW_PASSWORD_CONFIRM
            echo ""
            if [ -z "$NEW_PASSWORD" ]; then
                echo "  Password cannot be empty."
            elif [ "$NEW_PASSWORD" != "$NEW_PASSWORD_CONFIRM" ]; then
                echo "  Passwords don't match, try again."
            else
                break
            fi
        done

        DB_PATH="${DB_PATH:-$HOME/.zeno/data/runtime.db}"

        uv run --python 3.12 - "$NEW_PASSWORD" "$DB_PATH" << 'PYEOF'
import sys, bcrypt, sqlite3
password, db_path = sys.argv[1], sys.argv[2]
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
con = sqlite3.connect(db_path)
con.execute("INSERT INTO user_settings (key, value, updated_at) VALUES ('auth_password_hash', ?, datetime('now')) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at", (hashed,))
con.commit()
con.close()
print("  ✅ Password reset. Restart ZENO to apply.")
PYEOF
        echo ""
        ;;
    version|-v|--version)
        echo "$(_current_version)"
        ;;
    help|--help|-h)
        echo ""
        echo "  Usage: zeno [command]"
        echo ""
        echo "  Commands:"
        echo "    (none)            Start ZENO"
        echo "    update            Update to latest version"
        echo "    serve             Deploy with HTTPS (Linux VPS)"
        echo "    reset-password    Reset access password"
        echo "    version, -v       Show current version"
        echo "    help              Show this help"
        echo ""
        ;;
    *)
        exec uv run --python 3.12 "$ZENO_APP/zeno.py" "$@"
        ;;
esac
