"""How the command line builds the configuration of a run."""
import argparse
import json
from datetime import date
from pathlib import Path

import pytest

import config
import main
from modules.run_config import Profile

SESSION = {"dob": "1984-03-28", "gender": "female", "height": 170, "weight": 65.0,
           "data_path": "/from/session"}


def args(**overrides):
    values = dict(data_dir=None, out_dir=None, dob=None, height=None, weight=None,
                  gender=None, start_date=None, end_date=None)
    return argparse.Namespace(**{**values, **overrides})


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DATA_DIR", "START_DATE", "END_DATE", "USER_DOB", "USER_GENDER",
                 "USER_HEIGHT_CM", "USER_WEIGHT_KG"):
        monkeypatch.delenv(name, raising=False)


def write_session(folder, **overrides):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "session_config.json").write_text(json.dumps({**SESSION, **overrides}))


def test_session_config_is_read_from_the_output_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path / "default"))
    write_session(tmp_path / "default", height=150)       # must be ignored with --out-dir
    write_session(tmp_path / "chosen")
    cfg = main.build_config(args(out_dir=str(tmp_path / "chosen")))
    assert cfg.output_dir == tmp_path / "chosen"
    assert cfg.data_dir == Path("/from/session")
    assert cfg.profile == Profile(date(1984, 3, 28), "female", 170, 65.0)


def test_output_folder_defaults_to_the_client_public_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path))
    write_session(tmp_path)
    assert main.build_config(args()).output_dir == tmp_path


def test_command_line_beats_the_session_config(tmp_path):
    write_session(tmp_path)
    cfg = main.build_config(args(out_dir=str(tmp_path), data_dir="/from/cli", height=181,
                                 start_date=date(2024, 2, 1), end_date=date(2024, 3, 15)))
    assert cfg.data_dir == Path("/from/cli")
    assert cfg.profile.height_cm == 181 and cfg.profile.gender == "female"
    assert (cfg.start_date, cfg.end_date) == (date(2024, 2, 1), date(2024, 3, 15))


def test_session_config_beats_the_environment(tmp_path, monkeypatch):
    write_session(tmp_path, data_path="/from/session")
    monkeypatch.setenv("DATA_DIR", "/from/env")
    monkeypatch.setenv("USER_HEIGHT_CM", "199")
    monkeypatch.setenv("USER_GENDER", "male")
    cfg = main.build_config(args(out_dir=str(tmp_path)))
    assert cfg.data_dir == Path("/from/session") and cfg.profile.height_cm == 170


def test_environment_is_the_last_resort(tmp_path, monkeypatch):
    for name, value in (("DATA_DIR", "/from/env"), ("USER_DOB", "1990-01-01"),
                        ("USER_GENDER", "male"), ("USER_HEIGHT_CM", "180"),
                        ("USER_WEIGHT_KG", "80"), ("START_DATE", "2024-02-01")):
        monkeypatch.setenv(name, value)
    cfg = main.build_config(args(out_dir=str(tmp_path)))
    assert cfg.data_dir == Path("/from/env")
    assert cfg.profile == Profile(date(1990, 1, 1), "male", 180, 80.0)
    assert cfg.start_date == date(2024, 2, 1) and cfg.end_date is None


def test_incomplete_biometrics_give_no_config(tmp_path):
    write_session(tmp_path, weight=None)
    assert main.build_config(args(out_dir=str(tmp_path))) is None


def test_out_of_range_biometrics_are_an_error(tmp_path):
    write_session(tmp_path, height=400)
    with pytest.raises(ValueError, match="height"):
        main.build_config(args(out_dir=str(tmp_path)))
