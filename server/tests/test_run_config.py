"""EtlConfig, Profile and the session-config helpers."""
import dataclasses
import json
from datetime import date
from pathlib import Path

import pytest

from modules import run_config
from modules.run_config import EtlConfig, Profile, profile_from_mapping, read_session_config

TODAY = date(2026, 6, 15)
VALID = {"dob": "1984-03-28", "gender": "male", "height": 180, "weight": 75.5}


def test_config_and_profile_are_immutable():
    cfg = EtlConfig(Path("in"), Path("out"), None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.start_date = date(2024, 1, 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        Profile(date(1984, 3, 28), "male", 180, 75.0).height_cm = 170


def test_config_defaults_to_no_date_range():
    cfg = EtlConfig(Path("in"), Path("out"), None)
    assert cfg.start_date is None and cfg.end_date is None


def test_profile_from_a_session_config_mapping():
    assert profile_from_mapping(VALID, TODAY) == Profile(date(1984, 3, 28), "male", 180, 75.5)


def test_profile_accepts_a_date_object_and_a_whole_float_height():
    p = profile_from_mapping({**VALID, "dob": date(1984, 3, 28), "height": 180.0}, TODAY)
    assert p.dob == date(1984, 3, 28) and p.height_cm == 180 and isinstance(p.height_cm, int)


@pytest.mark.parametrize("missing", ["dob", "gender", "height", "weight"])
@pytest.mark.parametrize("empty", [None, "", 0])
def test_incomplete_profile_is_none(missing, empty):
    assert profile_from_mapping({**VALID, missing: empty}, TODAY) is None
    assert profile_from_mapping({k: v for k, v in VALID.items() if k != missing}, TODAY) is None


def test_empty_mapping_is_no_profile():
    assert profile_from_mapping({}, TODAY) is None


@pytest.mark.parametrize("change, text", [
    ({"dob": "28/03/1984"}, "dob"),
    ({"dob": "2026-06-14"}, "age"),
    ({"dob": "1900-01-01"}, "age"),
    ({"gender": "other"}, "gender"),
    ({"height": 49}, "height"),
    ({"height": 251}, "height"),
    ({"height": 180.5}, "height"),
    ({"height": "tall"}, "height"),
    ({"weight": 19.9}, "weight"),
    ({"weight": 300.1}, "weight"),
    ({"weight": "heavy"}, "weight"),
])
def test_profile_values_outside_the_limits_are_rejected_with_a_message(change, text):
    with pytest.raises(ValueError, match=text):
        profile_from_mapping({**VALID, **change}, TODAY)


def test_profile_limits_are_inclusive():
    for key, low, high in (("height", run_config.HEIGHT_CM_MIN, run_config.HEIGHT_CM_MAX),
                           ("weight", run_config.WEIGHT_KG_MIN, run_config.WEIGHT_KG_MAX)):
        assert profile_from_mapping({**VALID, key: low}, TODAY) is not None
        assert profile_from_mapping({**VALID, key: high}, TODAY) is not None


def test_read_session_config_returns_the_saved_values(tmp_path):
    (tmp_path / "session_config.json").write_text(json.dumps(VALID))
    assert read_session_config(tmp_path) == VALID


def test_read_session_config_is_empty_when_absent(tmp_path):
    assert read_session_config(tmp_path) == {}


@pytest.mark.parametrize("content", ["{broken", "[1, 2]", "", '"text"'])
def test_read_session_config_is_empty_when_unreadable(tmp_path, content):
    (tmp_path / "session_config.json").write_text(content)
    assert read_session_config(tmp_path) == {}
