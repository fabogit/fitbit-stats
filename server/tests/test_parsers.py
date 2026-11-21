"""One or more tests per parser: index, columns and aggregation on a known input."""
import pandas as pd
import pytest

from modules import load_plan, parsers
from modules.sources import Special

GLOBAL = "Global Export Data"
GOOGLE = "Physical Activity_GoogleData"


def day(s):
    return pd.Timestamp(s)


def csv_file(tmp_path, text, name="x.csv"):
    f = tmp_path / name
    f.write_text(text)
    return f


def json_file(tmp_path, text, name="x.json"):
    f = tmp_path / name
    f.write_text(text)
    return f


# --- every parser is registered, so a new one gets a test ---

def test_every_parser_function_is_in_the_table(parser_table):
    in_table = {s.key for v in parser_table.values() for s in (v if isinstance(v, tuple) else (v,))}
    assert in_table == {s.key for s in load_plan.LOAD_PLAN}
    special = {n for n in dir(parsers) if n.startswith("parse_")}
    assert special == {s.reader.parse.__name__ for s in load_plan.LOAD_PLAN
                       if isinstance(s.reader, Special)}


# --- resting heart rate ---

def test_resting_heart_rate_values_and_zero_dropped(parse, export_dir):
    df = parse("resting_heart_rate", export_dir / GLOBAL / "resting_heart_rate-2024-03-28.json")
    assert df.index.name == "date"
    assert list(df.columns) == ["resting_bpm"]
    # 7 entries, the one of 03-29 is 0 and is dropped
    assert day("2024-03-29") not in df.index
    assert df["resting_bpm"].tolist() == [60, 58, 57, 56, 55, 54]


def test_resting_heart_rate_without_valid_records_returns_none(parse, tmp_path):
    assert parse("resting_heart_rate", json_file(tmp_path, "[]")) is None
    only_zero = '[{"value": {"date": "03/28/24", "value": 0}}]'
    assert parse("resting_heart_rate", json_file(tmp_path, only_zero)) is None


# --- heart rate (intraday summary; more cases in test_heart_rate_parser.py) ---

def test_heart_rate_fixture_days(parse, export_dir):
    df = parse("heart_rate", export_dir / GLOBAL / "heart_rate-2024-03-28.json")
    # 03-28: samples 60, 100, 80 and a 0 that is ignored -> 240 / 3
    assert df.loc["2024-03-28"].tolist() == [60, 100, 80.0]
    # 04-04 has a single sample
    assert df.loc["2024-04-04"].tolist() == [70, 70, 70.0]
    assert len(df) == 8


# --- weight ---

def test_weight_pounds_to_kilograms_rounded(parse, export_dir):
    df = parse("weight", export_dir / GLOBAL / "weight-2024-03-28.json")
    assert list(df.columns) == ["weight", "bmi"]
    assert df.index.name == "date"
    # 176.4 lb x 0.453592 = 80.01 -> 80.0 ; 171.9 lb x 0.453592 = 77.97 -> 78.0
    assert df["weight"].tolist() == [80.0, 78.0]
    assert df.index.tolist() == [day("2024-03-28"), day("2024-04-01")]


def test_weight_two_weigh_ins_same_day_keep_the_first(parse, export_dir):
    df = parse("weight", export_dir / GLOBAL / "weight-2024-03-28.json")
    # the second weigh-in of 03-28 is 198.4 lb (90.0 kg): not kept
    assert df.loc["2024-03-28", "weight"] == 80.0
    assert df.loc["2024-03-28", "bmi"] == 24.7


def test_weight_empty_returns_none(parse, tmp_path):
    assert parse("weight", json_file(tmp_path, "[]")) is None


# --- sleep score ---

def test_sleep_score_takes_max_per_day(parse, export_dir):
    df = parse("sleep_score", export_dir / "Sleep Score" / "sleep_score.csv")
    assert len(df) == 7
    # two entries on 03-28: scores 78 and 82, deep sleep 50 and 40
    assert df.loc["2024-03-28", "overall_score"] == 82
    assert df.loc["2024-03-28", "deep_sleep_in_minutes"] == 50
    assert df.loc["2024-03-29", "overall_score"] == 80
    assert df.index.name == "date"
    assert (df.index == df.index.normalize()).all()


def test_sleep_score_optional_columns_may_be_missing(parse, tmp_path):
    f = csv_file(tmp_path, "timestamp,overall_score\n2024-03-28T07:00:00Z,80\n")
    df = parse("sleep_score", f)
    assert list(df.columns) == ["overall_score"]
    assert df["overall_score"].tolist() == [80]


# --- simple activity files ---

@pytest.mark.parametrize("name", ["very_active_minutes", "moderately_active_minutes",
                                  "lightly_active_minutes", "sedentary_minutes"])
def test_simple_activity_column_is_named_after_the_file(parse, export_dir, name):
    df = parse("simple_activity", export_dir / GLOBAL / f"{name}-2024-03-28.json")
    assert list(df.columns) == [name]
    assert len(df) == 6   # 03-31 is not in the file
    assert df.index.name == "date"


def test_simple_activity_values_and_non_numeric(parse, export_dir, tmp_path):
    df = parse("simple_activity", export_dir / GLOBAL / "very_active_minutes-2024-03-28.json")
    assert df["very_active_minutes"].tolist() == [10] * 6
    f = json_file(tmp_path, '[{"dateTime": "03/28/24 00:00:00", "value": "30"},'
                            ' {"dateTime": "03/29/24 00:00:00", "value": "x"}]',
                  "lightly_active_minutes-2024-03-28.json")
    out = parse("simple_activity", f)
    assert out["lightly_active_minutes"].iloc[0] == 30
    assert pd.isna(out["lightly_active_minutes"].iloc[1])


def test_simple_activity_empty_returns_none(parse, tmp_path):
    assert parse("simple_activity", json_file(tmp_path, "[]", "sedentary_minutes-1.json")) is None


# --- heart-rate zones ---

def test_zones_minutes_per_day_and_zone(parse, export_dir):
    df = parse("active_zones", export_dir / GOOGLE / "time_in_heart_rate_zone_2024-03-01.csv")
    df.index = df.index.tz_localize(None)
    # 03-28: 5 out of range, 10 light, 4 moderate, 2 vigorous minutes
    assert df.loc["2024-03-28"].to_dict() == {
        "zone_light": 10, "zone_moderate": 4, "zone_out_of_range": 5, "zone_vigorous": 2}
    assert df.loc["2024-03-29", "zone_light"] == 20
    assert df.loc["2024-03-29", "zone_moderate"] == 0
    assert df.loc["2024-03-30", "zone_light"] == 30
    assert len(df) == 3


def test_zones_minutes_around_midnight_go_to_their_own_day(parse, tmp_path):
    f = csv_file(tmp_path, "timestamp,heart rate zone type,data source\n"
                           "2024-03-01T23:59:00Z,LIGHT,x\n"
                           "2024-03-02T00:01:00Z,LIGHT,x\n"
                           "2024-03-02T00:02:00Z,LIGHT,x\n")
    df = parse("active_zones", f)
    df.index = df.index.tz_localize(None)
    assert df["zone_light"].to_dict() == {day("2024-03-01"): 1, day("2024-03-02"): 2}


def test_zones_unknown_zone_name_gets_a_generic_column(parse, tmp_path):
    f = csv_file(tmp_path, "timestamp,heart rate zone type,data source\n"
                           "2024-03-01T10:00:00Z,SOME NEW,x\n")
    assert parse("active_zones", f)["zone_some_new"].tolist() == [1]


def test_zones_missing_column_is_reported(parse, tmp_path):
    with pytest.raises(parsers.MissingColumns):
        parse("active_zones", csv_file(tmp_path, "timestamp,other\n2024-03-01T10:00:00Z,1\n"))


# --- SpO2 ---

def test_spo2_duplicates_are_averaged(parse, export_dir):
    df = parse("spo2", export_dir / "Oxygen Saturation (SpO2)" / "Daily SpO2 - 2024-03-28-2024-04-03.csv")
    assert list(df.columns) == ["spo2_avg", "spo2_min", "spo2_max"]
    assert len(df) == 7
    # two rows on 03-28: (95, 92, 98) and (97, 94, 100)
    assert df.loc["2024-03-28"].tolist() == [96.0, 93.0, 99.0]
    assert df.loc["2024-03-29"].tolist() == [96.0, 93.0, 99.0]


# --- JSON sums per day ---

def test_calories_sum_per_day(parse, export_dir):
    df = parse("calories", export_dir / GLOBAL / "calories-2024-03-01.json")
    assert list(df.columns) == ["calories_total"]
    assert df.index.name == "date"
    # each day is two samples: (total - 500.25) and 500.25
    assert df["calories_total"].tolist() == [2000.0, 2100.0, 2200.0, 2300.0]


def test_calories_non_numeric_values_are_ignored_in_the_sum(parse, tmp_path):
    f = json_file(tmp_path, '[{"dateTime": "03/28/24 08:00:00", "value": "x"},'
                            ' {"dateTime": "03/28/24 09:00:00", "value": "5.5"}]')
    assert parse("calories", f)["calories_total"].tolist() == [5.5]


def test_calories_empty_returns_none(parse, tmp_path):
    assert parse("calories", json_file(tmp_path, "[]")) is None


def test_steps_sum_per_day(parse, export_dir):
    df = parse("steps", export_dir / GLOBAL / "steps-2024-03-28.json")
    assert list(df.columns) == ["steps"]
    assert len(df) == 6
    # day i is (1000 + 100 i) + 500
    assert df.loc["2024-03-28", "steps"] == 1500
    assert df.loc["2024-04-01", "steps"] == 1900


def test_distance_sum_per_day(parse, export_dir):
    df = parse("distance", export_dir / GLOBAL / "distance-2024-03-28.json")
    assert list(df.columns) == ["distance"]
    # 03-28: 150000 + 50000
    assert df.loc["2024-03-28", "distance"] == 200000


@pytest.mark.parametrize("key", ["steps", "distance"])
def test_steps_and_distance_empty_return_none(parse, tmp_path, key):
    assert parse(key, json_file(tmp_path, "[]")) is None


# --- sleep stages ---

def test_sleep_json_sums_sessions_and_maps_stages(parse, export_dir):
    df = parse("sleep_json", export_dir / GLOBAL / "sleep-2024-03-28.json")
    assert list(df.columns) == ["sleep_deep", "sleep_light", "sleep_rem", "sleep_awake"]
    # 03-28: a stages night (deep 60, light 240, rem 90, wake 30) plus a classic
    # nap (asleep 20 -> light, restless 5 + awake 3 -> awake)
    assert df.loc["2024-03-28"].tolist() == [60, 260, 90, 38]
    # 03-29: light 240 + 20
    assert df.loc["2024-03-29"].tolist() == [60, 260, 90, 30]
    assert day("2024-03-30") not in df.index
    assert len(df) == 6


def test_sleep_json_entry_without_date_is_skipped(parse, tmp_path):
    entry = '{"levels": {"summary": {"deep": {"minutes": 5}}}}'
    assert parse("sleep_json", json_file(tmp_path, f"[{entry}]")) is None


# --- CSV sources with one value column ---

def test_hrv_returns_rmssd(parse, export_dir):
    df = parse("hrv", export_dir / "Heart Rate Variability" /
               "Daily Heart Rate Variability Summary - 2024-03-(28).csv")
    assert list(df.columns) == ["rmssd"]
    assert df["rmssd"].tolist() == [40, 50, 60, 45, 55, 50, 52]


def test_stress_zero_score_is_dropped(parse, export_dir):
    df = parse("stress", export_dir / "Stress Score" / "Stress Score.csv")
    assert list(df.columns) == ["stress_score"]
    # the 03-30 row has score 0
    assert df["stress_score"].tolist() == [60, 62, 58, 64, 66, 61]
    assert day("2024-03-30") not in df.index


def test_stress_headers_are_stripped(parse, tmp_path):
    f = csv_file(tmp_path, "DATE , STRESS_SCORE \n2024-03-28T00:00:00,55\n")
    assert parse("stress", f)["stress_score"].tolist() == [55]


@pytest.mark.parametrize("key, path, column, first", [
    ("acwr", f"{GOOGLE}/cardio_acute_chronic_workload_ratio.csv", "acwr_ratio", 0.99),
    ("vo2max", f"{GOOGLE}/demographic_vo2max.csv", "vo2max", 42.0),
    ("readiness", f"{GOOGLE}/daily_readiness.csv", "readiness_score", 70),
    ("respiratory_rate", f"{GOOGLE}/daily_respiratory_rate.csv", "respiratory_rate", 14.0),
])
def test_google_csv_sources_rename_their_column(parse, export_dir, key, path, column, first):
    df = parse(key, export_dir / path)
    assert list(df.columns) == [column]
    assert len(df) == 7
    assert df.index.name == "date"
    assert df[column].iloc[0] == first


def test_skin_temperature_is_nightly_minus_baseline(parse, export_dir):
    df = parse("skin_temperature", export_dir / GOOGLE / "daily_sleep_temperature_derivations.csv")
    assert list(df.columns) == ["temperature_variation"]
    # 03-28: 34.5 - 33.8
    assert df["temperature_variation"].iloc[0] == pytest.approx(0.7)
    # 03-29: 33.9 - 33.8
    assert df["temperature_variation"].iloc[1] == pytest.approx(0.1)


@pytest.mark.parametrize("key", ["hrv", "stress", "acwr", "vo2max", "readiness",
                                 "respiratory_rate", "skin_temperature"])
def test_csv_without_the_key_column_is_reported(parse, tmp_path, key):
    f = csv_file(tmp_path, "timestamp,other\n2024-03-28T00:00:00Z,1\n")
    with pytest.raises(parsers.MissingColumns):
        parse(key, f)


# --- exercise ---

def test_exercise_aggregates_sessions_per_day(parse, export_dir):
    df = parse("exercise", export_dir / GLOBAL / "exercise-0.json")
    assert df.index.name == "date"
    # 03-28: 10 min / 100 kcal / HR 100 and 30 min / 300 kcal / HR 150
    row = df.loc["2024-03-28"]
    assert row["exercise_duration"] == 40.0
    assert row["exercise_calories"] == 400
    assert row["exercise_count"] == 2
    assert row["exercise_aef"] == pytest.approx(1.5)   # mean(100/100, 300/150)
    # 04-01: one session, 20 min, 200 kcal, HR 100
    row = df.loc["2024-04-01"]
    assert (row["exercise_duration"], row["exercise_calories"], row["exercise_count"]) == (20.0, 200, 1)
    assert row["exercise_aef"] == pytest.approx(2.0)


def test_exercise_session_without_heart_rate_is_not_in_the_aef_mean(parse, tmp_path):
    f = json_file(tmp_path, '[{"startTime": "03/28/24 07:00:00", "duration": 600000,'
                            ' "calories": 100, "averageHeartRate": 100},'
                            ' {"startTime": "03/28/24 18:00:00", "duration": 600000, "calories": 50}]')
    row = parse("exercise", f).loc["2024-03-28"]
    assert row["exercise_count"] == 2
    assert row["exercise_aef"] == pytest.approx(1.0)


def test_exercise_empty_returns_none(parse, tmp_path):
    assert parse("exercise", json_file(tmp_path, "[]")) is None


# --- unreadable files are not swallowed by the parser ---

@pytest.mark.parametrize("key", ["hrv", "stress", "acwr", "vo2max", "readiness",
                                 "respiratory_rate", "skin_temperature", "spo2",
                                 "sleep_score", "active_zones"])
def test_empty_csv_raises(parse, tmp_path, key):
    with pytest.raises(ValueError):
        parse(key, csv_file(tmp_path, ""))
