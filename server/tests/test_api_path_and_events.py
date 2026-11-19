import json
import threading

import pytest
from fastapi.testclient import TestClient

import api
import config

GLOBAL = "Global Export Data"


@pytest.fixture
def client():
    return TestClient(api.app)


def check(client, path):
    return client.get("/api/check-path", params={"path": str(path)}).json()


def test_accepts_export_root(client, tmp_path):
    folder = tmp_path / GLOBAL
    folder.mkdir()
    (folder / "steps-2024-01-01.json").write_text("[]")
    assert check(client, tmp_path)["valid"] is True


def test_rejects_missing_path(client, tmp_path):
    result = check(client, tmp_path / "nope")
    assert result["valid"] is False and "does not exist" in result["reason"]


def test_rejects_folder_without_export_folder(client, tmp_path):
    result = check(client, tmp_path)
    assert result["valid"] is False and GLOBAL in result["reason"]


def test_rejects_export_folder_itself_with_hint(client, tmp_path):
    folder = tmp_path / GLOBAL
    folder.mkdir()
    (folder / "heart_rate-2024-01-01.json").write_text("[]")
    result = check(client, folder)
    assert result["valid"] is False and "parent" in result["reason"]


def test_rejects_empty_export_folder(client, tmp_path):
    (tmp_path / GLOBAL).mkdir()
    result = check(client, tmp_path)
    assert result["valid"] is False and "no JSON" in result["reason"]


def test_rejects_file_path(client, tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    result = check(client, f)
    assert result["valid"] is False and "not a folder" in result["reason"]


def test_event_reaches_client_connected_before_start(client, tmp_path, monkeypatch):
    """A socket opened before POST /api/start receives an instantly finished run."""
    import asyncio
    import config

    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path))

    def fast_etl(payload, loop):
        asyncio.run_coroutine_threadsafe(
            api.manager.broadcast({"event": "etl_finished", "status": "success", "message": "ok"}),
            loop,
        ).result()

    monkeypatch.setattr(api, "run_etl_sync", fast_etl)
    body = {"dob": "1990-01-01", "gender": "male", "height": 180, "weight": 80,
            "data_path": str(tmp_path)}
    with client.websocket_connect("/ws/status") as ws:
        assert client.post("/api/start", json=body).status_code == 200
        events = [ws.receive_json(), ws.receive_json()]
    assert events[0]["event"] == "etl_progress"
    assert events[-1]["event"] == "etl_finished"


# --- a second start while a run is in progress ---

def test_start_rejected_while_running(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path))
    started, release, calls = threading.Event(), threading.Event(), []

    def slow_etl(payload, loop):
        calls.append(payload.weight)
        started.set()
        release.wait(timeout=10)

    monkeypatch.setattr(api, "run_etl_sync", slow_etl)
    first = {"dob": "1990-01-01", "gender": "male", "height": 180, "weight": 80,
             "data_path": str(tmp_path)}
    # TestClient answers only once the background task is over, so the first
    # start runs in its own thread while the second is sent from this one.
    answers = []
    first_start = threading.Thread(
        target=lambda: answers.append(TestClient(api.app).post("/api/start", json=first)))
    first_start.start()
    try:
        assert started.wait(timeout=10)
        second = client.post("/api/start", json=dict(first, weight=70, data_path="/other"))
        assert second.status_code == 409
        assert second.json() == {"detail": "An ETL run is already in progress"}
    finally:
        release.set()
        first_start.join(timeout=10)
    assert [a.status_code for a in answers] == [200]
    assert calls == [80]
    assert json.loads((tmp_path / "session_config.json").read_text()) == first


def test_lock_is_released_when_the_run_ends(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path))
    body = {"dob": "1990-01-01", "gender": "male", "height": 180, "weight": 80,
            "data_path": str(tmp_path)}
    outcomes = iter([None, RuntimeError("boom"), None])

    def etl(payload, loop):
        outcome = next(outcomes)
        if outcome:
            raise outcome

    monkeypatch.setattr(api, "run_etl_sync", etl)
    # TestClient finishes the background task before it returns the response.
    lenient = TestClient(api.app, raise_server_exceptions=False)
    assert [lenient.post("/api/start", json=body).status_code for _ in range(3)] == [200] * 3
    assert not api.etl_run_lock.locked()


def test_invalid_start_does_not_take_the_lock(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path))
    assert client.post("/api/start", json={"dob": "nope"}).status_code == 422
    assert not api.etl_run_lock.locked()


def test_lock_is_released_when_the_config_cannot_be_saved(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path / "missing"))
    body = {"dob": "1990-01-01", "gender": "male", "height": 180, "weight": 80, "data_path": "x"}
    with pytest.raises(OSError):
        client.post("/api/start", json=body)
    assert not api.etl_run_lock.locked()
