import json

import pandas as pd
from fastapi.testclient import TestClient

import api
from modules import briefing, etl, metrics



# --- /api/brief: a missing brief is a 404, not a 500 ---

def test_brief_without_data_file_is_404(tmp_path, monkeypatch):
    monkeypatch.delenv("FITSTATS_API_TOKEN", raising=False)
    monkeypatch.setattr(briefing, "DATA_FILE", str(tmp_path / "missing.csv"))
    r = TestClient(api.app).post("/api/brief", json={"date": "2024-01-05"})
    assert r.status_code == 404
    assert "Run ETL first" in r.json()["detail"]
    assert not r.json()["detail"].startswith("404")


def test_brief_unexpected_error_is_still_500(monkeypatch):
    monkeypatch.delenv("FITSTATS_API_TOKEN", raising=False)

    def boom(_date):
        raise RuntimeError("boom")

    monkeypatch.setattr(api, "get_daily_brief", boom)
    r = TestClient(api.app).post("/api/brief", json={})
    assert r.status_code == 500


# --- export_to_json: one write per run ---

def test_export_writes_dashboard_json_once(tmp_path, monkeypatch):
    out = tmp_path / "shared"
    calls = []
    real = pd.DataFrame.to_json

    def spy(self, path=None, *a, **kw):
        calls.append(str(path))
        return real(self, path, *a, **kw)

    monkeypatch.setattr(pd.DataFrame, "to_json", spy)
    df = pd.DataFrame({"steps": [1, 2]},
                      index=pd.to_datetime(["2024-01-01", "2024-01-02"]))
    df.index.name = "date"
    etl.export_to_json(df, out)
    assert calls == [str(out / "dashboard_data.json")]
    assert len(json.loads((out / "dashboard_data.json").read_text())) == 2


# --- days without a sleep record stay empty ---

def write_export(data_dir, sleep_days, all_days):
    folder = data_dir / "Global Export Data"
    folder.mkdir(parents=True)
    rows = [{"dateTime": f"01/{d:02d}/24 12:00:00", "value": "10"}
            for d in all_days]
    (folder / "calories-2024-01-01.json").write_text(json.dumps(rows))
    sleep = [{"dateOfSleep": f"2024-01-{d:02d}",
              "levels": {"summary": {"deep": {"minutes": 60},
                                     "light": {"minutes": 240},
                                     "rem": {"minutes": 90},
                                     "wake": {"minutes": 30}}}}
             for d in sleep_days]
    (folder / "sleep-2024-01-01.json").write_text(json.dumps(sleep))


def run_metrics(data_dir):
    df = etl.merge_all_data(data_dir)
    return metrics.calculate_advanced_metrics(df)


def test_day_without_sleep_is_null_not_zero(tmp_path):
    write_export(tmp_path, sleep_days=[1, 2, 4, 5], all_days=[1, 2, 3, 4, 5])
    df = run_metrics(tmp_path)
    gap = df.loc["2024-01-03"]
    for col in ("sleep_deep", "sleep_light", "sleep_rem", "sleep_awake",
                "sleep_efficiency", "sleep_debt"):
        assert pd.isna(gap[col]), col
    assert df.loc["2024-01-04", "sleep_deep"] == 60


def test_missing_sleep_does_not_shift_sleep_debt_of_other_days(tmp_path):
    # Identical nights on every recorded day: debt must be 0 on all of them,
    # including the days after a gap (a 0-minute night would drag the mean).
    write_export(tmp_path, sleep_days=[1, 2, 4, 5], all_days=[1, 2, 3, 4, 5])
    df = run_metrics(tmp_path)
    recorded = df.drop(pd.Timestamp("2024-01-03"))
    assert (recorded["sleep_debt"] == 0).all()
