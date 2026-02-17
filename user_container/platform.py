"""Cross-platform detection and helpers.

Centralizes all platform-specific logic so the rest of the codebase
can remain platform-agnostic.
"""

import os
import sys
import subprocess
import shutil

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform == "linux"
IS_POSIX = os.name == "posix"


def _detect_docker() -> bool:
    """Detect if running inside a Docker container."""
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        return False


def _detect_sandbox_user() -> bool:
    """Check if our Docker 'sandbox' user exists (not the macOS built-in one).

    On macOS there's a built-in 'sandbox' user (uid=60, home=/var/empty)
    which is NOT ours. Our Docker sandbox user has home=/home/sandbox.
    """
    try:
        import pwd
        pw = pwd.getpwnam("sandbox")
        return pw.pw_dir == "/home/sandbox"
    except (KeyError, ImportError):
        return False


def _detect_resource_limits() -> bool:
    """Check if POSIX resource limits are available."""
    try:
        import resource  # noqa: F401
        return True
    except ImportError:
        return False


IS_DOCKER = _detect_docker()
HAS_SANDBOX_USER = _detect_sandbox_user()
HAS_RESOURCE_LIMITS = _detect_resource_limits()


def get_shell_command(script: str) -> list[str]:
    """Return the platform-appropriate command to run a shell script string.

    On POSIX: ['/bin/bash', '-c', script]  (or sh if bash missing)
    On Windows: ['powershell', '-Command', script]
    """
    if IS_WINDOWS:
        return ["powershell", "-Command", script]
    # Prefer bash, fall back to sh
    bash = shutil.which("bash") or "/bin/bash"
    return [bash, "-c", script]


def get_kill_signal():
    """Return the appropriate kill signal for the platform."""
    import signal
    if IS_POSIX:
        return signal.SIGKILL
    return signal.SIGTERM


def find_pids_on_port(port: int) -> list[int]:
    """Find PIDs listening on a given port. Cross-platform."""
    pids = []
    try:
        if IS_POSIX:
            out = subprocess.check_output(
                ["lsof", "-t", f"-i:{port}"],
                stderr=subprocess.DEVNULL,
            )
            for line in out.decode().strip().split("\n"):
                if line.strip():
                    pids.append(int(line.strip()))
        elif IS_WINDOWS:
            out = subprocess.check_output(
                ["netstat", "-ano", "-p", "TCP"],
                stderr=subprocess.DEVNULL,
            )
            for line in out.decode().splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        try:
                            pids.append(int(parts[-1]))
                        except ValueError:
                            pass
    except Exception:
        pass
    return pids
