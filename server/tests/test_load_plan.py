"""Structural checks on the server modules and on the ETL load plan."""
import ast
from pathlib import Path

import pandas as pd
import pytest

from modules import etl, load_plan, parsers
from modules.sources import Agg, FromSessions, Ratio, Special

SERVER = Path(__file__).resolve().parent.parent

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
            declared = [c.name for c in s.columns if not c.name.startswith("zone_")]
            assert set(declared) <= set(df.columns), (s.key, f.name)


def test_combine_rejects_an_unknown_rule():
    df = pd.DataFrame({"x": [1, 2]}, index=pd.to_datetime(["2024-03-01"] * 2))
    with pytest.raises(ValueError):
        etl._combine_duplicate_days(df, {"x": "sum"})


def test_no_inplace_in_the_server_modules():
    for path in sorted((SERVER / "modules").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.keyword):
                assert node.arg != "inplace", f"{path.name}:{node.value.lineno}"
