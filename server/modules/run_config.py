"""Configuration of one ETL run.

Plain data and constructors only: this module imports neither ``etl`` nor
``metrics`` (they receive the values as arguments), so it cannot create an
import cycle and it holds no state shared between runs.
"""
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, Mapping

import applog

logger = applog.get_logger("run_config")

# Biometric limits. Keep identical to client/src/lib/biometrics.ts (all bounds inclusive).
HEIGHT_CM_MIN = 50
HEIGHT_CM_MAX = 250
WEIGHT_KG_MIN = 20
WEIGHT_KG_MAX = 300
AGE_YEARS_MIN = 5
AGE_YEARS_MAX = 120

SESSION_CONFIG_FILE = "session_config.json"


def age_on(dob: date, today: date) -> int:
    """Completed years between dob and today."""
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


@dataclass(frozen=True)
class Profile:
    """The user's biometrics, used for the BMR and the active calories."""
    dob: date
    gender: Literal["male", "female"]
    height_cm: int
    weight_kg: float


@dataclass(frozen=True)
class EtlConfig:
    """Everything one ETL run needs. Immutable: a run never changes it."""
    data_dir: Path
    output_dir: Path
    profile: Profile | None          # None: BMR and active calories are left at 0
    start_date: date | None = None   # inclusive
    end_date: date | None = None     # inclusive


def _is_set(value: Any) -> bool:
    """False for the values that mean "not provided": None, "" and 0."""
    return value is not None and value != "" and value != 0


def _whole_number(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"{name} must be a whole number")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a whole number") from None


def _number(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None


def profile_from_mapping(m: Mapping[str, Any], today: date | None = None) -> Profile | None:
    """Builds a Profile from the keys of session_config.json (dob, gender, height, weight).

    Returns None when one of the four keys is missing or empty (an incomplete
    profile). Raises ValueError, with a message that can be shown to the user,
    when a value is present but outside the limits the API enforces.
    """
    if not all(_is_set(m.get(key)) for key in ("dob", "gender", "height", "weight")):
        return None

    raw_dob = m["dob"]
    if isinstance(raw_dob, date):
        dob = raw_dob
    else:
        try:
            dob = date.fromisoformat(str(raw_dob))
        except ValueError:
            raise ValueError("dob must be a date in YYYY-MM-DD format") from None
    age = age_on(dob, today or date.today())
    if not AGE_YEARS_MIN <= age <= AGE_YEARS_MAX:
        raise ValueError(
            f"dob must give an age between {AGE_YEARS_MIN} and {AGE_YEARS_MAX} years")

    gender = m["gender"]
    if gender not in ("male", "female"):
        raise ValueError("gender must be 'male' or 'female'")

    height = _whole_number("height", m["height"])
    if not HEIGHT_CM_MIN <= height <= HEIGHT_CM_MAX:
        raise ValueError(f"height must be between {HEIGHT_CM_MIN} and {HEIGHT_CM_MAX} cm")

    weight = _number("weight", m["weight"])
    if not WEIGHT_KG_MIN <= weight <= WEIGHT_KG_MAX:
        raise ValueError(f"weight must be between {WEIGHT_KG_MIN} and {WEIGHT_KG_MAX} kg")

    return Profile(dob=dob, gender=gender, height_cm=height, weight_kg=weight)


def read_session_config(output_dir: Path) -> dict:
    """The saved session_config.json of an output folder; {} if absent or unreadable."""
    path = Path(output_dir) / SESSION_CONFIG_FILE
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning("Could not read %s (%s); ignoring it.", SESSION_CONFIG_FILE, type(e).__name__)
        return {}
    return data if isinstance(data, dict) else {}
