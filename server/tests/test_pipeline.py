"""run_pipeline: progress, outputs, atomic writes, and the case without data."""
import json
import os
import time
from datetime import date

import pytest

from modules import etl, pipeline
from modules.pipeline import NoDataError

OUTPUTS = ("fitbit_analysis.csv", "dashboard_data.json")


def snapshot(folder):
    return {p.name: p.read_bytes() for p in sorted(folder.iterdir())}


@pytest.fixture
def previous_run(make_config, export_dir, tmp_path):
    """A finished run in tmp_path/output; returns the output folder and its files."""
    cfg = make_config(export_dir)
    pipeline.run_pipeline(cfg)
    return cfg.output_dir, snapshot(cfg.output_dir)


def test_writes_the_two_outputs_and_nothing_else(make_config, export_dir):
    cfg = make_config(export_dir)
    result = pipeline.run_pipeline(cfg)
    assert sorted(p.name for p in cfg.output_dir.iterdir()) == sorted(OUTPUTS)
    rows = json.loads((cfg.output_dir / "dashboard_data.json").read_text())
    assert [r["date"] for r in rows] == [d.strftime("%Y-%m-%d") for d in result.df.index]


def test_creates_a_missing_output_folder(make_config, export_dir, tmp_path):
    cfg = make_config(export_dir, output_dir=tmp_path / "a" / "b")
    pipeline.run_pipeline(cfg)
    assert (cfg.output_dir / "dashboard_data.json").exists()


def test_progress_steps_and_order(make_config, export_dir):
    seen = []
    pipeline.run_pipeline(make_config(export_dir), lambda pct, msg: seen.append((pct, msg)))
    percentages = [pct for pct, _ in seen]
    assert percentages == sorted(percentages)
    assert seen[0] == (10, "Loading and merging data files")
    assert (65, "Merging datasets") in seen
    assert seen[-7:] == [
        (65, "Merging datasets"),
        (70, "Calculating readiness metrics"),
        (75, "Calculating metabolic metrics"),
        (80, "Calculating advanced metrics"),
        (90, "Exporting analysis CSV"),
        (95, "Exporting dashboard JSON"),
        (100, "Complete"),
    ]


def test_runs_without_a_progress_callback(make_config, export_dir):
    assert len(pipeline.run_pipeline(make_config(export_dir)).df) == 7


def test_date_range_and_profile_come_from_the_config(make_config, export_dir):
    cfg = make_config(export_dir, start=date(2024, 3, 30), end=date(2024, 4, 1))
    assert len(pipeline.run_pipeline(cfg).df) == 3
    no_profile = pipeline.run_pipeline(make_config(export_dir, profile=None)).df
    assert (no_profile["bmr"] == 0).all() and (no_profile["active_calories"] == 0).all()


def test_warnings_are_returned_and_collected_in_the_callers_list(make_config, tmp_path):
    data = tmp_path / "data"
    folder = data / "Global Export Data"
    folder.mkdir(parents=True)
    rows = [{"dateTime": f"01/{d:02d}/24 12:00:00", "value": "10"} for d in range(1, 4)]
    (folder / "calories-2024-01-01.json").write_text(json.dumps(rows))
    (folder / "steps-2024-01-01.json").write_text("{ not json")
    cfg = make_config(data)
    result = pipeline.run_pipeline(cfg)
    assert [w["file"] for w in result.warnings] == ["steps-2024-01-01.json"]
    assert not (cfg.output_dir / "etl_warnings.json").exists()
    mine = []
    assert pipeline.run_pipeline(cfg, warnings=mine).warnings is mine
    assert [w["file"] for w in mine] == ["steps-2024-01-01.json"]


def test_warnings_found_before_a_failure_stay_in_the_callers_list(make_config, tmp_path, monkeypatch):
    data = tmp_path / "data"
    folder = data / "Global Export Data"
    folder.mkdir(parents=True)
    rows = [{"dateTime": f"01/{d:02d}/24 12:00:00", "value": "10"} for d in range(1, 4)]
    (folder / "calories-2024-01-01.json").write_text(json.dumps(rows))
    (folder / "steps-2024-01-01.json").write_text("{ not json")

    def boom(*args, **kwargs):
        raise RuntimeError("metrics failed")

    monkeypatch.setattr(pipeline.metrics, "calculate_readiness", boom)
    mine = []
    with pytest.raises(RuntimeError):
        pipeline.run_pipeline(make_config(data), warnings=mine)
    assert [w["file"] for w in mine] == ["steps-2024-01-01.json"]


# --- no data: the outputs of the previous run stay as they are ---

def test_no_data_raises_and_creates_no_output(make_config, tmp_path):
    (tmp_path / "empty").mkdir()
    cfg = make_config(tmp_path / "empty")
    with pytest.raises(NoDataError) as raised:
        pipeline.run_pipeline(cfg)
    assert raised.value.warnings == []
    assert not cfg.output_dir.exists()


def test_no_data_leaves_previous_outputs(previous_run, make_config, tmp_path):
    output_dir, before = previous_run
    unreadable = tmp_path / "bad"
    (unreadable / "Global Export Data").mkdir(parents=True)
    (unreadable / "Global Export Data" / "steps-2024-01-01.json").write_text("{ not json")
    with pytest.raises(NoDataError) as raised:
        pipeline.run_pipeline(make_config(unreadable, output_dir=output_dir))
    assert [w["file"] for w in raised.value.warnings] == ["steps-2024-01-01.json"]
    assert snapshot(output_dir) == before


def test_date_range_without_rows_is_not_an_error(make_config, export_dir):
    cfg = make_config(export_dir, start=date(2030, 1, 1))
    assert pipeline.run_pipeline(cfg).df.empty


# --- atomic writes ---

def test_failed_export_leaves_previous_outputs_and_no_temp_files(previous_run, make_config,
                                                                 export_dir, monkeypatch):
    output_dir, before = previous_run

    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(etl, "export_to_json", boom)
    with pytest.raises(RuntimeError):
        pipeline.run_pipeline(make_config(export_dir, start=date(2024, 3, 30), output_dir=output_dir))
    assert snapshot(output_dir) == before


def test_atomic_write_leaves_no_temp_files(previous_run):
    output_dir, _ = previous_run
    assert not [p for p in output_dir.iterdir() if ".tmp-" in p.name]


def flaky_replace(monkeypatch, failures):
    real = os.replace
    calls = []

    def replace(src, dst):
        calls.append(str(dst))
        if len(calls) <= failures:
            raise PermissionError("file in use")
        return real(src, dst)

    monkeypatch.setattr(pipeline.os, "replace", replace)
    monkeypatch.setattr(pipeline.time, "sleep", lambda _s: None)
    return calls


def test_replace_is_retried_after_a_sharing_error(make_config, export_dir, monkeypatch):
    calls = flaky_replace(monkeypatch, failures=2)
    cfg = make_config(export_dir)
    pipeline.run_pipeline(cfg)
    assert len(calls) == 2 + len(OUTPUTS)
    assert sorted(p.name for p in cfg.output_dir.iterdir()) == sorted(OUTPUTS)


def test_replace_gives_up_after_five_attempts(previous_run, make_config, export_dir, monkeypatch):
    output_dir, before = previous_run
    calls = flaky_replace(monkeypatch, failures=99)
    with pytest.raises(PermissionError):
        pipeline.run_pipeline(make_config(export_dir, start=date(2024, 3, 30), output_dir=output_dir))
    assert len(calls) == pipeline.REPLACE_ATTEMPTS
    assert snapshot(output_dir) == before


def test_stale_temp_files_of_an_interrupted_run_are_removed(make_config, export_dir, tmp_path):
    cfg = make_config(export_dir)
    cfg.output_dir.mkdir()
    stale = cfg.output_dir / "dashboard_data.json.tmp-1234"
    fresh = cfg.output_dir / "fitbit_analysis.csv.tmp-5678"
    for path in (stale, fresh):
        path.write_text("partial")
    old = time.time() - pipeline.STALE_TMP_SECONDS - 60
    os.utime(stale, (old, old))
    pipeline.run_pipeline(cfg)
    assert not stale.exists()
    assert fresh.exists()           # may belong to a run that is still writing
