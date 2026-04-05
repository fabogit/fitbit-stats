import subprocess
import os
import sys
import json
from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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


from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from typing import List

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


async def run_etl_subprocess(cmd):
    """Esegue l'ETL in background senza bloccare il server e notifica via WebSocket."""
    await manager.broadcast({"event": "etl_started", "status": "running"})
    try:
        # Run subprocess asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            await manager.broadcast({"event": "etl_finished", "status": "success", "message": "ETL completed successfully"})
        else:
            err_msg = stderr.decode() if stderr else "Unknown error"
            print(f"ETL Error: {err_msg}")
            await manager.broadcast({"event": "etl_finished", "status": "error", "message": err_msg})
            
    except Exception as e:
        await manager.broadcast({"event": "etl_finished", "status": "error", "message": str(e)})


@app.post("/api/start")
async def start_etl(payload: ConfigPayload, background_tasks: BackgroundTasks):
    """Saves biometric configurations and initiates the main ETL pipeline asynchronously via BackgroundTasks."""
    # Save to session_config.json to persist across runs and for watcher
    session_config = {
        "dob": payload.dob,
        "gender": payload.gender,
        "height": payload.height,
        "weight": payload.weight,
        "data_path": payload.data_path
    }
    with open("session_config.json", "w") as f:
        json.dump(session_config, f)

    # Run ETL via CLI
    cmd = [
        sys.executable,
        "main.py",
        "--dob", payload.dob,
        "--gender", payload.gender,
        "--height", str(payload.height),
        "--weight", str(payload.weight),
        "--data-dir", payload.data_path
    ]

    background_tasks.add_task(run_etl_subprocess, cmd)
    return {"status": "accepted", "message": "ETL process started in background"}


@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """Canale persistente per notificare il Client dello stato dell'ETL."""
    await manager.connect(websocket)
    try:
        while True:
            # Attendiamo passivamente (keep-alive)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/config")
async def get_config():
    """Retrieves the current user session configuration if it exists."""
    if os.path.exists("session_config.json"):
        with open("session_config.json", "r") as f:
            return json.load(f)
    return {}

@app.delete("/api/clear")
async def clear_data():
    """Erases session config and computed dashboard data to simulate a factory reset."""
    files_to_remove = ["session_config.json"]
    
    # Try to remove dashboard_data.json from CLIENT_PUBLIC_DIR if available
    client_dir = os.environ.get("CLIENT_PUBLIC_DIR")
    if client_dir:
        files_to_remove.append(os.path.join(client_dir, "dashboard_data.json"))
    else:
        files_to_remove.append("dashboard_data.json")

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
    """Executes the daily briefing script to generate a textual health summary."""
    # payload can contain {"date": "YYYY-MM-DD"}
    cmd = [sys.executable, "daily_brief.py"]
    if payload and payload.get("date"):
        cmd.extend(["--date", payload["date"]])

    try:
        # For brief, we want the output back
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False)
        return {"status": "done", "output": result.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    """Simple health check endpoint to verify API uptime."""
    return {"status": "ok"}
