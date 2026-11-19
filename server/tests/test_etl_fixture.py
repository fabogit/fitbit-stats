"""ETL on the small synthetic export: filtering, loading, merging, full pipeline."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import config
from modules import etl, parsers

FIXTURES = Path(__file__).parent / "fixtures"
GLOBAL = "Global Export Data"
GOOGLE = "Physical Activity_GoogleData"
DAYS = ["2024-03-28", "2024-03-29", "2024-03-30", "2024-03-31",
        "2024-04-01", "2024-04-02", "2024-04-03"]
NAN = np.nan


def week(values=None):
    idx = pd.to_datetime(DAYS)
    return pd.DataFrame({"v": values or list(range(7))}, index=idx)


def dates(df):
    return [d.strftime("%Y-%m-%d") for d in df.index]


# --- fixtures stay small ---

def test_fixture_files_total_less_than_100_kb():
    total = sum(p.stat().st_size for p in FIXTURES.rglob("*") if p.is_file())
    assert 0 < total < 100 * 1024


# --- filter_by_date ---

def test_filter_by_date_bounds_are_inclusive(configure_etl, tmp_path):
    configure_etl(tmp_path, "2024-03-30", "2024-04-01")
    assert dates(etl.filter_by_date(week())) == ["2024-03-30", "2024-03-31", "2024-04-01"]


def test_filter_by_date_only_start_or_only_end(configure_etl, tmp_path):
    configure_etl(tmp_path, start="2024-04-01")
    assert dates(etl.filter_by_date(week())) == DAYS[4:]
    configure_etl(tmp_path, end="2024-03-29")
    assert dates(etl.filter_by_date(week())) == DAYS[:2]


def test_filter_by_date_without_limits_keeps_everything(configure_etl, tmp_path):
    configure_etl(tmp_path)
    assert dates(etl.filter_by_date(week())) == DAYS


def test_filter_by_date_none_and_empty_pass_through(configure_etl, tmp_path):
    configure_etl(tmp_path, "2024-03-30", None)
    assert etl.filter_by_date(None) is None
    empty = pd.DataFrame()
    assert etl.filter_by_date(empty) is empty


def test_filter_by_date_accepts_a_string_index(configure_etl, tmp_path):
    configure_etl(tmp_path, "2024-03-30", "2024-03-31")
    df = pd.DataFrame({"v": [1, 2, 3, 4]}, index=DAYS[:4])
    assert dates(etl.filter_by_date(df)) == ["2024-03-30", "2024-03-31"]


def test_filter_by_date_leaves_an_unparseable_index_alone(configure_etl, tmp_path):
    configure_etl(tmp_path, "2024-03-30", None)
    df = pd.DataFrame({"v": [1, 2]}, index=["a", "b"])
    assert etl.filter_by_date(df).index.tolist() == ["a", "b"]


# --- load_collection ---

def test_load_collection_concatenates_files_in_date_order(configure_etl, export_dir):
    configure_etl(export_dir)
    df = etl.load_collection(GLOBAL, "calories-*.json", parsers.parse_calories_intraday)
    assert df.index.is_monotonic_increasing
    # 7 days over two monthly files, plus one day with 0 calories in the April file
    assert dates(df) == DAYS + ["2024-04-05"]
    assert df.loc["2024-04-01", "calories_total"] == 2400.0
    assert df.loc["2024-04-05", "calories_total"] == 0.0


def test_load_collection_strips_timezones(configure_etl, export_dir):
    configure_etl(export_dir)
    df = etl.load_collection(GOOGLE, "time_in_heart_rate_zone_*.csv", parsers.parse_active_zones_csv)
    assert df.index.tz is None
    assert dates(df) == [DAYS[i] for i in (0, 1, 2, 4, 5, 6)]


def test_load_collection_without_files_is_empty(configure_etl, tmp_path):
    configure_etl(tmp_path)
    assert etl.load_collection(GLOBAL, "steps-*.json", parsers.parse_steps_json).empty


def test_load_collection_one_bad_file_keeps_the_others(configure_etl, tmp_path):
    folder = tmp_path / GLOBAL
    folder.mkdir()
    (folder / "steps-2024-03-01.json").write_text(
        json.dumps([{"dateTime": "03/01/24 09:00:00", "value": "100"}]))
    (folder / "steps-2024-04-01.json").write_text("{ not json")
    configure_etl(tmp_path)
    warnings = []
    df = etl.load_collection(GLOBAL, "steps-*.json", parsers.parse_steps_json, warnings)
    assert df["steps"].tolist() == [100.0]
    assert [w["file"] for w in warnings] == ["steps-2024-04-01.json"]


def test_load_collection_overlapping_days_leave_one_row_per_day(configure_etl, tmp_path):
    # Which of the two values survives is deliberately not checked.
    folder = tmp_path / GLOBAL
    folder.mkdir()
    for name, value in (("calories-2024-03-01.json", "10"), ("calories-2024-03-15.json", "20")):
        (folder / name).write_text(json.dumps([{"dateTime": "03/20/24 12:00:00", "value": value}]))
    configure_etl(tmp_path)
    df = etl.load_collection(GLOBAL, "calories-*.json", parsers.parse_calories_intraday)
    assert dates(df) == ["2024-03-20"]


# --- merge_all_data on the full export ---

@pytest.fixture
def merged(configure_etl, export_dir):
    configure_etl(export_dir)
    return etl.merge_all_data()


EXPECTED_COLUMNS = {
    "resting_bpm", "min_bpm", "max_bpm", "avg_bpm", "steps", "distance",
    "exercise_duration", "exercise_calories", "exercise_count", "exercise_aef",
    "weight", "bmi", "calories_total", "overall_score", "deep_sleep_in_minutes", "restlessness",
    "sleep_deep", "sleep_light", "sleep_rem", "sleep_awake", "spo2_avg", "spo2_min", "spo2_max",
    "rmssd", "stress_score", "very_active_minutes", "moderately_active_minutes",
    "lightly_active_minutes", "sedentary_minutes", "acwr_ratio", "vo2max", "readiness_score",
    "respiratory_rate", "temperature_variation",
    "zone_out_of_range", "zone_light", "zone_moderate", "zone_vigorous",
}


def test_merge_full_export_index_and_columns(merged):
    assert merged.index.name == "date"
    assert dates(merged) == DAYS
    assert set(merged.columns) == EXPECTED_COLUMNS


def test_merge_full_export_spot_values(merged):
    d1 = merged.loc["2024-03-28"]
    # Every value below can be read straight off the fixture files.
    assert d1["resting_bpm"] == 60
    assert (d1["min_bpm"], d1["max_bpm"], d1["avg_bpm"]) == (60, 100, 80.0)
    assert d1["steps"] == 1500
    assert d1["distance"] == 200000
    assert (d1["exercise_duration"], d1["exercise_calories"], d1["exercise_count"]) == (40.0, 400, 2)
    assert d1["weight"] == 80.0
    assert d1["calories_total"] == 2000.0
    assert d1["overall_score"] == 82
    assert d1["sleep_deep"] == 60
    assert d1["spo2_avg"] == 96.0
    assert d1["rmssd"] == 40
    assert d1["stress_score"] == 60
    assert d1["very_active_minutes"] == 10
    assert d1["moderately_active_minutes"] == 20
    assert d1["lightly_active_minutes"] == 60
    assert d1["sedentary_minutes"] == 600
    assert d1["acwr_ratio"] == 0.99
    assert d1["vo2max"] == 42.0
    assert d1["readiness_score"] == 70
    assert d1["respiratory_rate"] == 14.0
    assert d1["temperature_variation"] == pytest.approx(0.7)
    assert (d1["zone_light"], d1["zone_moderate"], d1["zone_vigorous"]) == (10, 4, 2)
    d5 = merged.loc["2024-04-01"]
    assert (d5["steps"], d5["weight"], d5["exercise_calories"]) == (1900, 78.0, 200)


def test_merge_zero_fills_only_activity_columns(merged):
    # 03-31 has no steps, activity minutes, exercise or zone rows in the export
    gap = merged.loc["2024-03-31"]
    for col in ("steps", "distance", "very_active_minutes", "moderately_active_minutes",
                "lightly_active_minutes", "sedentary_minutes", "exercise_duration",
                "exercise_calories", "exercise_count"):
        assert gap[col] == 0, col
    for col in ("zone_light", "zone_moderate", "zone_vigorous", "zone_out_of_range"):
        assert pd.isna(gap[col]), col
    # 03-30 has no sleep record
    for col in ("sleep_deep", "sleep_light", "sleep_rem", "sleep_awake"):
        assert pd.isna(merged.loc["2024-03-30", col]), col


def test_merge_drops_days_without_calories(merged):
    # 04-04 has only heart rate, 04-05 has a calories entry of 0
    assert pd.Timestamp("2024-04-04") not in merged.index
    assert pd.Timestamp("2024-04-05") not in merged.index
    assert (merged["calories_total"] > 0).all()


def test_merge_across_two_months_covers_every_day(merged):
    assert merged.index[0] == pd.Timestamp("2024-03-28")
    assert merged.index[-1] == pd.Timestamp("2024-04-03")
    assert len(merged) == 7


def test_merge_respects_explicit_dates(configure_etl, export_dir):
    configure_etl(export_dir, "2024-03-30", "2024-04-01")
    assert dates(etl.merge_all_data()) == ["2024-03-30", "2024-03-31", "2024-04-01"]


# --- the whole pipeline (merge + metrics) ---

def test_pipeline_golden_values(run_pipeline, export_dir):
    out = run_pipeline(export_dir)
    assert dates(out) == DAYS

    def check(column, expected, **kw):
        np.testing.assert_allclose(out[column].to_numpy(dtype=float), expected,
                                   equal_nan=True, **({"atol": 1e-9} | kw))

    # zone minutes: light x 1 + moderate x 2.5 + vigorous x 4
    # 28 = 10 + 4 x 2.5 + 2 x 4 ; 20 ; 30 ; (no zone data) ; 10 ; 25 = 20 + 2 x 2.5 ; 34 = 30 + 4
    check("trimp", [28, 20, 30, NAN, 10, 25, 34])
    # (deep + light + rem) / (that + awake): 410/448, 410/440, none, 450/480, 470/500, 490/520, 510/540
    check("sleep_efficiency", [91.5, 93.2, NAN, 93.8, 94.0, 94.2, 94.4])
    # night minus the mean of the nights so far: 450 - 423.33 = 26.7, 470 - 435 = 35, ...
    check("sleep_debt", [0.0, 0.0, NAN, 26.7, 35.0, 44.0, 53.3])
    # weight 80 on 03-28 and 78 on 04-01, linear in between; male, 180 cm, born 1984-03-28
    check("weight_filled", [80.0, 79.5, 79.0, 78.5, 78.0, 78.0, 78.0])
    check("bmr", [1730.0, 1724.986, 1719.973, 1714.959, 1709.945, 1709.932, 1709.918], atol=0.01)
    # calories (2000, 2100, ...) minus BMR; intensity = active calories / 90 active minutes,
    # 0 on 03-31 where the export has no activity minutes
    check("active_calories", [270.0, 375.014, 480.027, 585.041, 690.055, 790.068, 890.082], atol=0.01)
    check("intensity_index", [3.0, 4.167, 5.334, 0.0, 7.667, 8.779, 9.890], atol=0.01)
    # rolling week over the days that have zone data, from the third sample on:
    # 03-30: 28, 20, 30 -> mean 26, std 5.29 -> 4.91, strain 78 x 4.91 = 383.0
    # 04-01: 28, 20, 30, 10 -> mean 22, std 9.09 -> 2.42, strain 88 x 2.42 = 213.0
    # 04-02: + 25 -> 2.83, 319.8 ; 04-03: + 34 -> 2.87, 421.9
    # (the first two days are not pinned on purpose)
    mono = out["training_monotony"].to_numpy(dtype=float)
    strain = out["training_strain"].to_numpy(dtype=float)
    np.testing.assert_allclose(mono[[2, 4, 5, 6]], [4.91, 2.42, 2.83, 2.87])
    np.testing.assert_allclose(strain[[2, 4, 5, 6]], [383.0, 213.0, 319.8, 421.9])
    assert np.isnan(mono[3]) and np.isnan(strain[3])
    assert "readiness_raw" in out.columns


# --- export_to_json ---

def test_export_to_json_dates_and_nulls(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path / "out"))
    df = pd.DataFrame({"steps": [100.0, NAN]}, index=pd.to_datetime(["2024-03-28", "2024-03-29"]))
    df.index.name = "date"
    etl.export_to_json(df)
    rows = json.loads((tmp_path / "out" / "dashboard_data.json").read_text())
    assert rows == [{"date": "2024-03-28", "steps": 100.0}, {"date": "2024-03-29", "steps": None}]
