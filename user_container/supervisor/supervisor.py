import subprocess
import os
import signal
import threading
import time
import json
from dataclasses import dataclass
from typing import Dict, Optional, List, Any

# We assume this is run in an environment where user_container package is available
from user_container.db.db import DB
from user_container.security import get_safe_env
from user_container.runner.runner import _demote_to_sandbox

# Directory for app logs
LOGS_DIR = "/workspace/logs"

@dataclass
class ProcInfo:
    pid: int
    cmd: List[str]
    cwd: str
    port: Optional[int]
    name: str

class Supervisor:
    """
    Process supervisor with persistence and auto-restart capabilities.
    """
    def __init__(self, db: Optional[DB] = None):
        self._procs: Dict[str, subprocess.Popen] = {}
        self._meta: Dict[str, ProcInfo] = {}
        self._log_files: Dict[str, Any] = {}  # Open log file handles
        self.db = db
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self, proc_id: str, cmd: List[str], cwd: str, name: str, port: Optional[int] = None) -> ProcInfo:
        if proc_id in self._procs and self.is_alive(proc_id):
            return self._meta[proc_id]

        # Ensure port is free if specified
        if port:
            self._kill_process_on_port(port)
            
        # Replace {port} placeholder in cmd
        final_cmd = []
        for arg in cmd:
            if "{port}" in arg and port is not None:
                final_cmd.append(arg.format(port=port))
            else:
                final_cmd.append(arg)

        # SECURITY: User apps get filtered environment (no API keys)
        safe_env = get_safe_env()

        # Add Skill API env vars for this app
        app_env = safe_env.copy()
        app_env['APP_ID'] = proc_id
        app_env['SKILL_API_URL'] = 'http://localhost:8000/internal'
        # Get api_token from DB if available
        if self.db:
            app_record = self.db.fetchone("SELECT api_token FROM apps WHERE app_id = ?", (proc_id,))
            if app_record and app_record.get('api_token'):
                app_env['SKILL_API_TOKEN'] = app_record['api_token']

        # SECURITY: User apps run as sandbox user (can't access /app/secrets.json)
        # Create logs directory and open log file
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = os.path.join(LOGS_DIR, f"{proc_id}.log")
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)  # Line buffered

        p = subprocess.Popen(
            final_cmd,
            cwd=cwd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=app_env,
            preexec_fn=_demote_to_sandbox,
        )
        info = ProcInfo(pid=p.pid, cmd=cmd, cwd=cwd, port=port, name=name) # Store original cmd with placeholder
        self._procs[proc_id] = p
        self._meta[proc_id] = info
        self._log_files[proc_id] = log_file  # Keep reference to close later
        return info

    def stop(self, proc_id: str) -> None:
        p = self._procs.get(proc_id)
        if not p:
            return
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            try:
                os.kill(p.pid, signal.SIGKILL)
            except Exception:
                pass
        finally:
            self._procs.pop(proc_id, None)
            # Close log file if open
            log_file = self._log_files.pop(proc_id, None)
            if log_file:
                try:
                    log_file.close()
                except Exception:
                    pass

    def is_alive(self, proc_id: str) -> bool:
        p = self._procs.get(proc_id)
        if not p:
            return False
        return p.poll() is None

    def tail_logs(self, proc_id: str, max_lines: int = 200) -> str:
        """Read last N lines from app's log file."""
        log_path = os.path.join(LOGS_DIR, f"{proc_id}.log")
        return self._tail_file(log_path, max_lines)

    @staticmethod
    def _tail_file(file_path: str, max_lines: int) -> str:
        """Read last N lines from a file (like tail -n)."""
        if not os.path.exists(file_path):
            return ""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                # Simple approach: read all lines and take last N
                # For very large files, a more efficient approach would seek from end
                lines = f.readlines()
                tail_lines = lines[-max_lines:] if len(lines) > max_lines else lines
                return "".join(tail_lines)
        except Exception:
            return ""

    def list(self) -> Dict[str, ProcInfo]:
        return dict(self._meta)

    def _kill_process_on_port(self, port: int):
        """
        Kill any process listening on the given port.
        """
        try:
            # Find PID using lsof
            pid_bytes = subprocess.check_output(["lsof", "-t", f"-i:{port}"], stderr=subprocess.DEVNULL)
            pids = pid_bytes.decode().strip().split('\n')
            for pid_str in pids:
                if pid_str:
                    pid = int(pid_str)
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        except Exception:
            # lsof missing or no process found
            pass

    def start_monitoring(self, interval: int = 5):
        if self._monitor_thread is not None:
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self, interval: int):
        # Initial reconcile
        try:
            self.reconcile()
        except Exception as e:
            print(f"Supervisor initial reconcile error: {e}")

        while not self._stop_event.is_set():
            time.sleep(interval)
            try:
                self.reconcile()
            except Exception as e:
                print(f"Supervisor reconcile error: {e}")

    def reconcile(self):
        if not self.db:
            return

        # 1. Fetch expected state from DB
        # We only care about apps that SHOULD be running
        rows = self.db.fetchall("SELECT * FROM apps WHERE status='running'")
        
        for row in rows:
            app_id = row["app_id"]
            
            # Check if running in memory
            if self.is_alive(app_id):
                continue
                
            # Not running, but should be.
            # Need to restart.
            print(f"Supervisor: Restarting app {app_id}...")
            
            try:
                cmd_str = row.get("cmd")
                if not cmd_str:
                     print(f"Supervisor: Missing cmd for {app_id}, cannot restart.")
                     continue
                
                cmd = json.loads(cmd_str)
                cwd = row["cwd"]
                name = row["name"]
                port = int(row["port"])
                
                self.start(app_id, cmd, cwd, name, port)
                
                # Check immediate crash
                time.sleep(0.5)
                if not self.is_alive(app_id):
                    print(f"Supervisor: App {app_id} crashed immediately.")
                    # Try to get logs
                    logs = self.tail_logs(app_id)
                    if logs:
                        print(f"Supervisor: App {app_id} logs:\n{logs}")
            except FileNotFoundError:
                print(f"Supervisor: Directory not found for {app_id}, stopping app.")
                self.db.execute("UPDATE apps SET status=? WHERE app_id=?", ("stopped", app_id))
            except Exception as e:
                print(f"Supervisor: Failed to restart {app_id}: {e}")
