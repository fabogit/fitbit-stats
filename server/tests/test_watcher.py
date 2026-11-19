import os
import threading
import time

import pandas as pd
import pytest

import config
import main
import watch


@pytest.fixture(autouse=True)
def _restore_config():
    saved = (config.DATA_DIR, config.CLIENT_PUBLIC_DIR, config.USER_DOB,
             config.USER_HEIGHT_CM, config.USER_WEIGHT_KG, config.USER_GENDER)
    yield
    (config.DATA_DIR, config.CLIENT_PUBLIC_DIR, config.USER_DOB,
     config.USER_HEIGHT_CM, config.USER_WEIGHT_KG, config.USER_GENDER) = saved


def _wait(predicate, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


# --- debounce: quiet period, restarted by every event ---

def test_burst_of_events_runs_once_after_quiet_period():
    runs = []
    trigger = watch.QuietPeriodTrigger(lambda: runs.append(time.time()), quiet=0.3)
    last = 0.0
    for _ in range(8):
        trigger.poke()
        last = time.time()
        time.sleep(0.1)  # shorter than the quiet period: timer must restart
    assert runs == []
    assert _wait(lambda: len(runs) == 1)
    assert runs[0] - last >= 0.25
    time.sleep(0.5)
    assert len(runs) == 1


def test_separate_bursts_run_separately():
    runs = []
    trigger = watch.QuietPeriodTrigger(lambda: runs.append(1), quiet=0.1)
    trigger.poke()
    assert _wait(lambda: len(runs) == 1)
    trigger.poke()
    assert _wait(lambda: len(runs) == 2)


def test_event_during_run_schedules_a_second_run_after_it():
    started, release, order = threading.Event(), threading.Event(), []

    def action():
        order.append("start")
        started.set()
        release.wait(2)
        order.append("end")

    trigger = watch.QuietPeriodTrigger(action, quiet=0.05)
    trigger.poke()
    assert started.wait(2)
    trigger.poke()          # change arrives while the first run is in progress
    time.sleep(0.3)         # second timer has fired but must wait for the lock
    assert order == ["start"]
    release.set()
    assert _wait(lambda: order == ["start", "end", "start", "end"])


def test_cancel_drops_pending_run():
    runs = []
    trigger = watch.QuietPeriodTrigger(lambda: runs.append(1), quiet=0.1)
    trigger.poke()
    trigger.cancel()
    time.sleep(0.3)
    assert runs == []


class _Event:
    def __init__(self, path, is_directory=False, dest_path=None):
        self.src_path = path
        self.dest_path = dest_path
        self.is_directory = is_directory


class _Recorder:
    quiet = 1

    def __init__(self):
        self.pokes = 0

    def poke(self):
        self.pokes += 1


def test_handler_pokes_only_for_data_files():
    rec = _Recorder()
    h = watch.DataHandler(trigger=rec)
    h.on_modified(_Event("/d/a.json"))
    h.on_created(_Event("/d/B.CSV"))
    h.on_moved(_Event("/d/tmp", dest_path="/d/c.json"))
    assert rec.pokes == 3
    h.on_modified(_Event("/d/notes.txt"))
    h.on_modified(_Event("/d/sub", is_directory=True))
    assert rec.pokes == 3


def test_log_strings_use_real_newlines(monkeypatch, capsys):
    monkeypatch.setattr(watch.subprocess, "run", lambda *a, **k: None)
    watch.run_etl()
    out = capsys.readouterr().out
    assert "\\n" not in out
    assert out.startswith("\n[watch.py] Running ETL...")


# --- paths ---

def test_session_config_path_follows_client_public_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(tmp_path))
    assert watch.session_config_path() == os.path.join(str(tmp_path), "session_config.json")


def test_main_writes_csv_into_client_public_dir(tmp_path, monkeypatch):
    out = tmp_path / "out"
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(config, "CLIENT_PUBLIC_DIR", str(out))
    df = pd.DataFrame({"resting_bpm": [60.0]},
                      index=pd.to_datetime(["2024-01-01"]).rename("date"))
    monkeypatch.setattr(main.etl, "merge_all_data",
                        lambda progress_callback=None, warnings=None: df)
    for name in ("calculate_readiness", "calculate_metabolic_metrics",
                 "calculate_advanced_metrics"):
        monkeypatch.setattr(main.metrics, name, lambda d: d)
    monkeypatch.setattr(main.sys, "argv", [
        "main.py", "--dob", "1990-01-01", "--height", "175",
        "--weight", "70", "--gender", "male"])
    main.main()
    assert (out / "fitbit_analysis.csv").exists()
    assert (out / "dashboard_data.json").exists()
    assert (out / "etl_warnings.json").exists()
    assert not (cwd / "fitbit_analysis.csv").exists()
