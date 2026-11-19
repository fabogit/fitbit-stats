
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import api

TOKEN = "t" * 64
APP_ORIGIN = "tauri://localhost"
OTHER_ORIGIN = "https://other.example"


@pytest.fixture
def client():
    return TestClient(api.app)


@pytest.fixture
def with_token(monkeypatch):
    monkeypatch.setenv("FITSTATS_API_TOKEN", TOKEN)


@pytest.fixture
def no_token(monkeypatch):
    monkeypatch.delenv("FITSTATS_API_TOKEN", raising=False)


def auth(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


def test_request_without_token_is_rejected(client, with_token):
    assert client.get("/api/config").status_code in (401, 403)
    assert client.post("/api/brief", json={}).status_code in (401, 403)
    assert client.delete("/api/clear").status_code in (401, 403)
    assert client.get("/api/status").status_code in (401, 403)
    assert client.post("/api/start", json={}).status_code in (401, 403)


def test_request_with_wrong_token_is_rejected(client, with_token):
    assert client.get("/api/config", headers=auth("x" * 64)).status_code in (401, 403)
    assert client.get("/api/config", headers={"Authorization": TOKEN}).status_code in (401, 403)


def test_request_with_token_is_accepted(client, with_token):
    assert client.get("/api/config", headers=auth()).status_code == 200


def test_status_needs_the_token(client, with_token):
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/status", headers=auth("x" * 64)).status_code == 401
    r = client.get("/api/status", headers=auth())
    assert r.status_code == 200 and r.json()["state"] == "idle"


def test_status_works_without_token_when_variable_unset(client, no_token):
    assert client.get("/api/status").status_code == 200


def test_status_from_unlisted_origin_gets_no_cors_permission(client, no_token):
    r = client.get("/api/status", headers={"Origin": OTHER_ORIGIN})
    assert "access-control-allow-origin" not in r.headers


def test_status_is_readable_by_an_app_origin(client, no_token):
    r = client.get("/api/status", headers={"Origin": APP_ORIGIN})
    assert r.headers["access-control-allow-origin"] == APP_ORIGIN


def test_health_is_open_and_minimal(client, with_token):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_no_token_required_when_variable_unset(client, no_token):
    assert client.get("/api/config").status_code == 200


def test_empty_token_variable_means_not_required(client, monkeypatch):
    monkeypatch.setenv("FITSTATS_API_TOKEN", "")
    assert client.get("/api/config").status_code == 200


def test_unlisted_origin_gets_no_cors_permission(client, no_token):
    r = client.get("/api/config", headers={"Origin": OTHER_ORIGIN})
    assert "access-control-allow-origin" not in r.headers
    pre = client.options(
        "/api/clear",
        headers={"Origin": OTHER_ORIGIN, "Access-Control-Request-Method": "DELETE"},
    )
    assert "access-control-allow-origin" not in pre.headers
    assert pre.status_code != 200


@pytest.mark.parametrize("origin", [
    "tauri://localhost", "http://tauri.localhost", "http://localhost:5173"])
def test_app_origins_are_allowed(client, no_token, origin):
    pre = client.options(
        "/api/start",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "authorization,content-type"},
    )
    assert pre.status_code == 200
    assert pre.headers["access-control-allow-origin"] == origin
    r = client.get("/api/config", headers={"Origin": origin})
    assert r.headers["access-control-allow-origin"] == origin


def test_preflight_does_not_need_token(client, with_token):
    pre = client.options(
        "/api/config",
        headers={"Origin": APP_ORIGIN, "Access-Control-Request-Method": "GET",
                 "Access-Control-Request-Headers": "authorization"},
    )
    assert pre.status_code == 200


def test_rejection_is_readable_by_app_origin(client, with_token):
    r = client.get("/api/config", headers={"Origin": APP_ORIGIN})
    assert r.status_code in (401, 403)
    assert r.headers["access-control-allow-origin"] == APP_ORIGIN


def test_no_wildcard_origin(client, no_token):
    r = client.get("/api/config", headers={"Origin": APP_ORIGIN})
    assert r.headers["access-control-allow-origin"] != "*"


def test_origins_from_environment():
    origins = api.build_allowed_origins(" http://localhost:8080, http://127.0.0.1:8080 ,")
    assert "http://localhost:8080" in origins and "http://127.0.0.1:8080" in origins
    assert "tauri://localhost" in origins
    assert "*" not in origins
    assert "*" not in api.build_allowed_origins("*, http://a.example")


def test_websocket_without_token_is_rejected(client, with_token):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/status"):
            pass


def test_websocket_with_wrong_token_is_rejected(client, with_token):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
                "/ws/status", subprotocols=["fitstats", "token." + "x" * 64]):
            pass


def test_websocket_with_token_is_accepted(client, with_token):
    with client.websocket_connect(
            "/ws/status", subprotocols=["fitstats", "token." + TOKEN]) as ws:
        assert ws.accepted_subprotocol == "fitstats"
        assert ws.receive_json()["state"] == "idle"
        ws.send_text("ping")


def test_websocket_without_token_works_when_variable_unset(client, no_token):
    with client.websocket_connect("/ws/status") as ws:
        ws.send_text("ping")


def ws_connect(client, origin=None, subprotocols=None):
    headers = {"Origin": origin} if origin else {}
    return client.websocket_connect("/ws/status", headers=headers, subprotocols=subprotocols)


def test_websocket_from_unlisted_origin_is_rejected_without_token(client, no_token):
    with pytest.raises(WebSocketDisconnect):
        with ws_connect(client, OTHER_ORIGIN):
            pass


def test_websocket_from_unlisted_origin_is_rejected_with_token(client, with_token):
    with pytest.raises(WebSocketDisconnect):
        with ws_connect(client, OTHER_ORIGIN, ["fitstats", "token." + TOKEN]):
            pass


def test_websocket_from_allowed_origin_is_accepted(client, no_token):
    with ws_connect(client, APP_ORIGIN) as ws:
        ws.send_text("ping")


def test_websocket_from_allowed_origin_with_token_is_accepted(client, with_token):
    with ws_connect(client, APP_ORIGIN, ["fitstats", "token." + TOKEN]) as ws:
        ws.send_text("ping")


def test_websocket_without_origin_is_accepted_when_token_not_required(client, no_token):
    with ws_connect(client) as ws:
        ws.send_text("ping")
