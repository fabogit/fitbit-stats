
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
    assert client.get("/api/data").status_code in (401, 403)
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


def test_data_needs_the_token(client, with_token):
    assert client.get("/api/data").status_code == 401
    assert client.get("/api/data", headers=auth("x" * 64)).status_code == 401
    assert client.get("/api/data", headers={"Authorization": TOKEN}).status_code == 401
    r = client.get("/api/data", headers=auth())
    assert r.status_code == 200 and isinstance(r.json(), list)


def test_data_works_without_token_when_variable_unset(client, no_token):
    assert client.get("/api/data").status_code == 200


def test_data_from_unlisted_origin_gets_no_cors_permission(client, no_token):
    r = client.get("/api/data", headers={"Origin": OTHER_ORIGIN})
    assert "access-control-allow-origin" not in r.headers


def test_data_is_readable_by_an_app_origin(client, no_token):
    r = client.get("/api/data", headers={"Origin": APP_ORIGIN})
    assert r.headers["access-control-allow-origin"] == APP_ORIGIN


def test_data_rejection_is_readable_by_app_origin(client, with_token):
    r = client.get("/api/data", headers={"Origin": APP_ORIGIN})
    assert r.status_code == 401
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


# --- WebSocket origin equal to the host the request was sent to (web UI behind its proxy) ---

HOST = "files.example:8080"
SAME_ORIGIN = "http://files.example:8080"


@pytest.mark.parametrize("origin, host", [
    (SAME_ORIGIN, HOST),
    ("https://files.example:8080", HOST),             # the scheme does not matter
    ("http://FILES.Example:8080", HOST),              # host names are case-insensitive
    ("http://files.example:8080", "FILES.EXAMPLE:8080"),
    ("http://files.example", "files.example:80"),     # default port, implicit against explicit
    ("http://files.example:80", "files.example"),
    ("https://files.example", "files.example:443"),
    ("https://files.example:443", "files.example"),
    ("ws://files.example", "files.example:80"),
    ("wss://files.example", "files.example:443"),
    ("http://192.0.2.7:8080", "192.0.2.7:8080"),
    ("http://[::1]:8080", "[::1]:8080"),
    ("http://[::1]", "[::1]"),
    ("http://[0:0:0:0:0:0:0:1]:8080", "[::1]:8080"),  # IPv6 spellings
    ("http://[2001:DB8::1]:8080", "[2001:db8::1]:8080"),
])
def test_origin_matches_host(origin, host):
    assert api.origin_matches_host(origin, host)


@pytest.mark.parametrize("origin, host", [
    ("http://files.example:9090", HOST),              # other port
    ("http://files.example", HOST),                   # implicit port 80 is not 8080
    ("http://files.example:8080", "files.example"),   # 8080 is not the default
    ("https://files.example", "files.example:80"),    # https implies 443
    ("http://other.example:8080", HOST),              # other host
    ("http://files.example.evil:8080", HOST),
    ("http://evil.example/files.example:8080", HOST),
    ("http://files.example:8080@evil.example", HOST),
    ("http://files.example:8080/", HOST),             # not an origin: it has a path
    ("http://[::2]:8080", "[::1]:8080"),
    ("null", "null"),                                 # opaque origin
    ("null", HOST),
    ("", HOST),
    ("files.example:8080", HOST),                     # no scheme
    ("tauri://localhost", "localhost"),               # not a web scheme
    ("http://", ""),                                  # no host at all
    ("http://:8080", ":8080"),
    ("http://files.example:notaport", "files.example:notaport"),
    ("http://files.example:8080", ""),                # Host missing
    ("http://files.example:8080", "files.example:8080/x"),
    ("http://files.example:8080", "user@files.example:8080"),
    ("http://files.example:8080", "files.example:99999"),
])
def test_origin_does_not_match_host(origin, host):
    assert not api.origin_matches_host(origin, host)


def ws_from(client, origin, host, token=None):
    headers = {"Origin": origin, "Host": host}
    protos = ["fitstats", "token." + token] if token else None
    return client.websocket_connect("/ws/status", headers=headers, subprotocols=protos)


def test_websocket_from_same_host_and_port_is_accepted(client, no_token):
    with ws_from(client, SAME_ORIGIN, HOST) as ws:
        assert ws.receive_json()["state"] == "idle"
        ws.send_text("ping")


def test_websocket_from_other_port_is_rejected(client, no_token):
    with pytest.raises(WebSocketDisconnect):
        with ws_from(client, "http://files.example:9090", HOST):
            pass


def test_websocket_from_other_host_is_rejected(client, no_token):
    with pytest.raises(WebSocketDisconnect):
        with ws_from(client, "http://other.example:8080", HOST):
            pass


def test_websocket_from_null_origin_is_rejected(client, no_token):
    with pytest.raises(WebSocketDisconnect):
        with ws_from(client, "null", HOST):
            pass


def test_websocket_from_listed_origin_is_accepted_whatever_the_host(client, no_token):
    with ws_from(client, APP_ORIGIN, HOST) as ws:
        ws.send_text("ping")


def test_websocket_same_host_without_token_is_rejected_when_token_required(client, with_token):
    with pytest.raises(WebSocketDisconnect):
        with ws_from(client, SAME_ORIGIN, HOST):
            pass


def test_websocket_same_host_with_token_is_accepted(client, with_token):
    with ws_from(client, SAME_ORIGIN, HOST, TOKEN) as ws:
        ws.send_text("ping")


def test_websocket_same_host_with_wrong_token_is_rejected(client, with_token):
    with pytest.raises(WebSocketDisconnect):
        with ws_from(client, SAME_ORIGIN, HOST, "x" * 64):
            pass


def test_websocket_desktop_origin_with_token_is_unchanged(client, with_token):
    with ws_from(client, APP_ORIGIN, "127.0.0.1:8000", TOKEN) as ws:
        ws.send_text("ping")
    with pytest.raises(WebSocketDisconnect):
        with ws_from(client, APP_ORIGIN, "127.0.0.1:8000"):
            pass


def test_websocket_without_host_header_is_rejected_unless_origin_is_listed(no_token):
    """The Host header is missing: only an origin from the list passes."""
    import asyncio

    async def run(origin):
        messages = []
        sent = []

        async def inner(scope, receive, send):
            sent.append("app")

        async def receive():
            messages.append("receive")
            return {"type": "websocket.connect"}

        async def send(message):
            sent.append(message["type"])

        scope = {"type": "websocket", "path": "/ws/status",
                 "headers": [(b"origin", origin.encode())]}
        await api.TokenMiddleware(inner)(scope, receive, send)
        return sent

    assert asyncio.run(run(SAME_ORIGIN)) == ["websocket.close"]
    assert asyncio.run(run(APP_ORIGIN)) == ["app"]
