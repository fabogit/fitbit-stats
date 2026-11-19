"""A run does not depend on the runs before it, and the ETL reads no global configuration."""
import ast
import filecmp
import importlib.util
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from modules import pipeline
from modules.run_config import EtlConfig, Profile

SERVER = Path(__file__).resolve().parents[1]
GENERATOR = SERVER.parent / "scripts" / "generate_sample_export.py"
OUTPUTS = ("dashboard_data.json", "fitbit_analysis.csv", "etl_warnings.json")


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_sample_export", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Two runs that differ in everything a run is configured with.
RUN_A = dict(seed=7, days=70, start=date(2024, 2, 1),
             range=(date(2024, 2, 10), date(2024, 3, 20)),
             profile=Profile(date(1985, 5, 17), "female", 165, 61.5))
RUN_B = dict(seed=42, days=45, start=date(2024, 1, 1), range=(None, None),
             profile=Profile(date(1990, 1, 1), "male", 180, 80.0))


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    gen = load_generator()
    root = tmp_path_factory.mktemp("exports")
    paths = {}
    for name, run in (("A", RUN_A), ("B", RUN_B)):
        paths[name] = gen.generate(root / name, days=run["days"], start=run["start"], seed=run["seed"])
    return paths


def run_in_process(name, data_dir, out_dir):
    run = {"A": RUN_A, "B": RUN_B}[name]
    start, end = run["range"]
    pipeline.run_pipeline(EtlConfig(data_dir=data_dir, output_dir=out_dir, profile=run["profile"],
                                    start_date=start, end_date=end))


def run_in_fresh_process(name, data_dir, out_dir):
    run = {"A": RUN_A, "B": RUN_B}[name]
    p, (start, end) = run["profile"], run["range"]
    cmd = [sys.executable, "main.py", "--data-dir", str(data_dir), "--out-dir", str(out_dir),
           "--dob", p.dob.isoformat(), "--height", str(p.height_cm), "--weight", str(p.weight_kg),
           "--gender", p.gender]
    if start:
        cmd += ["--start-date", start.isoformat()]
    if end:
        cmd += ["--end-date", end.isoformat()]
    done = subprocess.run(cmd, cwd=SERVER, capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr


@pytest.mark.parametrize("order", ["AB", "BA"])
def test_sequential_runs_in_one_process_match_fresh_processes(exports, tmp_path, order):
    for step, name in enumerate(order):
        run_in_process(name, exports[name], tmp_path / f"same_process_{step}")
    last = order[-1]
    run_in_fresh_process(last, exports[last], tmp_path / "fresh")
    same_process = tmp_path / f"same_process_{len(order) - 1}"
    for name in OUTPUTS:
        assert filecmp.cmp(same_process / name, tmp_path / "fresh" / name, shallow=False), name


def test_the_two_runs_really_differ(exports, tmp_path):
    # Guards the test above: if both runs gave the same output it would prove nothing.
    run_in_process("A", exports["A"], tmp_path / "a")
    run_in_process("B", exports["B"], tmp_path / "b")
    assert not filecmp.cmp(tmp_path / "a" / "dashboard_data.json",
                           tmp_path / "b" / "dashboard_data.json", shallow=False)


# --- the ETL reads no global configuration ---

def imports_config(source):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "config" for a in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "config":
            return True
        if isinstance(node, ast.ImportFrom) and node.module is None and \
                any(a.name == "config" for a in node.names):
            return True
    return False


@pytest.mark.parametrize("module", ["etl", "metrics", "parsers", "pipeline", "run_config"])
def test_no_config_globals(module):
    assert not imports_config((SERVER / "modules" / f"{module}.py").read_text())


@pytest.mark.parametrize("source", [
    "import config", "import config as c", "from config import CLIENT_PUBLIC_DIR",
    "from . import config", "def f():\n    import config"])
def test_import_check_detects_config(source):
    assert imports_config(source)


def test_import_check_ignores_other_modules():
    assert not imports_config("import configparser\nfrom modules import etl\nconfig_path = 1")
