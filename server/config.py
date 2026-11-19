"""Defaults read from the environment.

Nothing here is state of a run: a run gets its values from an EtlConfig. The
API and the command line read these defaults once, when they build one.
"""
import os
import sys
from datetime import date

PROFILE_ENV = {
    "dob": "USER_DOB",
    "gender": "USER_GENDER",
    "height": "USER_HEIGHT_CM",
    "weight": "USER_WEIGHT_KG",
}


def default_data_dir() -> str:
    """Folder with the export when nothing else says otherwise (DATA_DIR)."""
    return os.environ.get("DATA_DIR", "data")


def profile_values_from_env() -> dict:
    """Biometrics set in the environment, as the keys of session_config.json.

    Only the variables that are set appear; run_config.profile_from_mapping
    turns the merged values into a Profile.
    """
    return {key: os.environ[name] for key, name in PROFILE_ENV.items() if os.environ.get(name)}


def date_from_env(name: str) -> date | None:
    """A YYYY-MM-DD date from an environment variable (START_DATE, END_DATE), if set."""
    value = os.environ.get(name)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{name} must be a date in YYYY-MM-DD format") from None


# Output paths
if getattr(sys, 'frozen', False):
    import platform
    home = os.path.expanduser("~")
    if platform.system() == "Windows":
        CLIENT_PUBLIC_DIR = os.path.join(os.environ.get("APPDATA", home), "com.fitstats")
    elif platform.system() == "Darwin":
        CLIENT_PUBLIC_DIR = os.path.join(home, "Library", "Application Support", "com.fitstats")
    else:
        CLIENT_PUBLIC_DIR = os.path.join(home, ".local", "share", "com.fitstats")
    os.makedirs(CLIENT_PUBLIC_DIR, exist_ok=True)
else:
    CLIENT_PUBLIC_DIR = os.environ.get("CLIENT_PUBLIC_DIR", os.path.join("..", "client", "public"))
