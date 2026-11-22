"""The server log: levels, format, and that it never names the user's folders."""
import io
import logging
import re
import sys
from datetime import date
from pathlib import Path

import pytest

import applog
from conftest import DEFAULT_PROFILE
from jobs import JobManager
from modules import etl, pipeline
from modules.run_config import EtlConfig

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@pytest.fixture
def scrubber(monkeypatch, tmp_path):
    """A scrubber of its own, with a home folder that exists only in this test."""
    home = tmp_path / "home" / "someone"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return applog.PathScrubber()


@pytest.fixture
def log_text(monkeypatch):
    """The text that the "fitstats" logger writes, through the real handler and filter."""
    stream = io.StringIO()
    handler = applog.make_handler(stream)
    logger = logging.getLogger(applog.ROOT)
    monkeypatch.setattr(logger, "handlers", [handler])
    monkeypatch.setattr(applog, "scrubber", handler.filters[0])
    previous = logger.level
    logger.setLevel(logging.DEBUG)  # setLevel, not an assignment: it also clears the logger's cache
    yield stream.getvalue
    logger.setLevel(previous)


class TestScrubber:
    def test_home_becomes_a_tilde(self, scrubber, tmp_path):
        home = tmp_path / "home" / "someone"
        assert scrubber.scrub(f"cannot open {home}/Documents/export.json") == \
            "cannot open ~/Documents/export.json"

    def test_run_folders_get_their_placeholders(self, scrubber, tmp_path):
        data, out = tmp_path / "home" / "someone" / "Takeout", tmp_path / "elsewhere" / "results"
        scrubber.hide(data, applog.DATA_PLACEHOLDER)
        scrubber.hide(out, applog.OUTPUT_PLACEHOLDER)
        text = scrubber.scrub(f"read {data}/Global Export Data/a.json, wrote {out}/x.csv, {tmp_path}")
        # The data folder is inside the home folder: the longer match wins.
        assert text == f"read <data>/Global Export Data/a.json, wrote <output>/x.csv, {tmp_path}"

    def test_windows_spelling_of_a_folder_is_found_too(self, scrubber):
        scrubber.hide("C:\\Users\\someone\\Takeout", applog.DATA_PLACEHOLDER)
        assert scrubber.scrub("open C:\\Users\\someone\\Takeout\\a.json") == "open <data>\\a.json"
        assert scrubber.scrub("open C:/Users/someone/Takeout/a.json") == "open <data>/a.json"

    @pytest.mark.parametrize("short", ["/", ".", "", "C:\\", "/a"])
    def test_a_folder_too_short_to_be_private_is_left_alone(self, scrubber, short):
        scrubber.hide(short, applog.DATA_PLACEHOLDER)
        assert scrubber.scrub("/usr/lib/a.json and ./b") == "/usr/lib/a.json and ./b"

    def test_text_without_private_folders_is_unchanged(self, scrubber):
        assert scrubber.scrub("Skipped 3 files of *.json") == "Skipped 3 files of *.json"

    def test_message_arguments_and_traceback_are_scrubbed(self, scrubber, tmp_path):
        folder = tmp_path / "private" / "export"
        scrubber.hide(folder, applog.DATA_PLACEHOLDER)
        try:
            raise OSError(f"no such file: {folder}/a.json")
        except OSError:
            record = logging.LogRecord("t", logging.ERROR, __file__, 1, "failed on %s", (str(folder),),
                                       exc_info=sys.exc_info())
        scrubber.filter(record)
        text = logging.Formatter().format(record)
        assert str(folder) not in text
        assert "failed on <data>" in text and "no such file: <data>/a.json" in text


class TestHandler:
    def test_lines_start_with_the_level_like_uvicorn(self, log_text):
        applog.get_logger("t").info("hello")
        applog.get_logger("t").warning("careful")
        assert log_text().splitlines() == ["INFO:     hello", "WARNING:  careful"]

    def test_the_default_level_is_info(self):
        applog.configure_logging()
        assert logging.getLogger(applog.ROOT).level == logging.INFO

    def test_configure_logging_twice_adds_one_handler(self):
        applog.configure_logging()
        applog.configure_logging()
        ours = [h for h in logging.getLogger(applog.ROOT).handlers if getattr(h, "_fitstats", False)]
        assert len(ours) == 1


class TestRunsLeaveNoPrivateTrace:
    def test_failed_run_traceback_hides_the_folders(self, log_text, tmp_path):
        data, out = tmp_path / "Takeout 2026", tmp_path / "app data"

        def runner(cfg, progress, warnings):
            raise OSError(f"cannot read {cfg.data_dir}/Global Export Data/x.json")

        job = JobManager(runner, lambda: tmp_path / "last_run.json")
        job.start(EtlConfig(data_dir=data, output_dir=out, profile=DEFAULT_PROFILE))
        job.join(10)
        text = log_text()
        assert "ETL run failed" in text and "Traceback" in text
        assert str(data) not in text and str(out) not in text
        assert "<data>/Global Export Data/x.json" in text

    def test_the_pipeline_logs_no_folder_name_and_no_date(self, log_text, make_config, export_dir):
        cfg = make_config(export_dir, start=date(2024, 1, 3), end=date(2024, 1, 6))
        applog.hide_folders(cfg.data_dir, cfg.output_dir)
        pipeline.run_pipeline(cfg)
        text = log_text()
        assert "Building the master dataset" in text and "Outputs written" in text
        assert str(export_dir) not in text and str(cfg.output_dir) not in text
        assert not DATE.search(text), text

    def test_skipped_files_are_counted_at_info_and_named_only_at_debug(self, log_text, tmp_path):
        folder = tmp_path / "export" / "Global Export Data"
        folder.mkdir(parents=True)
        (folder / "steps-2024-01-01.json").write_text("not json")
        warnings = []
        etl.merge_all_data(tmp_path / "export", warnings=warnings)
        assert len(warnings) == 1
        lines = log_text().splitlines()
        assert "INFO:     Skipped 1 files of steps-*.json" in lines
        # The name appears only in a DEBUG line, which the default level never writes.
        named = [line for line in lines if "steps-2024-01-01.json" in line]
        assert named and all(line.startswith("DEBUG") for line in named)
