"""How the server process starts: the port it picks and how it tells the desktop shell."""
import json
import os
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

import api

SERVER_DIR = Path(api.__file__).resolve().parent


def start_server(extra_env=None):
    env = {k: v for k, v in os.environ.items() if k not in (api.PORT_ENV, api.TOKEN_ENV)}
    env.update(extra_env or {})
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.Popen([sys.executable, str(SERVER_DIR / "api.py")], env=env, cwd=SERVER_DIR,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    proc.stdout.close()


def read_ready(proc):
    """The parsed FITSTATS_READY line; fails if the process ends without printing one."""
    for line in proc.stdout:
        if line.startswith(api.READY_PREFIX + " "):
            return json.loads(line[len(api.READY_PREFIX) + 1:])
    pytest.fail(f"no {api.READY_PREFIX} line (exit code {proc.wait(10)})")


@pytest.fixture
def occupied_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        yield s.getsockname()[1]


class TestListenPort:
    def test_default_is_8000(self):
        assert api.listen_port({}) == 8000
        assert api.listen_port({api.PORT_ENV: ""}) == 8000

    def test_port_from_environment(self):
        assert api.listen_port({api.PORT_ENV: "8123"}) == 8123
        assert api.listen_port({api.PORT_ENV: "0"}) == 0

    @pytest.mark.parametrize("value", ["abc", "-1", "65536", "80.5"])
    def test_invalid_port_stops_the_start(self, value):
        with pytest.raises(SystemExit) as stop:
            api.listen_port({api.PORT_ENV: value})
        assert api.PORT_ENV in str(stop.value)


class TestMain:
    @pytest.fixture
    def fake_server(self, monkeypatch):
        """Replaces the uvicorn server: records the socket it was given instead of serving."""
        seen = {}

        class FakeServer:
            def __init__(self, config):
                seen["config"] = config

            def run(self, sockets):
                seen["port"] = sockets[0].getsockname()[1]
                seen["listening"] = sockets[0].getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN)

        monkeypatch.setattr(api, "_Server", FakeServer)
        return seen

    def test_default_port_is_bound_when_nothing_is_set(self, monkeypatch, fake_server):
        bound = []
        monkeypatch.setattr(api, "bind_socket", lambda port: bound.append(port) or socket.socket())
        api.main({})
        assert bound == [8000]

    def test_port_zero_gives_a_free_port_that_the_server_receives_unopened(self, fake_server):
        api.main({api.PORT_ENV: "0"})
        assert fake_server["port"] > 0
        assert fake_server["listening"] == 0  # uvicorn is the one that starts listening


class TestPortInUse:
    def test_bind_socket_exits_with_code_3(self, occupied_port, capsys):
        with pytest.raises(SystemExit) as stop:
            api.bind_socket(occupied_port)
        assert stop.value.code == api.EXIT_PORT_IN_USE == 3
        assert str(occupied_port) in capsys.readouterr().err

    def test_the_process_exits_with_code_3(self, occupied_port):
        proc = start_server({api.PORT_ENV: str(occupied_port)})
        try:
            assert proc.wait(60) == 3
            assert api.READY_PREFIX not in proc.stdout.read()
        finally:
            stop_server(proc)


class TestHandshake:
    def test_ready_line_gives_the_port_the_server_answers_on(self):
        proc = start_server({api.PORT_ENV: "0"})
        try:
            ready = read_ready(proc)
            assert set(ready) == {"port", "pid"}
            assert ready["pid"] == proc.pid
            # The line is printed after the listen: the first request already gets through.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f"http://127.0.0.1:{ready['port']}/api/health", timeout=5) as resp:
                assert resp.status == 200
                assert json.load(resp) == {"status": "ok"}
        finally:
            stop_server(proc)

    def test_ready_line_is_compact_json_on_its_own_line(self):
        proc = start_server({api.PORT_ENV: "0"})
        try:
            for line in proc.stdout:
                if line.startswith(api.READY_PREFIX):
                    assert line.endswith('}\n')
                    assert line.startswith(api.READY_PREFIX + ' {"port":')
                    assert " " not in line.split(" ", 1)[1].strip()
                    break
            else:
                pytest.fail("no ready line")
        finally:
            stop_server(proc)
