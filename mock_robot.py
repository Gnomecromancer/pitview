"""
Mock FRC robot for pitview development.
Starts: NT4 server, fake RoboRIO HTTP API, fake radio page, fake MJPEG streams.
Usage: python mock_robot.py
Then: pitview --rio-host localhost --nt-host localhost
"""
import io
import math
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import ntcore
    NT_OK = True
except ImportError:
    NT_OK = False

# ── Ports ────────────────────────────────────────────────────────────────────
NT_PORT     = 5810   # NT4 server (pitview connects here)
RIO_PORT    = 5800   # Fake RoboRIO HTTP API
RADIO_PORT  = 5801   # Fake radio page
CAM_BOULDER = 1182
CAM_STONE   = 1184
CAM_PEBBLE  = 1186

# ── NT4 Server ───────────────────────────────────────────────────────────────
def start_nt_server():
    if not NT_OK:
        print("[NT] pyntcore not available, skipping NT server")
        return

    inst = ntcore.NetworkTableInstance.create()
    inst.startServer()
    print(f"[NT] Server started on port {NT_PORT}")

    ds   = inst.getTable("DriverStation")
    fms  = inst.getTable("FMSInfo")
    sd   = inst.getTable("SmartDashboard")
    pv   = inst.getTable("photonvision")

    battery_pub  = ds.getDoubleTopic("BatteryVoltage").publish()
    enabled_pub  = ds.getBooleanTopic("Enabled").publish()
    auto_pub     = ds.getBooleanTopic("Autonomous").publish()
    match_t_pub  = fms.getDoubleTopic("MatchTime").publish()
    event_pub    = fms.getStringTopic("EventName").publish()
    alliance_pub = fms.getStringTopic("IsRedAlliance").publish()

    shooter_pub  = sd.getStringTopic("Shooter/State").publish()
    hopper_pub   = sd.getStringTopic("Hopper/State").publish()
    intake_pub   = sd.getStringTopic("Intake/State").publish()
    speed_pub    = sd.getDoubleTopic("Swerve/Speed").publish()

    boulder_pub  = pv.getSubTable("BOULDER").getBooleanTopic("hasTarget").publish()
    stone_pub    = pv.getSubTable("STONE").getBooleanTopic("hasTarget").publish()
    pebble_pub   = pv.getSubTable("PEBBLE").getBooleanTopic("hasTarget").publish()

    # Static values
    event_pub.set("Mock Competition")
    alliance_pub.set("true")

    modes = ["DISABLED", "TELEOP", "AUTO"]
    subsystem_states = [
        ("IDLE", "EMPTY", "RETRACTED"),
        ("SPINNING", "LOADED", "DEPLOYED"),
        ("SHOOTING", "FEEDING", "INTAKING"),
    ]
    t = 0

    def update_loop():
        nonlocal t
        while True:
            t += 0.1
            phase = int(t / 10) % 3

            battery_pub.set(12.5 - 0.3 * math.sin(t * 0.05))
            enabled_pub.set(phase != 0)
            auto_pub.set(phase == 2)
            match_t_pub.set(max(0.0, 135.0 - (t % 150)))

            ss = subsystem_states[phase % len(subsystem_states)]
            shooter_pub.set(ss[0])
            hopper_pub.set(ss[1])
            intake_pub.set(ss[2])
            speed_pub.set(abs(math.sin(t * 0.3)) * 4.5)

            boulder_pub.set(math.sin(t * 0.7) > 0)
            stone_pub.set(math.sin(t * 0.5) > 0.3)
            pebble_pub.set(math.sin(t * 0.9) > -0.2)

            time.sleep(0.1)

    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()


# ── Fake RoboRIO HTTP ─────────────────────────────────────────────────────────
class RioHandler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def do_GET(self):
        import json, random
        if self.path == "/api/v1/system/stats":
            data = {
                "cpuUsage": 18.4 + random.uniform(-3, 3),
                "memUsage": 42.1 + random.uniform(-2, 2),
                "diskUsage": 31.0,
                "uptime": int(time.time() % 86400),
                "canUtilization": 12.3 + random.uniform(-1, 1),
            }
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            body = b"<h2>Mock RoboRIO</h2><p>Team 1317</p>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)


# ── Fake Radio Page ───────────────────────────────────────────────────────────
class RadioHandler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def do_GET(self):
        body = b"""<!DOCTYPE html>
<html><head><title>FRC Radio</title>
<style>body{font-family:sans-serif;background:#111;color:#eee;padding:20px}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #333;padding:8px}
th{background:#222}.green{color:#4caf50}.val{font-weight:bold}</style></head>
<body>
<h2>&#128246; VH-109 Radio &mdash; Team 1317</h2>
<table>
<tr><th>Property</th><th>Value</th></tr>
<tr><td>SSID</td><td class="val">1317_Robot</td></tr>
<tr><td>Status</td><td class="green val">Connected</td></tr>
<tr><td>Signal</td><td class="val">-52 dBm</td></tr>
<tr><td>Bandwidth (up)</td><td class="val">1.2 Mbps</td></tr>
<tr><td>Bandwidth (down)</td><td class="val">3.8 Mbps</td></tr>
<tr><td>IP Address</td><td class="val">10.13.17.1</td></tr>
<tr><td>Clients</td><td class="val">2</td></tr>
</table>
<p style="color:#555;margin-top:20px">Mock radio page &mdash; pitview dev mode</p>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


# ── MJPEG Stream ──────────────────────────────────────────────────────────────
COLORS = {
    CAM_BOULDER: (30, 80, 200),
    CAM_STONE:   (200, 60, 30),
    CAM_PEBBLE:  (30, 160, 60),
}
LABELS = {
    CAM_BOULDER: "BOULDER (Shooter)",
    CAM_STONE:   "STONE (Battery-side)",
    CAM_PEBBLE:  "PEBBLE (Intake)",
}


def _make_frame(port: int, frame_n: int) -> bytes:
    if not PIL_OK:
        return b""
    color = COLORS.get(port, (100, 100, 100))
    label = LABELS.get(port, "Camera")

    # Pulse brightness to simulate a live feed
    pulse = int(20 * math.sin(frame_n * 0.15))
    c = tuple(max(0, min(255, v + pulse)) for v in color)

    img = Image.new("RGB", (640, 480), color=c)
    draw = ImageDraw.Draw(img)

    # Grid lines
    for x in range(0, 640, 80):
        draw.line([(x, 0), (x, 480)], fill=tuple(v // 2 for v in c), width=1)
    for y in range(0, 480, 60):
        draw.line([(0, y), (640, y)], fill=tuple(v // 2 for v in c), width=1)

    # Crosshair
    draw.line([(320, 200), (320, 280)], fill="white", width=2)
    draw.line([(280, 240), (360, 240)], fill="white", width=2)
    draw.ellipse([(290, 210), (350, 270)], outline="white", width=2)

    draw.rectangle([(0, 0), (640, 30)], fill=(0, 0, 0, 180))
    draw.text((10, 6), f"{label}  |  frame {frame_n}", fill="white")
    draw.text((10, 450), "MOCK FEED — pitview dev", fill=(200, 200, 200))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return buf.getvalue()


def _mjpeg_frame(port: int, frame_n: int) -> bytes:
    jpeg = _make_frame(port, frame_n)
    if not jpeg:
        return b""
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
        + jpeg + b"\r\n"
    )


def make_mjpeg_handler(port: int):
    class MjpegHandler(BaseHTTPRequestHandler):
        _port = port
        def log_message(self, *_): pass
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            n = 0
            try:
                while True:
                    frame = _mjpeg_frame(self._port, n)
                    if frame:
                        self.wfile.write(frame)
                        self.wfile.flush()
                    n += 1
                    time.sleep(1 / 15)
            except (BrokenPipeError, ConnectionResetError):
                pass
    return MjpegHandler


def serve(handler, port, name):
    srv = HTTPServer(("0.0.0.0", port), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    print(f"[{name}] http://localhost:{port}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not PIL_OK:
        print("[WARN] Pillow not installed — camera feeds will be blank. pip install pillow")

    start_nt_server()
    serve(RioHandler, RIO_PORT, "RIO API")
    serve(RadioHandler, RADIO_PORT, "Radio")
    serve(make_mjpeg_handler(CAM_BOULDER), CAM_BOULDER, "BOULDER cam")
    serve(make_mjpeg_handler(CAM_STONE),   CAM_STONE,   "STONE cam")
    serve(make_mjpeg_handler(CAM_PEBBLE),  CAM_PEBBLE,  "PEBBLE cam")

    print()
    print("Mock robot running. Now start pitview with:")
    print("  pitview --rio-host localhost --nt-host localhost --radio-port 5801")
    print()
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped.")
