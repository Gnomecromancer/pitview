"""Polls RoboRIO HTTP API for system stats."""
import threading
import time
import requests

POLL_INTERVAL = 3.0


def _get(host: str, port: int, path: str, timeout: float = 1.5) -> dict | None:
    try:
        url = f"http://{host}:{port}{path}" if port != 80 else f"http://{host}{path}"
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def poll_system(host: str = "10.13.17.2", port: int = 80) -> dict:
    data = _get(host, port, "/api/v1/system/stats") or {}
    return {
        "cpu_percent": data.get("cpuUsage"),
        "memory_percent": data.get("memUsage"),
        "disk_percent": data.get("diskUsage"),
        "uptime": data.get("uptime"),
        "can_utilization": data.get("canUtilization"),
    }


def ping_robot(host: str = "10.13.17.2", port: int = 80) -> bool:
    try:
        url = f"http://{host}:{port}/" if port != 80 else f"http://{host}/"
        requests.get(url, timeout=1.0)
        return True
    except Exception:
        return False


class RioPoller:
    def __init__(self, on_update, host: str = "10.13.17.2", port: int = 80):
        self._on_update = on_update
        self._host = host
        self._port = port
        self._running = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            stats = poll_system(self._host, self._port)
            reachable = ping_robot(self._host, self._port)
            self._on_update({"system": stats, "reachable": reachable})
            time.sleep(POLL_INTERVAL)

    def stop(self):
        self._running = False
