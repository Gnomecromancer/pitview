"""NT4 client — connects to robot and streams topic updates."""
import threading
from typing import Callable

try:
    import ntcore
    NT_AVAILABLE = True
except ImportError:
    NT_AVAILABLE = False


class NTClient:
    def __init__(self, team: int = 1317, host: str | None = None):
        self.team = team
        self.host = host  # None = resolve from team number
        self._inst = None
        self._sub = None
        self._listeners: list[Callable] = []
        self._values: dict[str, object] = {}
        self._connected = False
        self._lock = threading.Lock()

    def start(self):
        if not NT_AVAILABLE:
            return
        self._inst = ntcore.NetworkTableInstance.getDefault()
        self._inst.startClient4("pitview")
        if self.host:
            self._inst.setServer(self.host)
        else:
            self._inst.setServerTeam(self.team)

        self._sub = ntcore.MultiSubscriber(self._inst, ["/"])
        self._inst.addConnectionListener(True, self._on_connection)
        self._inst.addListener(self._sub, ntcore.EventFlags.kValueAll, self._on_value)

    def _on_connection(self, event):
        self._connected = event.is_connected
        for cb in self._listeners:
            cb({"type": "connection", "connected": self._connected})

    def _on_value(self, event):
        if not hasattr(event.data, "topic"):
            return
        name = event.data.topic.getName()
        val = event.data.value
        py_val = self._convert(val)
        with self._lock:
            self._values[name] = py_val
        for cb in self._listeners:
            cb({"type": "value", "key": name, "value": py_val})

    def _convert(self, val):
        if val is None:
            return None
        t = val.type()
        if t == ntcore.NetworkTableType.kDouble:
            return val.getDouble()
        if t == ntcore.NetworkTableType.kString:
            return val.getString()
        if t == ntcore.NetworkTableType.kBoolean:
            return val.getBoolean()
        if t == ntcore.NetworkTableType.kInteger:
            return val.getInteger()
        if t == ntcore.NetworkTableType.kDoubleArray:
            return list(val.getDoubleArray())
        if t == ntcore.NetworkTableType.kStringArray:
            return list(val.getStringArray())
        if t == ntcore.NetworkTableType.kBooleanArray:
            return list(val.getBooleanArray())
        return str(val)

    def add_listener(self, cb: Callable):
        self._listeners.append(cb)

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._values)

    @property
    def connected(self) -> bool:
        return self._connected
