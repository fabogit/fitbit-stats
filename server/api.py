import hmac
import logging
import multiprocessing
import os
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import date
from typing import List, Literal

import uvicorn
from pydantic import BaseModel, Field, field_validator
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

import config
from jobs import LAST_RUN_FILE, JobBusy, JobManager, JobSnapshot
from modules.briefing import get_daily_brief
from modules.etl import JSON_FILE
from modules.pipeline import run_pipeline
from modules.run_config import (
    AGE_YEARS_MAX, AGE_YEARS_MIN, HEIGHT_CM_MAX, HEIGHT_CM_MIN, WEIGHT_KG_MAX, WEIGHT_KG_MIN,
    EtlConfig, Profile, age_on)

# Change working directory so relative paths in config.py work correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

TOKEN_ENV = "FITSTATS_API_TOKEN"
ORIGINS_ENV = "FITSTATS_ALLOWED_ORIGINS"
WS_PROTOCOL = "fitstats"
WS_TOKEN_PREFIX = "token."
OPEN_PATHS = {"/api/health"}

# Origins of the application itself: desktop webview and Vite dev server.
APP_ORIGINS = [
    "tauri://localhost",
    "http://tauri.localhost",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

logger = logging.getLogger("uvicorn.error")


def build_allowed_origins(extra: str = "") -> List[str]:
    """App origins plus the comma-separated extra web origins (never '*')."""
    origins = list(APP_ORIGINS)
    for origin in (extra or "").split(","):
        origin = origin.strip()
        if origin and origin != "*" and origin not in origins:
            origins.append(origin)
    return origins


# Computed once; shared by the CORS middleware and the WebSocket origin check.
ALLOWED_ORIGINS = build_allowed_origins(os.environ.get(ORIGINS_ENV, ""))


def expected_token() -> str:
    return os.environ.get(TOKEN_ENV, "")


def token_matches(candidate: str, expected: str) -> bool:
    return hmac.compare_digest(candidate.encode(), expected.encode())


def _header(scope, name: bytes) -> str:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return ""


def request_token(scope) -> str:
    """Token offered by the caller: Authorization header, or WebSocket subprotocol."""
    if scope["type"] == "websocket":
        for proto in _header(scope, b"sec-websocket-protocol").split(","):
            proto = proto.strip()
            if proto.startswith(WS_TOKEN_PREFIX):
                return proto[len(WS_TOKEN_PREFIX):]
        return ""
    scheme, _, value = _header(scope, b"authorization").partition(" ")
    return value.strip() if scheme.lower() == "bearer" else ""


class TokenMiddleware:
    """Checks the WebSocket origin and, when FITSTATS_API_TOKEN is set, the token."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            # Browsers do not apply CORS to WebSockets, so check the origin here.
            # A missing Origin (non-browser client) is left to the token check.
            origin = _header(scope, b"origin")
            if origin and origin not in ALLOWED_ORIGINS:
                return await self._reject_websocket(receive, send)
        expected = expected_token()
        # Preflight requests carry no credentials by design; CORS answers them.
        is_preflight = scope["type"] == "http" and scope["method"] == "OPTIONS"
        if (scope["type"] not in ("http", "websocket") or not expected
                or is_preflight or scope["path"] in OPEN_PATHS):
            return await self.app(scope, receive, send)
        if token_matches(request_token(scope), expected):
            return await self.app(scope, receive, send)
        if scope["type"] == "websocket":
            return await self._reject_websocket(receive, send)
        response = JSONResponse({"detail": "Unauthorized"}, status_code=401)
        await response(scope, receive, send)

    @staticmethod
    async def _reject_websocket(receive, send):
        await receive()  # websocket.connect
        await send({"type": "websocket.close", "code": 1008})


@asynccontextmanager
async def lifespan(_app):
    if expected_token():
        logger.info("API access token required (per-launch token is set).")
    else:
        logger.info("No API access token configured: requests are not token-protected.")
    job_manager.load()
    yield


app = FastAPI(title="FitStats Config API", lifespan=lifespan)

# Order matters: CORS is added last so it wraps the token check and also
# decorates the 401 responses for the app's own origins.
app.add_middleware(TokenMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ConfigPayload(BaseModel):
    dob: date
    gender: Literal["male", "female"]
    height: int = Field(..., ge=HEIGHT_CM_MIN, le=HEIGHT_CM_MAX)
    weight: float = Field(..., ge=WEIGHT_KG_MIN, le=WEIGHT_KG_MAX)
    data_path: str

    @field_validator("dob")
    @classmethod
    def dob_in_range(cls, value: date) -> date:
        age = age_on(value, date.today())
        if age < AGE_YEARS_MIN or age > AGE_YEARS_MAX:
            raise ValueError(
                f"date of birth must give an age between {AGE_YEARS_MIN} and {AGE_YEARS_MAX} years")
        return value


EXPORT_FOLDER = "Global Export Data"


@app.get("/api/check-path")
async def check_path(path: str):
    """Checks that the path is an export root: it must contain the 'Global Export Data' folder with JSON files."""
    # Resolve relative paths from the current working directory ('server' folder)
    target_path = path
    if not os.path.isabs(path):
        target_path = os.path.abspath(path)
        print(f"Resolving relative path '{path}' to '{target_path}'")

    if not os.path.exists(target_path):
        return {"valid": False, "reason": f"Path '{target_path}' does not exist"}

    if not os.path.isdir(target_path):
        return {"valid": False, "reason": f"Path '{target_path}' is not a folder"}

    export_dir = os.path.join(target_path, EXPORT_FOLDER)
    if not os.path.isdir(export_dir):
        if os.path.basename(os.path.normpath(target_path)) == EXPORT_FOLDER:
            reason = (f"This is the '{EXPORT_FOLDER}' folder itself. "
                      "Select its parent folder instead.")
        else:
            reason = f"Folder '{EXPORT_FOLDER}' not found in '{target_path}'"
        return {"valid": False, "reason": reason}

    if not any(name.endswith(".json") for name in os.listdir(export_dir)):
        return {"valid": False, "reason": f"Folder '{EXPORT_FOLDER}' contains no JSON data files"}

    return {"valid": True, "path": target_path}


class ConnectionManager:
    """The open status WebSockets, and the way to reach them from the run thread."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.loop: asyncio.AbstractEventLoop | None = None
        self._tasks: set = set()

    async def connect(self, websocket: WebSocket, subprotocol: str = None):
        """Accepts the connection and sends it the current snapshot.

        The connection is registered before the snapshot is read: a change that
        happens in between reaches it as a broadcast, and a snapshot that
        arrives out of order is dropped by the client through its `seq`.
        """
        await websocket.accept(subprotocol=subprotocol)
        self.loop = asyncio.get_running_loop()
        self.active_connections.append(websocket)
        await websocket.send_json(job_manager.snapshot().to_dict())

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

    def notify(self, snapshot: JobSnapshot) -> None:
        """Sends a snapshot to every client. Safe to call from any thread."""
        loop = self.loop
        if loop is None or not self.active_connections:
            return

        def send():
            task = loop.create_task(self.broadcast(snapshot.to_dict()))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        try:
            loop.call_soon_threadsafe(send)
        except RuntimeError:
            pass  # the loop is closed: nobody is left to tell


manager = ConnectionManager()


def _run_pipeline(cfg, progress, warnings):
    # Looked up at call time, so a test can replace api.run_pipeline.
    return run_pipeline(cfg, progress, warnings)


def _last_run_path() -> Path:
    return Path(config.CLIENT_PUBLIC_DIR) / LAST_RUN_FILE


job_manager = JobManager(_run_pipeline, _last_run_path, on_change=manager.notify)


def _save_session_config(payload: ConfigPayload) -> None:
    """Saves the form values to session_config.json so the next launch can prefill the form."""
    session_config = {
        "dob": payload.dob.isoformat(),
        "gender": payload.gender,
        "height": payload.height,
        "weight": payload.weight,
        "data_path": payload.data_path
    }
    config_path = os.path.join(config.CLIENT_PUBLIC_DIR, "session_config.json")
    with open(config_path, "w") as f:
        json.dump(session_config, f)


@app.post("/api/start", status_code=202)
async def start_etl(payload: ConfigPayload):
    """Starts an ETL run in the background and answers with the status of the job.

    Answers 409, saving nothing and starting nothing, while another run is in
    progress; the body then carries the status of that run.
    """
    cfg = EtlConfig(
        data_dir=Path(payload.data_path),
        output_dir=Path(config.CLIENT_PUBLIC_DIR),
        profile=Profile(dob=payload.dob, gender=payload.gender,
                        height_cm=payload.height, weight_kg=payload.weight),
    )
    try:
        snapshot = job_manager.start(cfg, prepare=lambda: _save_session_config(payload))
    except JobBusy as busy:
        return JSONResponse(
            {"detail": "An ETL run is already in progress", "job": busy.snapshot.to_dict()},
            status_code=409)
    return snapshot.to_dict()


@app.get("/api/status")
async def get_status():
    """Status of the ETL job: idle, running, finished or error, with progress and warnings."""
    return job_manager.snapshot().to_dict()


@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """Sends the job snapshot on connection and again on every change."""
    offered = websocket.scope.get("subprotocols", [])
    try:
        await manager.connect(websocket, WS_PROTOCOL if WS_PROTOCOL in offered else None)
        while True:
            # Wait passively (keep-alive)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


@app.get("/api/data")
async def get_data():
    """The daily records of the last run, exactly as the pipeline wrote them.

    Answers an empty list, not 404, while there is no data: a 404 from a
    misrouted proxy then stays distinguishable from "nothing calculated yet".
    The pipeline replaces the file atomically, so a reader always gets a whole file.
    """
    no_store = {"Cache-Control": "no-store"}
    path = Path(config.CLIENT_PUBLIC_DIR) / JSON_FILE
    if not path.is_file():
        return JSONResponse([], headers=no_store)
    return FileResponse(path, media_type="application/json", headers=no_store)


@app.get("/api/config")
async def get_config():
    """Retrieves the current user session configuration if it exists."""
    config_path = os.path.join(config.CLIENT_PUBLIC_DIR, "session_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


@app.delete("/api/clear")
async def clear_data():
    """Erases session config, computed dashboard data and the last run status (a factory reset).

    Answers 409 and erases nothing while a run is in progress: it would write
    its files again when it ends.
    """
    client_dir = config.CLIENT_PUBLIC_DIR

    files_to_remove = [
        os.path.join(client_dir, "session_config.json"),
        os.path.join(client_dir, "dashboard_data.json"),
        os.path.join(client_dir, "fitbit_analysis.csv"),
    ]
    cleared = []

    def erase():
        for filepath in files_to_remove:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    cleared.append(filepath)
            except Exception as e:
                print(f"Error removing {filepath}: {e}")

    try:
        job_manager.reset(erase)
    except JobBusy as busy:
        return JSONResponse(
            {"detail": "A calculation is running. Wait for it to finish before deleting data.",
             "job": busy.snapshot.to_dict()},
            status_code=409)
    return {"status": "ok", "cleared": cleared}


@app.post("/api/brief")
async def run_brief(payload: dict = None):
    """Generates a structured daily health briefing."""
    date = payload.get("date") if payload else None
    try:
        brief = get_daily_brief(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if "error" in brief:
        raise HTTPException(status_code=404, detail=brief["error"])
    return brief


@app.get("/api/health")
async def health():
    """Simple health check endpoint to verify API uptime."""
    return {"status": "ok"}

if __name__ == "__main__":
    # Needed so the ETL process pool works in the frozen (PyInstaller) sidecar.
    multiprocessing.freeze_support()
    uvicorn.run(app, host="127.0.0.1", port=8000)
