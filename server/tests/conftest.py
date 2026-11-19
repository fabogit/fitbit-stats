"""Shared helpers for the parser, metric and ETL tests.

Everything that lists the parsers or builds the default profile is kept
here, so a later refactor of the parsers has a single place to adapt.
"""
from datetime import date
from pathlib import Path

import pytest

import api
from jobs import JobManager
from modules import load_plan, parsers, pipeline
from modules.run_config import EtlConfig, Profile

FIXTURES = Path(__file__).parent / "fixtures"

# The profile the golden values of the tests are worked out with.
DEFAULT_PROFILE = Profile(dob=date(1984, 3, 28), gender="male", height_cm=180, weight_kg=75.0)

# One entry per source: key -> parser function. Adapt this table, not the
# individual tests, if the parsers are ever reorganised.
# The sources of the load plan, by key (their combine rules are S[key].rules).
S = load_plan.SOURCES

PARSERS = {
    "resting_heart_rate": parsers.parse_resting_heart_rate,
    "heart_rate": parsers.parse_heart_rate_intraday_summary,
    "steps": parsers.parse_steps_json,
    "distance": parsers.parse_distance_json,
    "exercise": parsers.parse_exercise_json,
    "weight": parsers.parse_weight,
    "calories": parsers.parse_calories_intraday,
    "sleep_score": parsers.parse_sleep_score_csv,
    "sleep_json": parsers.parse_sleep_json_detailed,
    "spo2": parsers.parse_spo2_csv,
    "hrv": parsers.parse_hrv_csv,
    "stress": parsers.parse_stress_csv,
    "simple_activity": parsers.parse_simple_activity_json,
    "acwr": parsers.parse_acwr_csv,
    "vo2max": parsers.parse_vo2max_csv,
    "readiness": parsers.parse_readiness_csv,
    "respiratory_rate": parsers.parse_respiratory_rate_csv,
    "skin_temperature": parsers.parse_skin_temperature_csv,
    "active_zones": parsers.parse_active_zones_csv,
}


@pytest.fixture
def parser_table():
    return PARSERS


@pytest.fixture
def parse():
    """parse("steps", path) -> the DataFrame (or None) the parser returns."""
    def _parse(key, path):
        return PARSERS[key](str(path))
    return _parse


@pytest.fixture
def export_dir():
    """Root of the small synthetic export (same folder layout as a real one)."""
    return FIXTURES / "export"


@pytest.fixture
def make_profile():
    """make_profile(gender=..., height=...) -> a Profile, DEFAULT_PROFILE with overrides."""
    def _make(gender=DEFAULT_PROFILE.gender, dob=DEFAULT_PROFILE.dob,
              height=DEFAULT_PROFILE.height_cm, weight=DEFAULT_PROFILE.weight_kg):
        return Profile(dob=dob, gender=gender, height_cm=height, weight_kg=weight)
    return _make


@pytest.fixture
def make_config(tmp_path):
    """make_config(data_dir, start=None, end=None, profile=DEFAULT_PROFILE) -> an EtlConfig.

    Outputs go to a folder of the test's tmp_path, never to the default folder.
    """
    def _make(data_dir, start=None, end=None, profile=DEFAULT_PROFILE, output_dir=None):
        return EtlConfig(data_dir=Path(data_dir), output_dir=Path(output_dir or tmp_path / "output"),
                         profile=profile, start_date=start, end_date=end)
    return _make


@pytest.fixture
def run_pipeline(make_config):
    """Run the pipeline on an export and return the final DataFrame."""
    def _run(data_dir, start=None, end=None):
        return pipeline.run_pipeline(make_config(data_dir, start, end)).df
    return _run


@pytest.fixture(autouse=True)
def fresh_job_manager(monkeypatch):
    """Every test gets its own job manager, so no run or status leaks into the next test."""
    job = JobManager(api._run_pipeline, api._last_run_path, on_change=api.manager.notify)
    monkeypatch.setattr(api, "job_manager", job)
    yield job
    job.join(10)
