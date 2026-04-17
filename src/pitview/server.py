"""FastAPI backend — serves the dashboard and streams robot data via WebSocket."""
import asyncio
from pathlib import Path

import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .nt import NTClient
from .rio import RioPoller

STATIC_DIR = Path(__file__).parent / "static"

# Runtime config — overridden by CLI before app starts
config: dict = {
    "rio_host": "10.13.17.2",
    "rio_port": 5800,
    "photon_host": "photonvision.local",
    "photon_port": 5800,
    "radio_host": "10.13.17.1",
    "radio_port": 80,
    "nt_host": None,  # None = use team number
    "nt_team": 1317,
}

app = FastAPI()
nt: NTClient = None
_rio_poller: RioPoller = None
_rio_state: dict = {"system": {}, "reachable": False}
_ws_clients: set[WebSocket] = set()
_loop: asyncio.AbstractEventLoop | None = None


def _rio_update(data: dict):
    global _rio_state
    _rio_state = data
    _schedule_broadcast({"type": "rio", **data})


async def _broadcast(msg: dict):
    dead = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


def _schedule_broadcast(msg: dict):
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast(msg), _loop)


def _nt_update(event: dict):
    _schedule_broadcast(event)


@app.on_event("startup")
async def startup():
    global _loop, nt, _rio_poller
    _loop = asyncio.get_event_loop()

    nt = NTClient(
        team=config["nt_team"],
        host=config["nt_host"],
    )
    nt.add_listener(_nt_update)
    nt.start()

    _rio_poller = RioPoller(
        on_update=_rio_update,
        host=config["rio_host"],
        port=config["rio_port"],
    )
    _rio_poller.start()


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (STATIC_DIR / "index.html").read_text()
    # Inject runtime config for frontend
    radio_url = f"http://{config['radio_host']}:{config['radio_port']}"
    if config["radio_port"] == 80:
        radio_url = f"http://{config['radio_host']}"
    photon_url = f"http://{config['photon_host']}:{config['photon_port']}"
    html = html.replace("{{RADIO_URL}}", radio_url).replace("{{PHOTON_URL}}", photon_url)
    return html


@app.get("/api/snapshot")
async def snapshot():
    return {
        "nt": nt.snapshot() if nt else {},
        "nt_connected": nt.connected if nt else False,
        "rio": _rio_state,
    }


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    await ws.send_json({
        "type": "snapshot",
        "nt": nt.snapshot() if nt else {},
        "nt_connected": nt.connected if nt else False,
        "rio": _rio_state,
    })
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(ws)


def _proxy(url: str) -> Response:
    try:
        r = requests.get(url, timeout=3.0)
        return Response(content=r.content, media_type=r.headers.get("content-type", "text/html"))
    except Exception:
        return Response(content=b"<h2>Unreachable</h2>", media_type="text/html", status_code=503)


@app.get("/proxy/radio/{path:path}")
async def proxy_radio(path: str = ""):
    host = config["radio_host"]
    port = config["radio_port"]
    url = f"http://{host}:{port}/{path}" if port != 80 else f"http://{host}/{path}"
    return _proxy(url)


@app.get("/proxy/photon/{path:path}")
async def proxy_photon(path: str = ""):
    return _proxy(f"http://{config['photon_host']}:{config['photon_port']}/{path}")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
