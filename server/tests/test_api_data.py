"""GET /api/data: the daily records of the last run, served as the pipeline wrote them."""
import json
import os
import threading

import pytest
from fastapi.testclient import TestClient

import api
import config
from modules.etl import JSON_FILE

TOKEN = "t" * 64


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.delenv("FITSTATS_API_TOKEN", raising=False)
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(out):
    with TestClient(api.app) as c:
        yield c


def records(days, width=0):
    return [{"date": f"2024-01-{d:02d}", "steps": 1000 + d, "note": "x" * width}
            for d in range(1, days + 1)]


def test_without_data_the_answer_is_an_empty_list(client, out):
    r = client.get("/api/data")
    assert r.status_code == 200
    assert r.json() == []
    assert r.headers["content-type"].startswith("application/json")
    assert r.headers["cache-control"] == "no-store"


def test_with_data_the_body_is_the_file_byte_for_byte(client, out):
    # Not what json.dumps would write: spacing and key order must survive untouched.
    raw = '[{"date":"2024-01-01","steps":1234,"weight":null},\n {"steps": 5, "date": "2024-01-02"}]'.encode()
    (out / JSON_FILE).write_bytes(raw)
    r = client.get("/api/data")
    assert r.status_code == 200
    assert r.content == raw
    assert r.headers["content-type"].startswith("application/json")
    assert r.headers["cache-control"] == "no-store"


def test_a_corrupt_file_is_served_as_it_is(client, out):
    (out / JSON_FILE).write_bytes(b'[{"date": "2024-01-01", "ste')
    r = client.get("/api/data")
    assert r.status_code == 200
    assert r.content == b'[{"date": "2024-01-01", "ste'


def test_the_data_follows_the_file_after_a_reset(client, out):
    (out / JSON_FILE).write_text(json.dumps(records(3)))
    assert len(client.get("/api/data").json()) == 3
    assert client.delete("/api/clear").status_code == 200
    assert client.get("/api/data").json() == []


def test_it_reads_the_folder_at_call_time(client, tmp_path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    (other / JSON_FILE).write_text(json.dumps(records(2)))
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(other))
    assert len(client.get("/api/data").json()) == 2


def test_the_answer_is_always_valid_json_while_the_file_is_replaced(client, out):
    """The pipeline replaces the file atomically: a read sees one version or the other, never a mix."""
    versions = [json.dumps(records(5, width=10)), json.dumps(records(400, width=2000))]
    final = out / JSON_FILE
    final.write_text(versions[0])
    sizes = {len(versions[0]), len(versions[1])}
    stop = threading.Event()
    errors = []

    def rewrite():
        n = 0
        tmp = out / f"{JSON_FILE}.tmp-test"
        try:
            while not stop.is_set():
                tmp.write_text(versions[n % 2])
                os.replace(tmp, final)
                n += 1
        except Exception as e:  # report it from the test thread
            errors.append(e)

    writer = threading.Thread(target=rewrite)
    writer.start()
    try:
        for _ in range(200):
            r = client.get("/api/data")
            assert r.status_code == 200
            assert len(r.text) in sizes
            assert isinstance(json.loads(r.text), list)
    finally:
        stop.set()
        writer.join(10)
    assert not errors
