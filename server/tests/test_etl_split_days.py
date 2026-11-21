"""A day that appears in two export files is combined, not cut to the last file's part.

Every test writes the same invented samples twice: split over two files and all
in one file, and checks that the ETL gives the same rows.
"""
import glob
import json

import pandas as pd
import pytest

from conftest import S, parser
from modules import etl

GLOBAL = "Global Export Data"
ZONES = "Physical Activity_GoogleData"


def write_json(folder, name, rows):
    (folder / name).write_text(json.dumps(rows))


def load(data_dir, folder, pattern, parser, rules):
    return etl.load_collection(data_dir, folder, pattern, parser, combine=rules)


@pytest.fixture
def two_layouts(tmp_path):
    """Return make(folder, name_a, name_b, rows_a, rows_b, name_single) -> (split_dir, single_dir)."""
    def make(folder, names, parts, single_name):
        split_dir, single_dir = tmp_path / "split", tmp_path / "single"
        for d in (split_dir, single_dir):
            (d / folder).mkdir(parents=True)
        for name, rows in zip(names, parts):
            write_json(split_dir / folder, name, rows)
        write_json(single_dir / folder, single_name, [r for rows in parts for r in rows])
        return split_dir, single_dir
    return make


def same_rows(two_layouts, folder, names, parts, single_name, pattern, parser, rules):
    split_dir, single_dir = two_layouts(folder, names, parts, single_name)
    split = load(split_dir, folder, pattern, parser, rules)
    single = load(single_dir, folder, pattern, parser, rules)
    pd.testing.assert_frame_equal(split, single)
    return split


def samples(day, *values):
    return [{"dateTime": f"{day} {9 + i:02d}:00:00", "value": str(v)} for i, v in enumerate(values)]


# --- additive sources: the parts add up ---

@pytest.mark.parametrize("prefix, parser, rules, column", [
    ("steps", parser("steps"), S["steps"].rules, "steps"),
    ("distance", parser("distance"), S["distance"].rules, "distance"),
    ("calories", parser("calories"), S["calories"].rules, "calories_total"),
])
def test_split_day_of_intraday_sums_equals_one_file(two_layouts, prefix, parser, rules, column):
    parts = [
        samples("03/20/24", 100, 200) + samples("03/19/24", 7),
        samples("03/20/24", 300) + samples("03/21/24", 5),
    ]
    df = same_rows(two_layouts, GLOBAL,
                   [f"{prefix}-2024-03-01.json", f"{prefix}-2024-03-20.json"], parts,
                   f"{prefix}-2024-03-01.json", f"{prefix}-*.json", parser, rules)
    assert df.loc["2024-03-20", column] == 600
    # days that are not split keep their value
    assert df.loc["2024-03-19", column] == 7
    assert df.loc["2024-03-21", column] == 5


@pytest.mark.parametrize("name", ["very_active_minutes", "sedentary_minutes"])
def test_split_day_of_activity_minutes_sums(two_layouts, name):
    parts = [samples("03/20/24", 10), samples("03/20/24", 25)]
    df = same_rows(two_layouts, GLOBAL,
                   [f"{name}-2024-03-01.json", f"{name}-2024-03-20.json"], parts,
                   f"{name}-2024-03-01.json", f"{name}-*.json",
                   parser(name), S[name].rules)
    assert df[name].tolist() == [35]


def sleep_entry(day, deep, light, rem, wake, log_id=None):
    entry = {"dateOfSleep": day, "levels": {"summary": {
        "deep": {"minutes": deep}, "light": {"minutes": light},
        "rem": {"minutes": rem}, "wake": {"minutes": wake}}}}
    if log_id is not None:
        entry["logId"] = log_id
    return entry


def test_split_day_of_sleep_sessions_equals_one_file(two_layouts):
    parts = [
        [sleep_entry("2024-03-20", 60, 200, 80, 30), sleep_entry("2024-03-19", 50, 210, 70, 20)],
        [sleep_entry("2024-03-20", 10, 40, 5, 5)],     # a nap, in the next file
    ]
    df = same_rows(two_layouts, GLOBAL,
                   ["sleep-2024-03-01.json", "sleep-2024-03-20.json"], parts,
                   "sleep-2024-03-01.json", "sleep-*.json",
                   parser("sleep_stages"), S["sleep_stages"].rules)
    assert df.loc["2024-03-20"].tolist() == [70, 240, 85, 35]
    assert df.loc["2024-03-19"].tolist() == [50, 210, 70, 20]
    assert list(df.columns) == ["sleep_deep", "sleep_light", "sleep_rem", "sleep_awake"]


def test_sleep_session_present_in_two_overlapping_files_counts_once(two_layouts):
    night = sleep_entry("2024-03-20", 60, 200, 80, 30, log_id=111)
    nap = sleep_entry("2024-03-20", 10, 40, 5, 5, log_id=222)
    parts = [[night], [night, nap]]          # the second file repeats the night and adds a nap
    split_dir, _ = two_layouts(GLOBAL, ["sleep-2024-03-01.json", "sleep-2024-03-20.json"], parts,
                               "unused.json")
    df = load(split_dir, GLOBAL, "sleep-2024-0*.json", parser("sleep_stages"),
              S["sleep_stages"].rules)
    assert df.loc["2024-03-20"].tolist() == [70, 240, 85, 35]


def test_sleep_same_session_in_both_files_is_not_doubled(two_layouts):
    night = sleep_entry("2024-03-20", 60, 200, 80, 30, log_id=111)
    split_dir, _ = two_layouts(GLOBAL, ["sleep-2024-03-01.json", "sleep-2024-03-20.json"],
                               [[night], [night]], "unused.json")
    df = load(split_dir, GLOBAL, "sleep-2024-0*.json", parser("sleep_stages"),
              S["sleep_stages"].rules)
    assert df.loc["2024-03-20"].tolist() == [60, 200, 80, 30]


def session(start, minutes, calories, heart_rate=None, log_id=None):
    entry = {"startTime": start, "duration": minutes * 60000, "calories": calories}
    if log_id is not None:
        entry["logId"] = log_id
    if heart_rate:
        entry["averageHeartRate"] = heart_rate
    return entry


def test_split_day_of_exercise_equals_one_file(two_layouts):
    parts = [
        [session("03/20/24 07:00:00", 10, 100, 100)],
        [session("03/20/24 12:00:00", 30, 300, 150),
         session("03/20/24 18:00:00", 20, 50),            # no heart rate
         session("03/21/24 07:00:00", 15, 90, 90)],
    ]
    df = same_rows(two_layouts, GLOBAL, ["exercise-0.json", "exercise-100.json"], parts,
                   "exercise-0.json", "exercise-*.json", parser("exercise"), S["exercise"].rules)
    row = df.loc["2024-03-20"]
    assert (row["exercise_count"], row["exercise_duration"], row["exercise_calories"]) == (3, 60.0, 450)
    # mean over the two sessions with heart rate: (100/100 + 300/150) / 2
    assert row["exercise_aef"] == pytest.approx(1.5)
    assert df.loc["2024-03-21", "exercise_aef"] == pytest.approx(1.0)
    assert list(df.columns) == ["exercise_duration", "exercise_calories", "exercise_count", "exercise_aef"]


def test_split_day_of_exercise_aef_is_weighted_by_sessions(two_layouts):
    parts = [
        [session("03/20/24 07:00:00", 10, 100, 100)],                       # aef 1.0
        [session("03/20/24 12:00:00", 10, 300, 100),                        # aef 3.0
         session("03/20/24 18:00:00", 10, 500, 100)],                       # aef 5.0
    ]
    df = same_rows(two_layouts, GLOBAL, ["exercise-0.json", "exercise-100.json"], parts,
                   "exercise-0.json", "exercise-*.json", parser("exercise"), S["exercise"].rules)
    # mean of the three sessions is 3.0; the mean of the two files' means would be 2.5
    assert df.loc["2024-03-20", "exercise_aef"] == pytest.approx(3.0)


def test_exercise_session_present_in_two_overlapping_files_counts_once(two_layouts):
    run = session("03/20/24 07:00:00", 10, 100, 100, log_id=1)       # aef 1.0
    ride = session("03/20/24 12:00:00", 30, 300, 100, log_id=2)      # aef 3.0
    split_dir, _ = two_layouts(GLOBAL, ["exercise-0.json", "exercise-100.json"],
                               [[run], [run, ride]], "unused.json")
    df = load(split_dir, GLOBAL, "exercise-*.json", parser("exercise"),
              S["exercise"].rules)
    row = df.loc["2024-03-20"]
    assert (row["exercise_count"], row["exercise_duration"], row["exercise_calories"]) == (2, 40.0, 400)
    assert row["exercise_aef"] == pytest.approx(2.0)


def test_exercise_same_logid_with_different_values_keeps_the_last_file(two_layouts):
    first = session("03/20/24 07:00:00", 10, 100, 100, log_id=1)
    edited = session("03/20/24 07:00:00", 12, 120, 100, log_id=1)
    split_dir, _ = two_layouts(GLOBAL, ["exercise-0.json", "exercise-100.json"],
                               [[first], [edited]], "unused.json")
    df = load(split_dir, GLOBAL, "exercise-*.json", parser("exercise"),
              S["exercise"].rules)
    row = df.loc["2024-03-20"]
    assert (row["exercise_count"], row["exercise_duration"], row["exercise_calories"]) == (1, 12.0, 120)


def test_split_day_of_heart_rate_recomputes_min_max_avg(two_layouts):
    def hr(day, *bpms):
        return [{"dateTime": f"{day} 08:{i:02d}:00", "value": {"bpm": b}} for i, b in enumerate(bpms)]
    parts = [hr("03/20/24", 60, 100, 71) + hr("03/19/24", 80),
             hr("03/20/24", 55, 90, 90, 91, 70) + hr("03/21/24", 65)]
    df = same_rows(two_layouts, GLOBAL,
                   ["heart_rate-2024-03-19.json", "heart_rate-2024-03-20.json"], parts,
                   "heart_rate-2024-03-19.json", "heart_rate-*.json",
                   parser("heart_rate"), S["heart_rate"].rules)
    assert df.loc["2024-03-20"].tolist() == [55, 100, 78.4]    # 627 / 8 = 78.375
    assert list(df.columns) == ["min_bpm", "max_bpm", "avg_bpm"]


def test_split_day_of_zone_minutes_sums(tmp_path):
    folder = tmp_path / ZONES
    folder.mkdir()
    header = "timestamp,heart rate zone type\n"
    (folder / "time_in_heart_rate_zone_2024-03-01.csv").write_text(
        header + "2024-03-20T10:00:00Z,LIGHT\n2024-03-20T10:01:00Z,MODERATE\n")
    (folder / "time_in_heart_rate_zone_2024-03-20.csv").write_text(
        header + "2024-03-20T22:00:00Z,LIGHT\n2024-03-20T22:01:00Z,VIGOROUS\n")
    df = load(tmp_path, ZONES, "time_in_heart_rate_zone_*.csv", parser("active_zones"),
              S["active_zones"].rules)
    row = df.loc["2024-03-20"]
    assert (row["zone_light"], row["zone_moderate"], row["zone_vigorous"]) == (2, 1, 1)


# --- snapshot sources: the last file in name order wins ---

def test_snapshot_value_comes_from_the_last_file_in_name_order(tmp_path):
    folder = tmp_path / GLOBAL
    folder.mkdir()
    for name, bpm in (("resting_heart_rate-2024-03-20.json", 52), ("resting_heart_rate-2024-03-01.json", 61)):
        write_json(folder, name, [{"value": {"date": "03/20/24", "value": bpm}}])
    df = etl.load_collection(tmp_path, GLOBAL, "resting_heart_rate-*.json", parser("resting_heart_rate"))
    assert df["resting_bpm"].tolist() == [52]


# --- independent of the order in which files are listed ---

def build_export(root):
    folder = root / GLOBAL
    folder.mkdir(parents=True)
    write_json(folder, "steps-2024-03-01.json", samples("03/20/24", 100, 200))
    write_json(folder, "steps-2024-03-20.json", samples("03/20/24", 300) + samples("03/21/24", 40))
    write_json(folder, "calories-2024-03-01.json", samples("03/20/24", 1000, 500))
    write_json(folder, "calories-2024-03-20.json", samples("03/20/24", 700) + samples("03/21/24", 2000))
    write_json(folder, "sleep-2024-03-01.json", [sleep_entry("2024-03-20", 60, 200, 80, 30)])
    write_json(folder, "sleep-2024-03-20.json", [sleep_entry("2024-03-20", 10, 40, 5, 5)])
    write_json(folder, "exercise-0.json", [session("03/20/24 07:00:00", 10, 100, 100)])
    write_json(folder, "exercise-100.json", [session("03/20/24 12:00:00", 30, 500, 100),
                                             session("03/21/24 12:00:00", 30, 100)])
    write_json(folder, "weight-2024-03-01.json", [{"date": "03/20/24", "weight": 170.0, "bmi": 24.0}])
    write_json(folder, "weight-2024-03-20.json", [{"date": "03/20/24", "weight": 168.0, "bmi": 23.5}])


def test_merged_result_does_not_depend_on_file_listing_order(tmp_path, monkeypatch):
    build_export(tmp_path)
    expected = etl.merge_all_data(tmp_path)

    real_glob = glob.glob
    monkeypatch.setattr(etl.glob, "glob", lambda pattern: sorted(real_glob(pattern), reverse=True))
    assert etl.glob.glob(str(tmp_path / GLOBAL / "steps-*.json"))[0].endswith("steps-2024-03-20.json")
    pd.testing.assert_frame_equal(etl.merge_all_data(tmp_path), expected)

    row = expected.loc["2024-03-20"]
    assert row["steps"] == 600
    assert row["calories_total"] == 2200
    assert row["sleep_deep"] == 70
    assert (row["exercise_count"], row["exercise_calories"]) == (2, 600)
    assert row["exercise_aef"] == pytest.approx(3.0)       # (1.0 + 5.0) / 2
    assert row["weight"] == 76.2                           # 168 lbs, from the last file
    assert expected.loc["2024-03-21", "steps"] == 40


def test_merged_split_day_equals_the_same_samples_in_one_file(tmp_path):
    split_root, single_root = tmp_path / "split", tmp_path / "single"
    build_export(split_root)
    # same samples, one file per source
    folder = single_root / GLOBAL
    folder.mkdir(parents=True)
    write_json(folder, "steps-2024-03-01.json", samples("03/20/24", 100, 200, 300) + samples("03/21/24", 40))
    write_json(folder, "calories-2024-03-01.json",
               samples("03/20/24", 1000, 500, 700) + samples("03/21/24", 2000))
    write_json(folder, "sleep-2024-03-01.json", [sleep_entry("2024-03-20", 60, 200, 80, 30),
                                                 sleep_entry("2024-03-20", 10, 40, 5, 5)])
    write_json(folder, "exercise-0.json", [session("03/20/24 07:00:00", 10, 100, 100),
                                           session("03/20/24 12:00:00", 30, 500, 100),
                                           session("03/21/24 12:00:00", 30, 100)])
    write_json(folder, "weight-2024-03-01.json", [{"date": "03/20/24", "weight": 168.0, "bmi": 23.5}])
    split = etl.merge_all_data(split_root)
    single = etl.merge_all_data(single_root)
    pd.testing.assert_frame_equal(split, single, check_exact=False)
    assert not [c for c in split.columns if str(c).startswith("_")]


def test_exercise_aef_without_any_heart_rate_stays_empty(tmp_path):
    folder = tmp_path / GLOBAL
    folder.mkdir()
    write_json(folder, "exercise-0.json", [session("03/20/24 07:00:00", 10, 100)])
    write_json(folder, "exercise-100.json", [session("03/20/24 12:00:00", 10, 50)])
    df = etl.load_collection(tmp_path, GLOBAL, "exercise-*.json", parser("exercise"),
                             combine=S["exercise"].rules)
    assert df["exercise_count"].tolist() == [2]
    assert df["exercise_aef"].isna().tolist() == [True]
