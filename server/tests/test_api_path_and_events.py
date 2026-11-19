import pytest
from fastapi.testclient import TestClient

import api

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
