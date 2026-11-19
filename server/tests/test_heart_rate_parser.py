import json

import pandas as pd

from modules import etl


def write_heart_rate(path, samples):
    """Write a tiny intraday heart-rate file in the export format."""
    rows = [{"dateTime": ts, "value": {"bpm": bpm, "confidence": 2}}
            for ts, bpm in samples]
    path.write_text(json.dumps(rows))


SAMPLES = [
    ("03/01/24 08:00:00", 60),
    ("03/01/24 08:00:05", 100),
    ("03/01/24 23:59:55", 70),
    ("03/02/24 00:00:05", 80),
    ("03/02/24 00:00:10", 0),     # zero readings are ignored
    ("03/02/24 12:00:00", 91),
    ("03/02/24 12:00:05", 90),
    ("03/02/24 12:00:10", 89),
    ("03/02/24 12:00:15", 84),
]


def test_daily_min_max_avg(tmp_path, parse):
    f = tmp_path / "heart_rate-2024-03-01.json"
    write_heart_rate(f, SAMPLES)
    df = parse("heart_rate", f)
    assert df.index.name == "date"
    assert list(df.index) == [pd.Timestamp("2024-03-01"), pd.Timestamp("2024-03-02")]
    assert list(df.columns) == ["min_bpm", "max_bpm", "avg_bpm"]
    assert df.loc["2024-03-01"].tolist() == [60, 100, 76.7]   # 230 / 3
    assert df.loc["2024-03-02"].tolist() == [80, 91, 86.8]    # 434 / 5


def test_empty_or_all_zero_file_returns_none(tmp_path, parse):
    f = tmp_path / "heart_rate-2024-03-01.json"
    f.write_text("[]")
    assert parse("heart_rate", f) is None
    write_heart_rate(f, [("03/01/24 08:00:00", 0)])
    assert parse("heart_rate", f) is None


def test_etl_merges_heart_rate_files_in_parallel(tmp_path):
    folder = tmp_path / "Global Export Data"
    folder.mkdir()
    n = 12   # more files than workers, so the process pool is used
    for i in range(n):
        day = f"03/{i + 1:02d}/24"
        write_heart_rate(folder / f"heart_rate-2024-03-{i + 1:02d}.json",
                         [(f"{day} 10:00:00", 60 + i), (f"{day} 10:00:05", 80 + i)])
        (folder / f"calories-2024-03-{i + 1:02d}.json").write_text(
            json.dumps([{"dateTime": f"{day} 12:00:00", "value": "10"}]))
    df = etl.merge_all_data(tmp_path)
    assert len(df) == n
    assert df["min_bpm"].tolist() == [60 + i for i in range(n)]
    assert df["max_bpm"].tolist() == [80 + i for i in range(n)]
    assert df["avg_bpm"].tolist() == [70.0 + i for i in range(n)]
