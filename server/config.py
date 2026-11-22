"""Defaults read from the environment.

Nothing here is state of a run: a run gets its values from an EtlConfig. The
API and the command line read these defaults once, when they build one.
"""
import os
import platform
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


def frozen_data_dir() -> str:
    """The data folder of the packaged app, when the desktop shell does not name one.

    The same folder the shell calls its app data folder (Tauri's `app_data_dir`)
    on Windows and macOS; on Linux the shell follows XDG_DATA_HOME, which this
    fallback does not, so the shell always passes the folder (CLIENT_PUBLIC_DIR).
    """
    home = os.path.expanduser("~")
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ.get("APPDATA", home), "com.fitstats")
    if system == "Darwin":
        return os.path.join(home, "Library", "Application Support", "com.fitstats")
    return os.path.join(home, ".local", "share", "com.fitstats")


def initial_output_dir() -> str:
    """Where the app keeps its files (CLIENT_PUBLIC_DIR).

    Packaged (frozen) app: the folder the desktop shell passes in CLIENT_PUBLIC_DIR,
    so the shell and the server always agree on it, or `frozen_data_dir()` when
    the server is started by hand. Anywhere else, CLIENT_PUBLIC_DIR or the
    folder the web client is served from.
    """
    explicit = os.environ.get("CLIENT_PUBLIC_DIR")
    if getattr(sys, "frozen", False):
        folder = explicit or frozen_data_dir()
        os.makedirs(folder, exist_ok=True)
        return folder
    return explicit or os.path.join("..", "client", "public")


CLIENT_PUBLIC_DIR = initial_output_dir()
