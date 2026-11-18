import json

import pytest

import config
from modules import etl


@pytest.fixture(autouse=True)
def _restore_config():
    saved = (config.DATA_DIR, config.START_DATE, config.END_DATE)
    config.START_DATE = None
    config.END_DATE = None
    yield
    config.DATA_DIR, config.START_DATE, config.END_DATE = saved


def write_calories(data_dir, file_date, days):
    """Write one synthetic monthly calories file covering the given days."""
    folder = data_dir / "Global Export Data"
    folder.mkdir(parents=True, exist_ok=True)
    rows = [{"dateTime": f"{d} 12:00:00", "value": "10"} for d in days]
    path = folder / f"calories-{file_date}.json"
    path.write_text(json.dumps(rows))


def merged_dates(data_dir):
    config.DATA_DIR = str(data_dir)
    df = etl.merge_all_data()
    return [d.strftime("%Y-%m-%d") for d in df.index]


def test_days_after_last_monthly_file_start_are_kept(tmp_path):
    days = [f"03/{n:02d}/24" for n in (1, 2, 15, 31)]
    write_calories(tmp_path, "2024-03-01", days)
    assert merged_dates(tmp_path) == [
        "2024-03-01", "2024-03-02", "2024-03-15", "2024-03-31"]


def test_multi_month_range_ends_at_last_day_with_data(tmp_path):
    write_calories(tmp_path, "2024-03-01", ["03/01/24", "03/20/24"])
    write_calories(tmp_path, "2024-04-01", ["04/01/24", "04/28/24"])
    dates = merged_dates(tmp_path)
    assert dates[0] == "2024-03-01"
    assert dates[-1] == "2024-04-28"


def test_two_runs_in_one_process_cover_their_own_range(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_calories(first, "2024-03-01", ["03/01/24", "03/10/24"])
    write_calories(second, "2024-06-01", ["06/01/24", "06/25/24"])
    assert merged_dates(first)[-1] == "2024-03-10"
    assert merged_dates(second) == ["2024-06-01", "2024-06-25"]


def test_config_dates_unchanged_after_run(tmp_path):
    write_calories(tmp_path, "2024-03-01", ["03/01/24", "03/10/24"])
    merged_dates(tmp_path)
    assert config.START_DATE is None
    assert config.END_DATE is None


def test_explicit_dates_still_filter(tmp_path):
    write_calories(tmp_path, "2024-03-01", ["03/01/24", "03/10/24", "03/20/24"])
    config.START_DATE = "2024-03-05"
    config.END_DATE = "2024-03-15"
    assert merged_dates(tmp_path) == ["2024-03-10"]
    assert config.START_DATE == "2024-03-05"
