"""Where the app keeps its files: the packaged server and the desktop shell must agree."""
import platform
import sys

import pytest

import config


@pytest.fixture
def frozen(monkeypatch, tmp_path):
    """Pretends to be the PyInstaller build, with a home folder and no shell-provided folder."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.delenv("CLIENT_PUBLIC_DIR", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    return tmp_path


def test_frozen_server_uses_the_folder_the_shell_passes(frozen, monkeypatch):
    shell_folder = frozen / "xdg" / "com.fitstats"
    monkeypatch.setenv("CLIENT_PUBLIC_DIR", str(shell_folder))
    assert config.initial_output_dir() == str(shell_folder)
    assert shell_folder.is_dir()                       # created when missing
    assert not (frozen / "home").exists()              # nothing is written to the fallback folder


def test_an_empty_value_from_the_shell_counts_as_none(frozen, monkeypatch):
    monkeypatch.setenv("CLIENT_PUBLIC_DIR", "")
    assert config.initial_output_dir() == config.frozen_data_dir()


@pytest.mark.parametrize("system, expected", [
    ("Linux", ("home", ".local", "share", "com.fitstats")),
    ("Darwin", ("home", "Library", "Application Support", "com.fitstats")),
])
def test_frozen_server_started_by_hand_keeps_the_folder_of_earlier_versions(
        frozen, monkeypatch, system, expected):
    monkeypatch.setattr(platform, "system", lambda: system)
    folder = config.initial_output_dir()
    assert folder == str(frozen.joinpath(*expected))
    assert (frozen / "home").is_dir() and folder.endswith("com.fitstats")


def test_frozen_server_started_by_hand_on_windows_uses_appdata(frozen, monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", str(frozen / "roaming"))
    assert config.initial_output_dir() == str(frozen / "roaming" / "com.fitstats")


def test_a_shell_folder_is_not_used_when_not_frozen_unless_named(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delenv("CLIENT_PUBLIC_DIR", raising=False)
    assert config.initial_output_dir().endswith("public")
    monkeypatch.setenv("CLIENT_PUBLIC_DIR", str(tmp_path / "out"))
    assert config.initial_output_dir() == str(tmp_path / "out")
    assert not (tmp_path / "out").exists()             # not created here: the pipeline does it
