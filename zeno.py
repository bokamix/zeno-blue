#!/usr/bin/env python3
"""ZENO - Your personal AI agent. One command to run everything."""
import os
import sys
import signal
import socket
import subprocess
import shutil
import webbrowser
import threading
from pathlib import Path

# When bundled with PyInstaller, resources are in sys._MEIPASS
# When running from source, they're in the script's directory
BUNDLED = getattr(sys, 'frozen', False)
if BUNDLED:
    BUNDLE_DIR = Path(sys._MEIPASS)
    ROOT = BUNDLE_DIR
else:
    ROOT = Path(__file__).parent.resolve()

VENV_DIR = Path.home() / ".zeno" / "venv"


def main():
    # In bundled mode, skip venv/deps/frontend - everything is included
    if not BUNDLED:
        _ensure_venv()
        _ensure_python_deps()
        _ensure_frontend()

    print("🚀 Starting ZENO...\n")

    # Setup data directories
    data_dir = Path.home() / ".zeno"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "data").mkdir(exist_ok=True)
    (data_dir / "workspace").mkdir(exist_ok=True)
    (data_dir / "workspace" / "artifacts").mkdir(exist_ok=True)

    # Set env defaults
    os.environ.setdefault("DATA_DIR", str(data_dir / "data"))
    os.environ.setdefault("WORKSPACE_DIR", str(data_dir / "workspace"))
    os.environ.setdefault("ARTIFACTS_DIR", str(data_dir / "workspace" / "artifacts"))
    os.environ.setdefault("DB_PATH", str(data_dir / "data" / "runtime.db"))
    os.environ.setdefault("SKILLS_DIR", str(ROOT / "user_container" / "skills"))

    # Load config from .env files (project root first, then ~/.zeno/.env overrides)
    project_env = ROOT / ".env"
    if project_env.exists():
        _load_dotenv(project_env)
    user_env = data_dir / ".env"
    if user_env.exists():
        _load_dotenv(user_env)

    port = int(os.environ.get("ZENO_PORT", "18000"))
    host = os.environ.get("ZENO_HOST", "127.0.0.1")

    _kill_existing(host, port)

    print(f"✅ ZENO running at http://{host}:{port}")
    print("   Opening browser...\n")

    threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    import uvicorn
    uvicorn.run(
        "user_container.app:app",
        host=host,
        port=port,
        log_level="info",
    )


def _kill_existing(host: str, port: int):
    """Kill any existing process on our port so restart always works."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        sock.connect((host, port))
        sock.close()
    except OSError:
        return  # Port is free

    # Port is in use - find and kill the process
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f"tcp:{port}"], text=True
        ).strip()
        for pid_str in out.splitlines():
            pid = int(pid_str)
            if pid != os.getpid():
                os.kill(pid, signal.SIGTERM)
        import time
        time.sleep(0.5)
        print(f"   Stopped previous ZENO instance (port {port})")
    except (subprocess.CalledProcessError, ProcessLookupError, ValueError):
        pass


# --- Bootstrap (source mode only) ---

def _ensure_venv():
    """Create venv with uv and re-exec inside it if not already in one."""
    if sys.prefix != sys.base_prefix:
        return

    venv_python = VENV_DIR / "bin" / "python"

    if not venv_python.exists():
        print("📦 Creating virtual environment (~/.zeno/venv)...")
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call(["uv", "venv", "--python", "3.12", str(VENV_DIR)])
        print("   Done.\n")

    os.environ["VIRTUAL_ENV"] = str(VENV_DIR)
    os.execv(str(venv_python), [str(venv_python), str(ROOT / "zeno.py")] + sys.argv[1:])


def _ensure_python_deps():
    """Install Python deps if missing."""
    try:
        import uvicorn, fastapi, anthropic  # noqa: F401,E401
    except ImportError:
        print("📦 Installing Python dependencies...")
        subprocess.check_call(["uv", "pip", "install", "-r", str(ROOT / "requirements.txt"), "-q"])
        print("   Done.\n")


def _ensure_frontend():
    """Build frontend if dist/ doesn't exist."""
    dist = ROOT / "frontend" / "dist"
    if dist.exists() and any(dist.iterdir()):
        return

    frontend = ROOT / "frontend"
    if not (frontend / "package.json").exists():
        return

    npm = shutil.which("npm")
    if not npm:
        print("⚠️  npm not found - skipping frontend build.")
        print("   Install Node.js: brew install node\n")
        return

    if not (frontend / "node_modules").exists():
        print("📦 Installing frontend dependencies...")
        subprocess.check_call([npm, "install", "--silent"], cwd=str(frontend),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("🔨 Building frontend...")
    subprocess.check_call([npm, "run", "build", "--silent"], cwd=str(frontend),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("   Done.\n")


def _load_dotenv(path: Path):
    """Simple .env loader."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                value = value.strip()
                # Strip quotes first
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                else:
                    # Strip inline comments (only for unquoted values)
                    if " #" in value:
                        value = value[:value.index(" #")].rstrip()
                os.environ.setdefault(key.strip(), value)


if __name__ == "__main__":
    main()
