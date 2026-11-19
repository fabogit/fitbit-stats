"""Unreadable files are reported, not skipped silently."""
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api
import config
from modules import briefing, etl, parsers

GLOBAL = "Global Export Data"


def write_export(data_dir, bad_json=False, bad_csv=False):
    folder = data_dir / GLOBAL
    folder.mkdir(parents=True)
    rows = [{"dateTime": f"01/{d:02d}/24 12:00:00", "value": "10"} for d in range(1, 4)]
    (folder / "calories-2024-01-01.json").write_text(json.dumps(rows))
    if bad_json:
        (folder / "steps-2024-01-01.json").write_text("{ this is not json")
    if bad_csv:
        stress = data_dir / "Stress Score"
        stress.mkdir()
        (stress / "Stress Score.csv").write_bytes(b"\xff\xfe\x00\x81\x82 garbage\n\xc3\x28")


def test_unreadable_json_is_reported_by_name(tmp_path):
    write_export(tmp_path, bad_json=True)
    warnings = []
    df = etl.merge_all_data(tmp_path, warnings=warnings)
    assert df is not None  # the readable file still produces data
    assert [w["file"] for w in warnings] == ["steps-2024-01-01.json"]
    assert str(tmp_path) not in json.dumps(warnings)


def test_unreadable_csv_is_reported_by_name(tmp_path):
    write_export(tmp_path, bad_csv=True)
    warnings = []
    etl.merge_all_data(tmp_path, warnings=warnings)
    assert [w["file"] for w in warnings] == ["Stress Score.csv"]
    assert str(tmp_path) not in json.dumps(warnings)


def test_clean_run_has_no_warnings(tmp_path):
    write_export(tmp_path)
    warnings = []
    etl.merge_all_data(tmp_path, warnings=warnings)
    assert warnings == []


def test_missing_files_are_not_warnings(tmp_path):
    # A collection with no files at all is an empty result, not an error.
    (tmp_path / GLOBAL).mkdir()
    warnings = []
    assert etl.merge_all_data(tmp_path, warnings=warnings) is None
    assert warnings == []


def test_csv_reader_raises_on_empty_file(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("")
    with pytest.raises(ValueError):
        parsers._read_csv(str(f))


def test_missing_file_reason_has_no_path(tmp_path):
    missing = str(tmp_path / "gone.json")
    reason = etl._skip_reason(FileNotFoundError(2, "No such file or directory", missing), missing)
    assert str(tmp_path) not in reason and "No such file" in reason


def test_finished_event_carries_count_and_names():
    ev = api.finished_event("success", "ok", [
        {"file": "a.json", "reason": "x"}, {"file": "b.csv", "reason": "y"},
        {"file": "a.json", "reason": "z"}])
    assert ev["warning_count"] == 3
    assert ev["warning_files"] == ["a.json", "b.csv"]
    assert "a.json" in ev["message"] and "b.csv" in ev["message"]
    clean = api.finished_event("success", "ok", [])
    assert clean["warning_count"] == 0 and clean["warning_files"] == []


def test_run_ends_with_warning_naming_the_file(tmp_path, monkeypatch):
    """Whole API run: the etl_finished event names the unreadable file."""
    data, out = tmp_path / "data", tmp_path / "out"
    out.mkdir()
    write_export(data, bad_json=True)
    monkeypatch.delenv("FITSTATS_API_TOKEN", raising=False)
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(out))
    body = {"dob": "1990-01-01", "gender": "male", "height": 180, "weight": 80,
            "data_path": str(data)}
    client = TestClient(api.app)
    with client.websocket_connect("/ws/status") as ws:
        assert client.post("/api/start", json=body).status_code == 200
        event = ws.receive_json()
        while event["event"] != "etl_finished":
            event = ws.receive_json()
    assert event["status"] == "success"
    assert event["warning_count"] == 1
    assert event["warning_files"] == ["steps-2024-01-01.json"]
    assert str(data) not in json.dumps(event)
    listed = client.get("/api/etl-warnings").json()
    assert [w["file"] for w in listed] == ["steps-2024-01-01.json"]


def test_warnings_endpoint_empty_without_file(tmp_path, monkeypatch):
    monkeypatch.delenv("FITSTATS_API_TOKEN", raising=False)
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path))
    assert TestClient(api.app).get("/api/etl-warnings").json() == []
    (tmp_path / etl.WARNINGS_FILE).write_text("not json")
    assert TestClient(api.app).get("/api/etl-warnings").json() == []


def test_age_of_invalid_dob_is_zero():
    assert briefing.calculate_age("not a date", pd.Timestamp("2024-01-01")) == 0
