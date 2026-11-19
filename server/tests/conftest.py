"""Shared helpers for the parser, metric and ETL tests.

Everything that touches the global ``config`` module or lists the parsers is
kept here, so a later refactor of the configuration or of the parsers has a
single place to adapt.
"""
from pathlib import Path

import pytest

import config
from modules import etl, metrics, parsers

FIXTURES = Path(__file__).parent / "fixtures"

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
def configure_etl(monkeypatch):
    """Point the ETL at a data folder and an optional date range."""
    def _configure(data_dir, start=None, end=None):
        monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
        monkeypatch.setattr(config, "START_DATE", start)
        monkeypatch.setattr(config, "END_DATE", end)
    return _configure


@pytest.fixture
def set_profile(monkeypatch):
    """Set the user profile the metabolic metrics read (empty value = not set)."""
    def _set(gender="male", dob="1984-03-28", height=180, weight=75.0):
        monkeypatch.setattr(config, "USER_GENDER", gender)
        monkeypatch.setattr(config, "USER_DOB", dob)
        monkeypatch.setattr(config, "USER_HEIGHT_CM", height)
        monkeypatch.setattr(config, "USER_WEIGHT_KG", weight)
    return _set


@pytest.fixture
def run_pipeline(configure_etl, set_profile):
    """Merge the export and apply the three metric steps, like main.py and api.py.

    NOTE: this repeats the call order used by main.py and api.py. Once the
    pipeline refactor provides one shared pipeline function, replace the body
    of this fixture with a call to it.
    """
    def _run(data_dir, start=None, end=None):
        configure_etl(data_dir, start, end)
        set_profile()
        df = etl.merge_all_data()
        df = metrics.calculate_readiness(df)
        df = metrics.calculate_metabolic_metrics(df)
        return metrics.calculate_advanced_metrics(df)
    return _run
