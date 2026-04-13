import os
import json
import asyncio
from typing import List

import uvicorn
import websockets
from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from modules.briefing import get_daily_brief

# Change working directory so relative paths in config.py work correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="FitStats Config API")

# Allow CORS for local development (React runs on 8080/5173, etc)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConfigPayload(BaseModel):
    dob: str
    gender: str
    height: int = Field(..., gt=40, lt=260)
    weight: float = Field(..., gt=20, lt=300)
    data_path: str


@app.get("/api/check-path")
async def check_path(path: str):
    """Checks if the data path exists and contains heart rate data."""
    # Resolve relative paths from the current working directory ('server' folder)
    target_path = path
    if not os.path.isabs(path):
        target_path = os.path.abspath(path)
        print(f"Resolving relative path '{path}' to '{target_path}'")

    if not os.path.exists(target_path):
        return {"valid": False, "reason": f"Path '{target_path}' does not exist"}

    return {"valid": True, "path": target_path}


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


def run_etl_sync(payload, loop):
    """Runs the synchronous ETL by sending updates to the queue."""
    import config
    from modules import etl, metrics

    config.DATA_DIR = payload.data_path
    config.USER_DOB = payload.dob
    config.USER_HEIGHT_CM = payload.height
    config.USER_WEIGHT_KG = payload.weight
    config.USER_GENDER = payload.gender

    def progress(pct, msg):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(
                {"event": "etl_progress", "step": msg, "progress": pct}),
            loop
        )

    try:
        progress(10, "Loading and merging data files")
        df = etl.merge_all_data(progress_callback=progress)

        if df is not None:
            progress(70, "Calculating readiness metrics")
            df = metrics.calculate_readiness(df)

            progress(75, "Calculating metabolic metrics")
            df = metrics.calculate_metabolic_metrics(df)

            progress(80, "Calculating advanced metrics")
            df = metrics.calculate_advanced_metrics(df)

            progress(90, "Exporting analysis CSV")
            # Required for BRIEFING module
            df.to_csv(os.path.join(
                config.CLIENT_PUBLIC_DIR, "fitbit_analysis.csv"))

            progress(95, "Exporting dashboard JSON")
            etl.export_to_json(df)

            progress(100, "Complete")
            asyncio.run_coroutine_threadsafe(
                manager.broadcast(
                    {"event": "etl_finished", "status": "success", "message": "ETL completed successfully"}),
                loop
            )
        else:
            asyncio.run_coroutine_threadsafe(
                manager.broadcast(
                    {"event": "etl_finished", "status": "error", "message": "No valid data found."}),
                loop
            )
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(
                {"event": "etl_finished", "status": "error", "message": str(e)}),
            loop
        )


async def run_etl_task(payload):
    """Starts the synchronous execution of the ETL in a separate thread."""
    await manager.broadcast({"event": "etl_progress", "step": "Starting ETL engine...", "progress": 0})
    loop = asyncio.get_running_loop()
    await asyncio.to_thread(run_etl_sync, payload, loop)


@app.post("/api/start")
async def start_etl(payload: ConfigPayload, background_tasks: BackgroundTasks):
    """Saves biometric configurations and initiates the main ETL pipeline asynchronously via BackgroundTasks."""
    import config
    # Save to session_config.json to persist across runs and for watcher
    session_config = {
        "dob": payload.dob,
        "gender": payload.gender,
        "height": payload.height,
        "weight": payload.weight,
        "data_path": payload.data_path
    }
    config_path = os.path.join(config.CLIENT_PUBLIC_DIR, "session_config.json")
    with open(config_path, "w") as f:
        json.dump(session_config, f)

    # Run ETL logic internally without subprocesses
    background_tasks.add_task(run_etl_task, payload)
    return {"status": "accepted", "message": "ETL process started in background"}


@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """Persistent channel to notify the client of the ETL status."""
    await manager.connect(websocket)
    try:
        while True:
            # Wait passively (keep-alive)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/config")
async def get_config():
    """Retrieves the current user session configuration if it exists."""
    import config
    config_path = os.path.join(config.CLIENT_PUBLIC_DIR, "session_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


@app.delete("/api/clear")
async def clear_data():
    """Erases session config and computed dashboard data to simulate a factory reset."""
    import config
    client_dir = config.CLIENT_PUBLIC_DIR

    files_to_remove = [
        os.path.join(client_dir, "session_config.json"),
        os.path.join(client_dir, "dashboard_data.json"),
        os.path.join(client_dir, "fitbit_analysis.csv")
    ]

    cleared = []
    for filepath in files_to_remove:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                cleared.append(filepath)
        except Exception as e:
            print(f"Error removing {filepath}: {e}")

    return {"status": "ok", "cleared": cleared}


@app.post("/api/brief")
async def run_brief(payload: dict = None):
    """Generates a structured daily health briefing."""
    date = payload.get("date") if payload else None
    try:
        brief = get_daily_brief(date)
        if "error" in brief:
            raise HTTPException(status_code=404, detail=brief["error"])
        return brief
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    """Simple health check endpoint to verify API uptime."""
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
