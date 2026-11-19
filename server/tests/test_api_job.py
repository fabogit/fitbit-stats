"""POST /api/start, GET /api/status, DELETE /api/clear and the status WebSocket."""
import json
import threading

import pytest
from fastapi.testclient import TestClient

import api
import config
import jobs
from modules.pipeline import PipelineResult

WAIT = 10
GLOBAL = "Global Export Data"
BODY = {"dob": "1990-01-01", "gender": "male", "height": 180, "weight": 80, "data_path": "/export"}


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.delenv("FITSTATS_API_TOKEN", raising=False)
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(out):
    # `with` keeps one event loop for the whole test, so the WebSocket and the
    # requests share it, as they do under uvicorn.
    with TestClient(api.app) as c:
        yield c


class Gate:
    """A fake pipeline that stops after a progress step until the test releases it."""

    def __init__(self, error=None, warnings=()):
        self.reached = threading.Event()
        self.release = threading.Event()
        self.configs = []
        self.error = error
        self.found = list(warnings)

    def __call__(self, cfg, progress, warnings):
        self.configs.append(cfg)
        progress(40, "Working")
        warnings.extend(self.found)
        self.reached.set()
        assert self.release.wait(WAIT)
        if self.error:
            raise self.error
        return PipelineResult(df=None, warnings=warnings)


@pytest.fixture
def gate(monkeypatch):
    g = Gate()
    monkeypatch.setattr(api, "run_pipeline", g)
    yield g
    g.release.set()


def wait_for_end():
    assert api.job_manager.join(WAIT)


# --- status ---

def test_status_is_idle_before_any_run(client):
    body = client.get("/api/status").json()
    assert body["state"] == "idle" and body["id"] is None and body["warnings"] == []
    assert set(body) == {"instance", "seq", "id", "state", "progress", "step", "started_at",
                         "finished_at", "message", "warnings"}


def test_status_before_during_and_after_a_run(client, gate):
    started = client.post("/api/start", json=BODY)
    assert started.status_code == 202
    assert gate.reached.wait(WAIT)
    during = client.get("/api/status").json()
    assert (during["state"], during["progress"], during["step"]) == ("running", 40, "Working")
    assert during["id"] == started.json()["id"]
    gate.release.set()
    wait_for_end()
    after = client.get("/api/status").json()
    assert (after["state"], after["progress"], after["id"]) == ("finished", 100, during["id"])
    assert after["seq"] > during["seq"] and after["instance"] == during["instance"]


def test_start_answers_202_with_the_snapshot_and_saves_the_form(client, gate, out):
    r = client.post("/api/start", json=BODY)
    assert r.status_code == 202
    assert r.json()["state"] == "running" and r.json()["progress"] == 0
    assert json.loads((out / "session_config.json").read_text()) == BODY
    assert gate.reached.wait(WAIT)
    cfg = gate.configs[0]
    assert str(cfg.data_dir) == "/export" and str(cfg.output_dir) == str(out)
    assert cfg.profile.weight_kg == 80


def test_second_start_gets_409_with_the_running_snapshot(client, gate, out):
    first = client.post("/api/start", json=BODY)
    assert gate.reached.wait(WAIT)
    second = client.post("/api/start", json=dict(BODY, weight=70, data_path="/other"))
    assert second.status_code == 409
    body = second.json()
    assert body["detail"] == "An ETL run is already in progress"
    assert body["job"]["state"] == "running" and body["job"]["id"] == first.json()["id"]
    assert json.loads((out / "session_config.json").read_text()) == BODY   # the new form is not saved
    gate.release.set()
    wait_for_end()
    assert len(gate.configs) == 1


def test_a_new_run_starts_after_the_last_one_ended(client, gate):
    gate.release.set()
    first = client.post("/api/start", json=BODY).json()
    wait_for_end()
    second = client.post("/api/start", json=BODY)
    assert second.status_code == 202 and second.json()["id"] != first["id"]
    wait_for_end()


def test_invalid_start_does_not_start_a_run(client, gate):
    assert client.post("/api/start", json={"dob": "nope"}).status_code == 422
    assert client.get("/api/status").json()["state"] == "idle"
    assert client.post("/api/start", json=BODY).status_code == 202   # not refused as busy


def test_start_that_cannot_save_the_form_starts_nothing(out, monkeypatch, gate):
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(out / "missing"))
    with TestClient(api.app) as c:
        with pytest.raises(OSError):
            c.post("/api/start", json=BODY)
        assert c.get("/api/status").json()["state"] == "idle"
    assert not gate.configs


def test_unexpected_error_is_a_banner_message_without_paths(client, out, monkeypatch):
    gate = Gate(error=OSError(13, "Permission denied", str(out / "dashboard_data.json.tmp-9")),
                warnings=[{"file": "a.json", "reason": "ValueError: bad"}])
    monkeypatch.setattr(api, "run_pipeline", gate)
    gate.release.set()
    client.post("/api/start", json=BODY)
    wait_for_end()
    body = client.get("/api/status").json()
    assert body["state"] == "error" and body["message"] == "PermissionError: Permission denied"
    assert body["warnings"] == [{"file": "a.json", "reason": "ValueError: bad"}]
    assert str(out) not in json.dumps(body)


def test_warnings_of_a_real_run_are_in_the_status(client, out, tmp_path_factory):
    data = tmp_path_factory.mktemp("export")
    folder = data / GLOBAL
    folder.mkdir()
    rows = [{"dateTime": f"01/{d:02d}/24 12:00:00", "value": "10"} for d in range(1, 4)]
    (folder / "calories-2024-01-01.json").write_text(json.dumps(rows))
    (folder / "steps-2024-01-01.json").write_text("{ this is not json")
    assert client.post("/api/start", json=dict(BODY, data_path=str(data))).status_code == 202
    wait_for_end()
    body = client.get("/api/status").json()
    assert body["state"] == "finished"
    assert [w["file"] for w in body["warnings"]] == ["steps-2024-01-01.json"]
    assert str(data) not in json.dumps(body)
    assert (out / "dashboard_data.json").exists() and not (out / "etl_warnings.json").exists()
    assert json.loads((out / jobs.LAST_RUN_FILE).read_text())["warnings"] == body["warnings"]


def test_run_that_finds_no_data_is_an_error_with_the_warnings(client, out, tmp_path_factory):
    data = tmp_path_factory.mktemp("bad")
    (data / GLOBAL).mkdir()
    (data / GLOBAL / "steps-2024-01-01.json").write_text("{ not json")
    client.post("/api/start", json=dict(BODY, data_path=str(data)))
    wait_for_end()
    body = client.get("/api/status").json()
    assert body["state"] == "error" and body["message"] == "No valid data found."
    assert [w["file"] for w in body["warnings"]] == ["steps-2024-01-01.json"]


def test_etl_warnings_endpoint_is_gone(client):
    assert client.get("/api/etl-warnings").status_code == 404


def test_status_survives_a_restart(out, monkeypatch, gate):
    gate.release.set()
    with TestClient(api.app) as first:
        first.post("/api/start", json=BODY)
        wait_for_end()
        saved = first.get("/api/status").json()
    monkeypatch.setattr(api, "job_manager", jobs.JobManager(api._run_pipeline, api._last_run_path,
                                                            on_change=api.manager.notify))
    with TestClient(api.app) as second:       # lifespan loads last_run.json
        again = second.get("/api/status").json()
    assert (again["id"], again["state"]) == (saved["id"], "finished")
    assert again["instance"] != saved["instance"]


def test_a_run_cut_short_by_a_restart_reads_as_interrupted(out, monkeypatch):
    (out / jobs.LAST_RUN_FILE).write_text(json.dumps({
        "version": 1, "id": "abc", "state": "running", "progress": 40, "step": "Working",
        "started_at": "2024-01-01T10:00:00Z", "finished_at": None, "message": None, "warnings": []}))
    with TestClient(api.app) as c:
        body = c.get("/api/status").json()
    assert body["state"] == "error" and body["message"] == jobs.INTERRUPTED_MESSAGE


# --- reset ---

def test_clear_during_a_run_is_refused_and_erases_nothing(client, gate, out):
    (out / "dashboard_data.json").write_text("[]")
    (out / "fitbit_analysis.csv").write_text("x")
    client.post("/api/start", json=BODY)
    assert gate.reached.wait(WAIT)
    r = client.delete("/api/clear")
    assert r.status_code == 409 and r.json()["job"]["state"] == "running"
    for name in ("dashboard_data.json", "fitbit_analysis.csv", "session_config.json", jobs.LAST_RUN_FILE):
        assert (out / name).exists(), name
    gate.release.set()
    wait_for_end()


def test_clear_erases_the_data_the_session_and_the_last_run(client, gate, out):
    gate.release.set()
    client.post("/api/start", json=BODY)
    wait_for_end()
    (out / "dashboard_data.json").write_text("[]")
    (out / "fitbit_analysis.csv").write_text("x")
    assert (out / jobs.LAST_RUN_FILE).exists()
    r = client.delete("/api/clear")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert [p.name for p in out.iterdir()] == []
    body = client.get("/api/status").json()
    assert body["state"] == "idle" and body["id"] is None and body["warnings"] == []


# --- the status WebSocket ---

def read_snapshots(ws, until_state):
    seen = []
    while True:
        snap = ws.receive_json()
        seen.append(snap)
        if snap["state"] == until_state:
            return seen


def test_websocket_sends_the_snapshot_on_connection(client):
    with client.websocket_connect("/ws/status") as ws:
        first = ws.receive_json()
    assert first == client.get("/api/status").json()


def test_websocket_sends_a_snapshot_on_every_change(client, gate):
    with client.websocket_connect("/ws/status") as ws:
        initial = ws.receive_json()
        assert initial["state"] == "idle"
        client.post("/api/start", json=BODY)
        assert gate.reached.wait(WAIT)
        gate.release.set()
        seen = read_snapshots(ws, "finished")
    assert [s["state"] for s in seen][0] == "running"
    seqs = [s["seq"] for s in seen]
    assert seqs == sorted(set(seqs)) and seqs[0] > initial["seq"]
    assert {s["instance"] for s in seen} == {initial["instance"]}
    assert any(s["progress"] == 40 and s["step"] == "Working" for s in seen)
    assert seen[-1]["progress"] == 100 and seen[-1]["id"] == seen[0]["id"]


def test_websocket_connected_late_gets_the_current_run(client, gate):
    client.post("/api/start", json=BODY)
    assert gate.reached.wait(WAIT)
    with client.websocket_connect("/ws/status") as ws:
        first = ws.receive_json()
        assert (first["state"], first["progress"], first["step"]) == ("running", 40, "Working")
        gate.release.set()
        assert read_snapshots(ws, "finished")[-1]["seq"] > first["seq"]


def test_every_connection_gets_the_changes(client, gate):
    with client.websocket_connect("/ws/status") as a, client.websocket_connect("/ws/status") as b:
        a.receive_json(), b.receive_json()
        client.post("/api/start", json=BODY)
        gate.release.set()
        assert read_snapshots(a, "finished")[-1]["id"] == read_snapshots(b, "finished")[-1]["id"]


def test_websocket_sees_the_reset(client, gate):
    gate.release.set()
    client.post("/api/start", json=BODY)
    wait_for_end()
    with client.websocket_connect("/ws/status") as ws:
        assert ws.receive_json()["state"] == "finished"
        client.delete("/api/clear")
        assert read_snapshots(ws, "idle")[-1]["id"] is None
