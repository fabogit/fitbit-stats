"""Unreadable files are reported, not skipped silently."""
import json

import pandas as pd
import pytest

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


def test_age_of_invalid_dob_is_zero():
    assert briefing.calculate_age("not a date", pd.Timestamp("2024-01-01")) == 0
