import subprocess
import os
import pwd
import resource
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime


def _demote_to_sandbox():
    """
    Switch to sandbox user before exec.
    This prevents user-generated code from accessing sensitive files like /app/secrets.json.
    """
    try:
        pw = pwd.getpwnam('sandbox')
        os.setgid(pw.pw_gid)
        os.setuid(pw.pw_uid)
    except KeyError:
        # sandbox user doesn't exist (dev environment without Docker)
        print("Warning: sandbox user not found - running without privilege drop (dev environment)")


def _setup_process_limits(demote: bool = True):
    """
    Set resource limits for child processes to prevent DoS attacks.
    Called via preexec_fn before subprocess execution.

    Args:
        demote: If True, switch to sandbox user (for user commands).
                If False, stay as root (for skills that need secrets.json).
    """
    # First demote user if requested (must be done before resource limits)
    if demote:
        _demote_to_sandbox()

    try:
        # For user commands (demote=True): apply strict limits
        # For skills (demote=False): skip memory limit (Chromium needs more)
        if demote:
            # Max 2GB virtual memory per process
            mem_limit = 2 * 1024 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))

        # Max 500MB file size (allows large Python packages like pyarrow)
        file_limit = 500 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))

        # Max 300 child processes (prevents fork bombs)
        # Note: Must match ulimits.nproc in docker-compose.yml
        resource.setrlimit(resource.RLIMIT_NPROC, (300, 300))

        # Max 60 seconds CPU time (skip for skills - browser ops can take longer)
        if demote:
            resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    except (ValueError, resource.error):
        # Some limits may not be available on all systems
        pass


@dataclass
class RunResult:
    cmd: List[str]
    cwd: Optional[str]
    code: int
    stdout: str
    stderr: str
    started_at: str
    finished_at: str

class Runner:
    """
    Short-lived command runner. Use Supervisor for long-lived services.
    """
    def __init__(self):
        pass

    def run(self, cmd: List[str], cwd: Optional[str] = None, timeout_s: int = 60, env: Optional[Dict[str, str]] = None, demote: bool = True) -> RunResult:
        """
        Run a command with resource limits and optional user demotion.

        Args:
            cmd: Command to run
            cwd: Working directory
            timeout_s: Timeout in seconds
            env: Environment variables
            demote: If True, run as sandbox user (default). If False, run as root (for skills).
        """
        if not cmd:
            raise ValueError("Empty command")

        def preexec():
            _setup_process_limits(demote=demote)

        started = datetime.utcnow().isoformat() + "Z"
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            preexec_fn=preexec,  # Apply resource limits + optional user demotion
        )
        finished = datetime.utcnow().isoformat() + "Z"
        return RunResult(
            cmd=cmd,
            cwd=cwd,
            code=proc.returncode,
            stdout=proc.stdout[-20000:],  # cap
            stderr=proc.stderr[-20000:],
            started_at=started,
            finished_at=finished,
        )
