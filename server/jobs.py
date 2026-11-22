"""Runs the ETL in a background thread and keeps the status of the last run.

The JobManager owns the run lock and the thread: a run is either refused
(JobBusy) or started, and its state is always one of idle, running, finished
or error. The status of the last run is saved to ``last_run.json`` in the
output folder when a run starts and when it ends, so it survives a restart.
"""
import json
import os
import secrets
import threading
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

import applog
from modules.etl import describe_error
from modules.pipeline import NoDataError, PipelineResult, ProgressFn
from modules.run_config import EtlConfig

logger = applog.get_logger("jobs")

JobState = Literal["idle", "running", "finished", "error"]

LAST_RUN_FILE = "last_run.json"
STATUS_VERSION = 1
START_STEP = "Starting ETL engine..."
SUCCESS_MESSAGE = "ETL completed successfully"
NO_DATA_MESSAGE = "No valid data found."
INTERRUPTED_MESSAGE = "The previous calculation was interrupted."

# A runner does one run: runner(config, progress, warnings). `warnings` is a
# list it fills with the skipped files as it finds them.
Runner = Callable[[EtlConfig, ProgressFn, list], PipelineResult]


@dataclass(frozen=True)
class JobSnapshot:
    """The status of the job at one moment.

    `instance` (random, one per server process) and `seq` (grows with every
    change in that process) let a client discard a snapshot that arrives
    after a newer one.
    """
    instance: str
    seq: int
    id: str | None              # uuid4 hex of the last known run; None if there is none
    state: JobState
    progress: int               # 0-100, never decreases within a run
    step: str
    started_at: str | None      # ISO 8601 UTC, for display only
    finished_at: str | None
    message: str | None         # outcome or error, never a folder path
    warnings: list[dict]        # [{"file", "reason"}] of the run, finished or failed

    def to_dict(self) -> dict:
        return {
            "instance": self.instance, "seq": self.seq, "id": self.id, "state": self.state,
            "progress": self.progress, "step": self.step, "started_at": self.started_at,
            "finished_at": self.finished_at, "message": self.message,
            "warnings": [dict(w) for w in self.warnings],
        }


class JobBusy(Exception):
    """A run is already in progress. Carries the current snapshot."""

    def __init__(self, snapshot: JobSnapshot):
        super().__init__("An ETL run is already in progress")
        self.snapshot = snapshot


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _is_str_or_none(value) -> bool:
    return value is None or isinstance(value, str)


def _warning_list(value) -> list[dict] | None:
    """The warnings of a saved record, or None if they are not a list of {file, reason}."""
    if not isinstance(value, list):
        return None
    if not all(isinstance(w, dict) and isinstance(w.get("file"), str)
               and isinstance(w.get("reason"), str) for w in value):
        return None
    return [{"file": w["file"], "reason": w["reason"]} for w in value]


class JobManager:
    def __init__(self, runner: Runner, status_path: Callable[[], Path],
                 on_change: Callable[[JobSnapshot], None] | None = None):
        """`status_path` is called each time, so the output folder can change between runs.

        `on_change` is called, in the order of `seq`, after every change, from
        the thread that made it (the run thread or the caller of start/reset).
        It must not block.
        """
        self._runner = runner
        self._status_path = status_path
        self._on_change = on_change
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._current = JobSnapshot(
            instance=secrets.token_hex(8), seq=0, id=None, state="idle", progress=0, step="",
            started_at=None, finished_at=None, message=None, warnings=[])

    # --- reading ---

    def snapshot(self) -> JobSnapshot:
        with self._lock:
            return self._current

    def join(self, timeout: float | None = None) -> bool:
        """Waits for the current run to end (for tests). True if no run is left."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return thread is None or not thread.is_alive()

    # --- changing the state ---

    def _advance(self, **changes) -> JobSnapshot:
        """Publishes a new snapshot (caller holds the lock)."""
        self._current = replace(self._current, seq=self._current.seq + 1, **changes)
        snapshot = self._current
        if self._on_change is not None:
            try:
                self._on_change(snapshot)
            except Exception:
                logger.exception("Job status listener failed")
        return snapshot

    def load(self) -> None:
        """Restores the status of the last run from the output folder, at server start.

        A saved run still marked as running was cut short by a shutdown: it
        becomes an error. A missing, unreadable or foreign file means idle.
        """
        with self._lock:
            record = self._read_record()
            if record is None:
                return
            if record["state"] == "running":
                record.update(state="error", message=INTERRUPTED_MESSAGE, finished_at=None)
                self._advance(**record)
                self._write_record()
            else:
                self._advance(**record)

    def start(self, cfg: EtlConfig, prepare: Callable[[], None] | None = None) -> JobSnapshot:
        """Starts a run in a new thread; raises JobBusy if one is in progress.

        `prepare` is called once the run is accepted and before it starts; if it
        raises, nothing starts and the state is unchanged.
        """
        with self._lock:
            if self._current.state == "running":
                raise JobBusy(self._current)
            # From here on the log never names the folders of this run.
            applog.hide_folders(cfg.data_dir, cfg.output_dir)
            if prepare is not None:
                prepare()
            run_id = uuid.uuid4().hex
            previous = self._current
            warnings: list[dict] = []
            snapshot = self._advance(
                id=run_id, state="running", progress=0, step=START_STEP, started_at=_now(),
                finished_at=None, message=None, warnings=[])
            # Saved before the thread exists, so the file never lags behind the run.
            self._write_record()
            thread = threading.Thread(target=self._run, args=(cfg, run_id, warnings),
                                      name="etl-run", daemon=True)
            try:
                thread.start()
            except BaseException:
                # No thread, so nothing would ever end this run: put the old state back.
                self._advance(
                    id=previous.id, state=previous.state, progress=previous.progress,
                    step=previous.step, started_at=previous.started_at,
                    finished_at=previous.finished_at, message=previous.message,
                    warnings=previous.warnings)
                if previous.id is None:
                    self._remove_record()
                else:
                    self._write_record()
                raise
            self._thread = thread
            return snapshot

    def reset(self, erase: Callable[[], None] | None = None) -> JobSnapshot:
        """Forgets the last run (factory reset); raises JobBusy while a run is in progress.

        `erase` is called with the lock held, so no run can start while it deletes the data.
        """
        with self._lock:
            if self._current.state == "running":
                raise JobBusy(self._current)
            if erase is not None:
                erase()
            self._remove_record()
            return self._advance(id=None, state="idle", progress=0, step="", started_at=None,
                                 finished_at=None, message=None, warnings=[])

    # --- the run thread ---

    def _run(self, cfg: EtlConfig, run_id: str, warnings: list[dict]) -> None:
        def progress(pct, step):
            self._progress(run_id, pct, step)

        try:
            result = self._runner(cfg, progress, warnings)
        except NoDataError as e:
            self._finish(run_id, "error", NO_DATA_MESSAGE, e.warnings)
        except Exception as e:
            logger.exception("ETL run failed")
            message = describe_error(e, (cfg.data_dir, cfg.output_dir))
            self._finish(run_id, "error", message, warnings)
        else:
            self._finish(run_id, "finished", SUCCESS_MESSAGE, result.warnings)

    def _progress(self, run_id: str, pct, step: str) -> None:
        with self._lock:
            current = self._current
            if current.id != run_id or current.state != "running":
                return
            pct = max(current.progress, min(100, max(0, int(pct))))
            if pct == current.progress and step == current.step:
                return
            self._advance(progress=pct, step=step)

    def _finish(self, run_id: str, state: JobState, message: str, warnings: list[dict]) -> None:
        """Ends the run. Only called after run_pipeline has put all its files in place."""
        with self._lock:
            if self._current.id != run_id or self._current.state != "running":
                return
            progress = 100 if state == "finished" else self._current.progress
            self._advance(state=state, progress=progress, finished_at=_now(), message=message,
                          warnings=[dict(w) for w in warnings])
            self._write_record()

    # --- the file ---

    def _read_record(self) -> dict | None:
        try:
            with open(self._status_path(), "r") as f:
                raw = json.load(f)
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as e:
            logger.warning("Ignoring %s (%s)", LAST_RUN_FILE, type(e).__name__)
            return None
        warnings = _warning_list(raw.get("warnings")) if isinstance(raw, dict) else None
        if (not isinstance(raw, dict) or raw.get("version") != STATUS_VERSION
                or raw.get("state") not in ("running", "finished", "error")
                or not isinstance(raw.get("id"), str)
                or isinstance(raw.get("progress"), bool) or not isinstance(raw.get("progress"), int)
                or not isinstance(raw.get("step"), str)
                or not all(_is_str_or_none(raw.get(k)) for k in ("started_at", "finished_at", "message"))
                or warnings is None):
            logger.warning("Ignoring %s: unexpected content", LAST_RUN_FILE)
            return None
        return {"id": raw["id"], "state": raw["state"], "progress": max(0, min(100, raw["progress"])),
                "step": raw["step"], "started_at": raw["started_at"],
                "finished_at": raw["finished_at"], "message": raw["message"], "warnings": warnings}

    def _remove_record(self) -> None:
        try:
            Path(self._status_path()).unlink(missing_ok=True)
        except OSError as e:
            logger.warning("Could not remove %s (%s)", LAST_RUN_FILE, type(e).__name__)

    def _write_record(self) -> None:
        """Saves the current status atomically. A failure is logged: it never stops a run."""
        s = self._current
        record = {"version": STATUS_VERSION, "id": s.id, "state": s.state, "progress": s.progress,
                  "step": s.step, "started_at": s.started_at, "finished_at": s.finished_at,
                  "message": s.message, "warnings": s.warnings}
        path = Path(self._status_path())
        tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w") as f:
                json.dump(record, f)
            os.replace(tmp, path)
        except OSError as e:
            logger.warning("Could not save %s (%s)", LAST_RUN_FILE, type(e).__name__)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
