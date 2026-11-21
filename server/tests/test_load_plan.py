"""Structural checks on the server modules and on the ETL load plan."""
import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from conftest import S, parser
from modules import etl, load_plan, parsers
from modules.sources import Agg, CsvDaily, FromSessions, JsonDaily, Ratio, Special

SERVER = Path(__file__).resolve().parent.parent
ZONES = "Physical Activity_GoogleData"

# The 22 progress messages, in order (the percentages follow from the count).
LABELS = ["Resting heart rate", "Heart rate intraday", "Steps", "Distance", "Exercise sessions",
          "Weight", "Calories", "Sleep scores", "Sleep stages", "SpO2", "HRV", "Stress scores",
          "Active minutes", "Moderate activity", "Light activity", "Sedentary minutes", "ACWR",
          "VO2 Max", "Readiness", "Respiratory rate", "Skin temperature", "HR zones"]


def test_progress_messages_and_percentages_follow_the_plan(tmp_path):
    seen = []
    etl.merge_all_data(tmp_path, progress_callback=lambda pct, msg: seen.append((pct, msg)))
    loading = [(p, m) for p, m in seen if m.startswith("Loading ")]
    assert [m.removeprefix("Loading ") for _, m in loading] == LABELS
    assert [p for p, _ in loading] == [10 + int(i / 22 * 55) for i in range(22)]


def test_plan_entries_are_unique_and_well_formed():
    plan = load_plan.LOAD_PLAN
    assert len({s.key for s in plan}) == len(plan)
    assert len({(s.folder, s.pattern) for s in plan}) == len(plan)
    for s in plan:
        names = {c.name for c in s.columns}
        assert len(names) == len(s.columns), s.key
        if isinstance(s.reader, (JsonDaily, CsvDaily)):
            assert s.reader.per_day in (None, Agg.SUM, Agg.MEAN, Agg.MAX, Agg.FIRST), s.key
        for c in s.columns:
            if isinstance(c.combine, FromSessions):
                assert "_sessions" in names, s.key
            if isinstance(c.combine, Ratio):
                assert {c.combine.numerator, c.combine.denominator} <= names, s.key
            if isinstance(c.combine, Agg):
                assert c.combine in (Agg.SUM, Agg.MIN, Agg.MAX, Agg.LAST), s.key
        assert s.parallel is False or isinstance(s.reader, Special), s.key
    assert load_plan.SOURCES == {s.key: s for s in plan}


def test_parsers_give_the_declared_columns_on_the_fixture_export(export_dir):
    for s in load_plan.LOAD_PLAN:
        for f in sorted((export_dir / s.folder).glob(s.pattern)):
            df = parsers.parser_for(s)(str(f))
            if df is None:
                continue
            extra = [c for c in df.columns if c not in {c.name for c in s.columns}]
            assert not extra or s.other_columns is not Agg.LAST, (s.key, extra)
            required = [c.name for c in s.columns if c.required and not c.name.startswith("zone_")]
            assert set(required) <= set(df.columns), (s.key, f.name)


def test_combine_rejects_an_unknown_rule():
    df = pd.DataFrame({"x": [1, 2]}, index=pd.to_datetime(["2024-03-01"] * 2))
    with pytest.raises(ValueError):
        etl._combine_duplicate_days(df, {"x": "sum"})


def test_no_inplace_in_the_server_modules():
    for path in sorted((SERVER / "modules").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.keyword):
                assert node.arg != "inplace", f"{path.name}:{node.value.lineno}"


# --- optional columns are optional ---

def test_weight_without_bmi_keeps_the_weight(tmp_path):
    f = tmp_path / "weight-2024-03-01.json"
    f.write_text(json.dumps([{"date": "03/01/24", "weight": 176.4}]))
    df = parsers.parse(S["weight"], str(f))
    assert list(df.columns) == ["weight"]
    assert df["weight"].tolist() == [80.0]


def test_weight_and_bmi_written_as_text_are_read_as_numbers(tmp_path):
    f = tmp_path / "weight-2024-03-01.json"
    f.write_text(json.dumps([{"date": "03/01/24", "weight": "176.4", "bmi": "24.5"}]))
    df = parsers.parse(S["weight"], str(f))
    assert df.loc["2024-03-01"].tolist() == [80.0, 24.5]


def test_heart_rate_sample_whose_value_is_not_an_object_is_skipped(tmp_path):
    f = tmp_path / "heart_rate-2024-03-01.json"
    f.write_text(json.dumps([{"dateTime": "03/01/24 08:00:00", "value": {"bpm": 60}},
                             {"dateTime": "03/01/24 08:00:05", "value": 0},
                             {"dateTime": "03/01/24 08:00:10", "value": {"bpm": 80}}]))
    df = parsers.drop_helpers(parsers.parse(S["heart_rate"], str(f)))
    assert df.loc["2024-03-01"].tolist() == [60, 80, 70.0]


def test_resting_heart_rate_entry_whose_value_is_not_an_object_is_skipped(tmp_path):
    f = tmp_path / "resting_heart_rate-2024-03-01.json"
    f.write_text(json.dumps([{"value": 5}, {"value": {"date": "03/01/24", "value": 55}}]))
    assert parsers.parse(S["resting_heart_rate"], str(f))["resting_bpm"].tolist() == [55]


def test_unknown_zone_split_across_files_is_summed(tmp_path):
    folder = tmp_path / ZONES
    folder.mkdir()
    header = "timestamp,heart rate zone type\n"
    (folder / "time_in_heart_rate_zone_2024-03-01.csv").write_text(header + "2024-03-20T10:00:00Z,NEW ZONE\n")
    (folder / "time_in_heart_rate_zone_2024-03-20.csv").write_text(header + "2024-03-20T22:00:00Z,NEW ZONE\n")
    assert etl.load_source(tmp_path, S["active_zones"])["zone_new_zone"].tolist() == [2]


@pytest.mark.parametrize("name, content, reason", [
    ("Daily Heart Rate Variability Summary - 1.csv", "timestamp,other\n2024-03-01T00:00:00,1\n",
     "MissingColumns: missing column(s): rmssd"),
    ("Daily Heart Rate Variability Summary - 2.csv", "day,rmssd\n2024-03-01T00:00:00,1\n",
     "MissingColumns: missing column(s): timestamp"),
])
def test_a_file_without_a_required_column_is_reported_as_a_warning(tmp_path, name, content, reason):
    folder = tmp_path / "Heart Rate Variability"
    folder.mkdir()
    (folder / name).write_text(content)
    warnings = []
    etl.load_source(tmp_path, S["hrv"], warnings)
    assert warnings == [{"file": name, "reason": reason}]


def test_exercise_efficiency_is_empty_when_no_session_has_a_heart_rate(tmp_path):
    f = tmp_path / "exercise-0.json"
    f.write_text(json.dumps([{"logId": 1, "startTime": "03/20/24 07:00:00",
                              "duration": 600000, "calories": 100}]))
    df = parsers.parse(S["exercise"], str(f))
    assert df["exercise_aef"].isna().tolist() == [True]
    assert df["exercise_count"].tolist() == [1]


def test_stress_rows_without_data_are_dropped(tmp_path):
    f = tmp_path / "Stress Score.csv"
    f.write_text("DATE,STRESS_SCORE,STATUS\n2024-03-01T00:00:00,50,NO_DATA\n2024-03-02T00:00:00,60,READY\n")
    assert parsers.parse(S["stress"], str(f))["stress_score"].tolist() == [60]


def test_csv_headers_with_spaces_are_cleaned_for_every_csv_source(tmp_path):
    f = tmp_path / "daily_readiness.csv"
    f.write_text("timestamp, score \n2024-03-01T00:00:00,70\n")
    assert parsers.parse(S["readiness"], str(f))["readiness_score"].tolist() == [70]


@pytest.mark.parametrize("key", ["steps", "calories", "weight", "sedentary_minutes", "spo2", "hrv"])
def test_a_simple_source_needs_no_function_of_its_own(key):
    assert not isinstance(S[key].reader, Special)
    assert callable(parser(key))
