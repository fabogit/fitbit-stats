"""Shared helpers for the parser, metric and ETL tests.

Everything that lists the parsers or builds the default profile is kept
here, so a later refactor of the parsers has a single place to adapt.
"""
import fnmatch
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

# One entry per test key: the source(s) of the load plan it reads. Adapt this
# table, not the individual tests, if the parsers are ever reorganised.
S = load_plan.SOURCES
PARSERS = {
    "resting_heart_rate": S["resting_heart_rate"],
    "heart_rate": S["heart_rate"],
    "steps": S["steps"],
    "distance": S["distance"],
    "exercise": S["exercise"],
    "weight": S["weight"],
    "calories": S["calories"],
    "sleep_score": S["sleep_score"],
    "sleep_json": S["sleep_stages"],
    "spo2": S["spo2"],
    "hrv": S["hrv"],
    "stress": S["stress"],
    # four sources with the same format: the file name picks one
    "simple_activity": (S["very_active_minutes"], S["moderately_active_minutes"],
                        S["lightly_active_minutes"], S["sedentary_minutes"]),
    "acwr": S["acwr"],
    "vo2max": S["vo2max"],
    "readiness": S["readiness"],
    "respiratory_rate": S["respiratory_rate"],
    "skin_temperature": S["skin_temperature"],
    "active_zones": S["active_zones"],
}


def source_for(key, path=None):
    entry = PARSERS[key]
    if isinstance(entry, tuple):
        return next(s for s in entry if fnmatch.fnmatch(Path(path).name, s.pattern))
    return entry


def parser(key):
    """The parser of a source, as the ETL calls it (helper columns included)."""
    return parsers.parser_for(S[key])


@pytest.fixture
def parser_table():
    return PARSERS


@pytest.fixture
def parse():
    """parse("steps", path) -> the DataFrame (or None) of the source, without helper columns."""
    def _parse(key, path):
        return parsers.drop_helpers(parsers.parse(source_for(key, path), str(path)))
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
