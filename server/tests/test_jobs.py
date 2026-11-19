"""JobManager: states, the run lock, the saved status, and what a failed run keeps."""
import json
import threading

import pytest

import jobs
from jobs import JobBusy, JobManager
from modules.pipeline import NoDataError, PipelineResult

WAIT = 10


class FakeRun:
    """A runner that waits on an Event, so a test can look at the job mid-run."""

    def __init__(self, steps=(), warnings=(), error=None):
        self.steps = list(steps)
        self.found = list(warnings)
        self.error = error
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = []

    def __call__(self, cfg, progress, warnings):
        self.calls.append(cfg)
        for pct, step in self.steps:
            progress(pct, step)
        warnings.extend(self.found)
        self.started.set()      # after the steps, so a test that waits for it sees them
        assert self.release.wait(WAIT)
        if self.error is not None:
            raise self.error
        return PipelineResult(df=None, warnings=warnings)


@pytest.fixture
def status_file(tmp_path):
    return tmp_path / "out" / jobs.LAST_RUN_FILE


@pytest.fixture
def make_job(status_file):
    created = []

    def _make(runner, on_change=None):
        job = JobManager(runner, lambda: status_file, on_change)
        created.append(job)
        return job

    yield _make
    for job in created:
        assert job.join(WAIT)


@pytest.fixture
def cfg(make_config, export_dir):
    return make_config(export_dir)


def finish(job, run):
    run.release.set()
    assert job.join(WAIT)
    return job.snapshot()


def saved(status_file):
    return json.loads(status_file.read_text())


def test_starts_idle(make_job):
    snap = make_job(FakeRun()).snapshot()
    assert (snap.state, snap.id, snap.progress, snap.step, snap.warnings) == ("idle", None, 0, "", [])
    assert snap.started_at is None and snap.finished_at is None and snap.message is None


def test_idle_running_finished(make_job, cfg, status_file):
    run = FakeRun(steps=[(30, "Loading")], warnings=[{"file": "a.json", "reason": "bad"}])
    job = make_job(run)
    started = job.start(cfg)
    assert started.state == "running" and started.progress == 0 and started.id
    assert run.started.wait(WAIT)
    during = job.snapshot()
    assert (during.state, during.progress, during.step) == ("running", 30, "Loading")
    assert saved(status_file)["state"] == "running"       # saved at the start, not at each step
    done = finish(job, run)
    assert (done.state, done.progress, done.id) == ("finished", 100, started.id)
    assert done.message == jobs.SUCCESS_MESSAGE
    assert done.started_at and done.finished_at
    assert done.warnings == [{"file": "a.json", "reason": "bad"}]
    record = saved(status_file)
    assert record["version"] == 1 and record["state"] == "finished" and record["id"] == started.id
    assert record["warnings"] == done.warnings


def test_start_during_a_run_is_busy_and_runs_once(make_job, cfg):
    run = FakeRun()
    job = make_job(run)
    first = job.start(cfg)
    assert run.started.wait(WAIT)
    with pytest.raises(JobBusy) as busy:
        job.start(cfg)
    assert busy.value.snapshot.id == first.id and busy.value.snapshot.state == "running"
    finish(job, run)
    assert len(run.calls) == 1


def test_a_new_run_can_start_after_the_last_one_ended(make_job, cfg):
    run = FakeRun()
    run.release.set()
    job = make_job(run)
    first = job.start(cfg)
    assert job.join(WAIT)
    second = job.start(cfg)
    assert job.join(WAIT)
    assert second.id != first.id and len(run.calls) == 2


def test_no_data_is_an_error_that_keeps_the_warnings(make_job, cfg):
    warning = [{"file": "steps.json", "reason": "ValueError: bad"}]
    run = FakeRun(error=NoDataError(warning))
    job = make_job(run)
    job.start(cfg)
    done = finish(job, run)
    assert done.state == "error" and done.message == "No valid data found."
    assert done.warnings == warning


def test_unexpected_error_keeps_the_warnings_and_hides_paths(make_job, cfg, status_file):
    secret = str(cfg.output_dir / "dashboard_data.json.tmp-1")
    run = FakeRun(warnings=[{"file": "a.csv", "reason": "x"}],
                  error=OSError(28, "No space left", secret))
    job = make_job(run)
    job.start(cfg)
    done = finish(job, run)
    assert done.state == "error"
    assert done.message == "OSError: No space left"
    assert done.warnings == [{"file": "a.csv", "reason": "x"}]
    assert str(cfg.output_dir) not in json.dumps(saved(status_file))


def test_error_text_without_oserror_has_no_folder_either(make_job, cfg):
    run = FakeRun(error=RuntimeError(f"cannot open {cfg.data_dir} / {cfg.output_dir}/x"))
    job = make_job(run)
    job.start(cfg)
    message = finish(job, run).message
    assert message.startswith("RuntimeError: ")
    assert str(cfg.data_dir) not in message and str(cfg.output_dir) not in message


def test_a_failed_run_does_not_block_the_next(make_job, cfg):
    run = FakeRun(error=RuntimeError("boom"))
    job = make_job(run)
    job.start(cfg)
    assert finish(job, run).state == "error"
    run.error = None
    job.start(cfg)
    assert finish(job, run).state == "finished"


def test_progress_never_decreases_and_the_step_follows(make_job, cfg):
    run = FakeRun(steps=[(10, "a"), (50, "b"), (30, "c"), (200, "d")])
    job = make_job(run)
    seen = []
    job._on_change = lambda s: seen.append((s.progress, s.step))
    job.start(cfg)
    assert run.started.wait(WAIT)
    finish(job, run)
    percentages = [p for p, _ in seen]
    assert percentages == sorted(percentages)
    assert (50, "c") in seen and seen[-1][0] == 100
    assert max(percentages) == 100


def test_seq_grows_and_instance_stays_the_same(make_job, cfg):
    run = FakeRun(steps=[(10, "a"), (20, "b")])
    seen = []
    job = make_job(run, seen.append)
    first = job.snapshot()
    job.start(cfg)
    assert run.started.wait(WAIT)
    finish(job, run)
    seqs = [s.seq for s in seen]
    assert seqs == sorted(set(seqs)) and seqs[0] > first.seq
    assert {s.instance for s in seen} == {first.instance}
    assert seen[0].state == "running" and seen[-1].state == "finished"
    assert JobManager(run, lambda: None).snapshot().instance != first.instance


def test_an_unchanged_step_is_not_announced_again(make_job, cfg):
    run = FakeRun(steps=[(10, "a"), (10, "a"), (5, "a")])
    seen = []
    job = make_job(run, seen.append)
    job.start(cfg)
    assert run.started.wait(WAIT)
    finish(job, run)
    assert [(s.progress, s.step) for s in seen] == [(0, jobs.START_STEP), (10, "a"), (100, "a")]


def test_a_failing_listener_does_not_stop_the_run(make_job, cfg):
    def broken(_snapshot):
        raise RuntimeError("listener")

    run = FakeRun()
    job = make_job(run, broken)
    job.start(cfg)
    assert finish(job, run).state == "finished"


def test_prepare_failure_starts_nothing(make_job, cfg, status_file):
    run = FakeRun()
    job = make_job(run)

    def prepare():
        raise OSError("cannot save")

    with pytest.raises(OSError):
        job.start(cfg, prepare=prepare)
    assert job.snapshot().state == "idle" and job.snapshot().seq == 0
    assert not run.calls and not status_file.exists()
    run.release.set()
    assert job.start(cfg).state == "running"      # the lock was not left taken


def test_prepare_is_not_called_when_busy(make_job, cfg):
    run = FakeRun()
    job = make_job(run)
    job.start(cfg)
    called = []
    with pytest.raises(JobBusy):
        job.start(cfg, prepare=lambda: called.append(1))
    assert called == []
    finish(job, run)


def test_a_thread_that_cannot_start_does_not_leave_the_lock_taken(make_job, cfg, monkeypatch):
    run = FakeRun()
    run.release.set()
    job = make_job(run)
    with monkeypatch.context() as m:
        def refuse(self):
            raise RuntimeError("can't start new thread")
        m.setattr(threading.Thread, "start", refuse)
        with pytest.raises(RuntimeError):
            job.start(cfg)
    assert job.snapshot().state == "idle"
    assert job.start(cfg).state == "running"
    assert job.join(WAIT)


def test_progress_of_an_old_run_is_ignored(make_job, cfg):
    run = FakeRun()
    run.release.set()
    job = make_job(run)
    old = job.start(cfg)
    assert job.join(WAIT)
    job._progress(old.id, 50, "late")
    assert job.snapshot().state == "finished" and job.snapshot().step != "late"


# --- the saved status ---

def write_record(status_file, **fields):
    record = {"version": 1, "id": "abc", "state": "finished", "progress": 100, "step": "Complete",
              "started_at": "2024-01-01T10:00:00Z", "finished_at": "2024-01-01T10:00:05Z",
              "message": "ok", "warnings": [{"file": "a.json", "reason": "bad"}]}
    record.update(fields)
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(record))


def test_load_restores_a_finished_run(make_job, status_file):
    write_record(status_file)
    job = make_job(FakeRun())
    job.load()
    snap = job.snapshot()
    assert (snap.id, snap.state, snap.message) == ("abc", "finished", "ok")
    assert snap.warnings == [{"file": "a.json", "reason": "bad"}]


def test_load_turns_a_running_record_into_an_interrupted_error(make_job, status_file):
    write_record(status_file, state="running", progress=40, finished_at=None, message=None)
    job = make_job(FakeRun())
    job.load()
    snap = job.snapshot()
    assert snap.state == "error" and snap.message == jobs.INTERRUPTED_MESSAGE and snap.id == "abc"
    assert saved(status_file)["state"] == "error"        # a second restart says the same


@pytest.mark.parametrize("content", [
    "not json", "[]", "null", json.dumps({"version": 2}), json.dumps({"version": 1}),
    json.dumps({"version": 1, "id": "x", "state": "idle", "progress": 0, "step": "",
                "started_at": None, "finished_at": None, "message": None, "warnings": []}),
    json.dumps({"version": 1, "id": "x", "state": "finished", "progress": "100", "step": "",
                "started_at": None, "finished_at": None, "message": None, "warnings": []}),
    json.dumps({"version": 1, "id": "x", "state": "finished", "progress": 100, "step": "",
                "started_at": None, "finished_at": None, "message": None, "warnings": [1]}),
])
def test_unreadable_or_foreign_file_means_idle(make_job, status_file, content):
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(content)
    job = make_job(FakeRun())
    job.load()
    assert job.snapshot().state == "idle" and job.snapshot().id is None


def test_load_without_a_file_is_idle(make_job):
    job = make_job(FakeRun())
    job.load()
    assert job.snapshot().state == "idle"


def test_a_status_that_cannot_be_saved_does_not_stop_the_run(make_config, export_dir, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    run = FakeRun()
    job = JobManager(run, lambda: blocker / jobs.LAST_RUN_FILE)     # a folder cannot be made here
    job.start(make_config(export_dir))
    assert finish(job, run).state == "finished"


def test_the_saved_status_is_written_after_the_run_ends(make_job, cfg, status_file):
    """While the runner is still moving its files the saved status says running, never finished."""
    seen = []

    def runner(cfg, progress, warnings):
        seen.append(saved(status_file)["state"])
        return PipelineResult(df=None, warnings=warnings)

    job = make_job(runner)
    job.start(cfg)
    assert job.join(WAIT)
    assert seen == ["running"] and saved(status_file)["state"] == "finished"


# --- reset ---

def test_reset_forgets_the_run_and_the_file(make_job, cfg, status_file):
    run = FakeRun()
    run.release.set()
    job = make_job(run)
    job.start(cfg)
    assert job.join(WAIT)
    erased = []
    snap = job.reset(erase=lambda: erased.append(1))
    assert erased == [1] and not status_file.exists()
    assert (snap.state, snap.id, snap.warnings, snap.message) == ("idle", None, [], None)


def test_reset_during_a_run_is_busy_and_erases_nothing(make_job, cfg, status_file):
    run = FakeRun()
    job = make_job(run)
    job.start(cfg)
    erased = []
    with pytest.raises(JobBusy):
        job.reset(erase=lambda: erased.append(1))
    assert erased == [] and status_file.exists()
    finish(job, run)
