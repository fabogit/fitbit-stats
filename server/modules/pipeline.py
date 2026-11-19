"""The one ETL pipeline, called by the API and by the command line.

Reads everything it needs from an EtlConfig and keeps no state between runs.
"""
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from modules import etl, metrics
from modules.run_config import EtlConfig

ProgressFn = Callable[[int, str], None]

CSV_FILE = "fitbit_analysis.csv"
# Moved into place in this order: the dashboard data, which the app reads, goes last.
OUTPUT_FILES = (CSV_FILE, etl.JSON_FILE)

# A temporary file of an interrupted run is removed by the next run once it is
# this old; a younger one may belong to a run that is still writing.
STALE_TMP_SECONDS = 3600
# On Windows os.replace fails while another process has the file open.
REPLACE_ATTEMPTS = 5
REPLACE_DELAY_SECONDS = 0.1


@dataclass(frozen=True)
class PipelineResult:
    df: pd.DataFrame
    warnings: list[dict]             # [{"file", "reason"}], file names only


class NoDataError(Exception):
    """The data folder gave no usable data. Carries the files skipped on the way."""

    def __init__(self, warnings: list[dict]):
        super().__init__("No valid data found.")
        self.warnings = warnings


def _tmp_path(final: Path) -> Path:
    return final.with_name(f"{final.name}.tmp-{os.getpid()}")


def _remove_stale_tmp_files(output_dir: Path) -> None:
    cutoff = time.time() - STALE_TMP_SECONDS
    for name in OUTPUT_FILES:
        for path in output_dir.glob(f"{name}.tmp-*"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                pass


def _replace(src: Path, dst: Path) -> None:
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(REPLACE_DELAY_SECONDS)


def run_pipeline(cfg: EtlConfig, progress: ProgressFn | None = None,
                 warnings: list[dict] | None = None) -> PipelineResult:
    """Merges the export, computes the metrics and writes the two output files.

    The files (fitbit_analysis.csv, dashboard_data.json) go to cfg.output_dir.
    Each is written under a temporary name first and moved into place only once
    both are complete, so a failed or interrupted run leaves the files of the
    previous run untouched.

    The skipped files are collected in `warnings` (a new list when not given)
    as they are found, so a caller that passes its own list still has them if
    the run fails. They are also in the result.

    Raises NoDataError, without touching any output file, when the data folder
    gives no usable data.
    """
    def report(pct, msg):
        if progress:
            progress(pct, msg)

    output_dir = Path(cfg.output_dir)
    warnings = [] if warnings is None else warnings

    report(10, "Loading and merging data files")
    df = etl.merge_all_data(cfg.data_dir, cfg.start_date, cfg.end_date,
                            progress_callback=report, warnings=warnings)
    if df is None:
        raise NoDataError(warnings)

    report(70, "Calculating readiness metrics")
    df = metrics.calculate_readiness(df)

    report(75, "Calculating metabolic metrics")
    df = metrics.calculate_metabolic_metrics(df, cfg.profile)

    report(80, "Calculating advanced metrics")
    df = metrics.calculate_advanced_metrics(df)

    output_dir.mkdir(parents=True, exist_ok=True)
    _remove_stale_tmp_files(output_dir)
    finals = [output_dir / name for name in OUTPUT_FILES]
    tmps = [_tmp_path(path) for path in finals]
    try:
        report(90, "Exporting analysis CSV")
        df.to_csv(tmps[0])

        report(95, "Exporting dashboard JSON")
        etl.export_to_json(df, output_dir, filename=tmps[1].name)

        for tmp, final in zip(tmps, finals):
            _replace(tmp, final)
    finally:
        for tmp in tmps:
            tmp.unlink(missing_ok=True)
    print(f"-> Analysis CSV exported to: {finals[0]}")
    print(f"-> Dashboard JSON exported to: {finals[1]}")

    report(100, "Complete")
    return PipelineResult(df=df, warnings=warnings)
