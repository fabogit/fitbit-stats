import filecmp
import importlib.util
from pathlib import Path

import pytest

import config
from modules import etl

GENERATOR = Path(__file__).resolve().parents[2] / "scripts" / "generate_sample_export.py"
DAYS = 12


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_sample_export", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _restore_config():
    saved = (config.DATA_DIR, config.START_DATE, config.END_DATE)
    config.START_DATE = None
    config.END_DATE = None
    yield
    config.DATA_DIR, config.START_DATE, config.END_DATE = saved


def files_under(root):
    return sorted(p.relative_to(root) for p in root.rglob("*") if p.is_file())


def test_generator_is_deterministic(tmp_path):
    gen = load_generator()
    a, b = tmp_path / "a", tmp_path / "b"
    gen.generate(a, days=DAYS)
    gen.generate(b, days=DAYS)
    names = files_under(a)
    assert names and names == files_under(b)
    match, mismatch, errors = filecmp.cmpfiles(a, b, names, shallow=False)
    assert not mismatch and not errors


def test_different_seed_changes_output(tmp_path):
    gen = load_generator()
    gen.generate(tmp_path / "a", days=DAYS, seed=1)
    gen.generate(tmp_path / "b", days=DAYS, seed=2)
    names = files_under(tmp_path / "a")
    _, mismatch, _ = filecmp.cmpfiles(tmp_path / "a", tmp_path / "b", names, shallow=False)
    assert mismatch


def test_etl_loads_generated_export(tmp_path):
    gen = load_generator()
    gen.generate(tmp_path, days=DAYS)
    config.DATA_DIR = str(tmp_path)
    df = etl.merge_all_data()
    assert df is not None
    assert len(df) == DAYS
    assert df.index.min().strftime("%Y-%m-%d") == "2024-01-01"
    assert df.index.max().strftime("%Y-%m-%d") == "2024-01-12"
    for col in ("resting_bpm", "avg_bpm", "steps", "calories_total", "sleep_deep", "overall_score",
                "spo2_avg", "rmssd", "stress_score", "very_active_minutes", "acwr_ratio", "vo2max",
                "readiness_score", "respiratory_rate", "temperature_variation"):
        assert col in df.columns, col
        assert (df[col].fillna(0) != 0).any(), col
    # Zone column names depend on the parser, so only check that some are loaded.
    zone_cols = [c for c in df.columns if c.startswith("zone_")]
    assert zone_cols
    assert any((df[c].fillna(0) != 0).any() for c in zone_cols)
