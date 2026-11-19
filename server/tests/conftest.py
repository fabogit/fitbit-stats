"""Shared helpers for the parser, metric and ETL tests.

Everything that lists the parsers or builds the default profile is kept
here, so a later refactor of the parsers has a single place to adapt.
"""
from datetime import date
from pathlib import Path

import pytest

from modules import etl, metrics, parsers
from modules.run_config import Profile

FIXTURES = Path(__file__).parent / "fixtures"

# The profile the golden values of the tests are worked out with.
DEFAULT_PROFILE = Profile(dob=date(1984, 3, 28), gender="male", height_cm=180, weight_kg=75.0)

# One entry per source: key -> parser function. Adapt this table, not the
# individual tests, if the parsers are ever reorganised.
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
def run_pipeline():
    """Merge the export and apply the three metric steps, like main.py and api.py.

    NOTE: this repeats the call order used by main.py and api.py. Once the
    pipeline refactor provides one shared pipeline function, replace the body
    of this fixture with a call to it.
    """
    def _run(data_dir, start=None, end=None):
        df = etl.merge_all_data(data_dir, start, end)
        df = metrics.calculate_readiness(df)
        df = metrics.calculate_metabolic_metrics(df, DEFAULT_PROFILE)
        return metrics.calculate_advanced_metrics(df)
    return _run
