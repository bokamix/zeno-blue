import socket
from dataclasses import dataclass

@dataclass
class PortRange:
    start: int
    end: int  # inclusive

class PortManager:
    def __init__(self, port_range: PortRange):
        self.port_range = port_range

    def _is_free(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            try:
                s.bind(("0.0.0.0", port))
                return True
            except OSError:
                return False

    def allocate(self) -> int:
        for port in range(self.port_range.start, self.port_range.end + 1):
            if self._is_free(port):
                return port
        raise RuntimeError("No free ports in pool")
