from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import subprocess
import os
import sys
import glob

# Change working directory so relative paths in config.py work correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import json
from fastapi import FastAPI, HTTPException

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


@app.post("/api/start")
async def start_etl(payload: ConfigPayload):
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
    
    try:
        # Run ETL and wait for it to complete so the client can fetch the result immediately
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"status": "success", "message": "ETL process completed successfully"}
    except subprocess.CalledProcessError as e:
        print(f"ETL Error: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"ETL failed: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config():
    if os.path.exists("session_config.json"):
        with open("session_config.json", "r") as f:
            return json.load(f)
    return {}

@app.post("/api/brief")
async def run_brief(payload: dict = None):
    # payload can contain {"date": "YYYY-MM-DD"}
    cmd = [sys.executable, "daily_brief.py"]
    if payload and payload.get("date"):
        cmd.extend(["--date", payload["date"]])
    
    try:
        # For brief, we want the output back
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return {"status": "done", "output": result.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {"status": "ok"}
