"""Stopping the server while a calculation is running leaves no worker process behind (Linux)."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

import api

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="reads /proc")

SERVER_DIR = Path(api.__file__).resolve().parent
TOKEN = "t" * 64
FILES = 10            # more than the pool has workers on a small machine
SAMPLES = 25_000      # per file


def write_export(root: Path) -> None:
    folder = root / "Global Export Data"
    folder.mkdir(parents=True)
    for n in range(FILES):
        day = f"{n % 28 + 1:02d}"
        samples = [{"dateTime": f"03/{day}/24 {i // 3600 % 24:02d}:{i // 60 % 60:02d}:{i % 60:02d}",
                    "value": {"bpm": 50 + i % 70, "confidence": 2}} for i in range(SAMPLES)]
        (folder / f"heart_rate-2024-03-{n + 1:02d}.json").write_text(json.dumps(samples, separators=(",", ":")))
    # the minimum the pipeline needs to produce a result
    (folder / "calories-2024-03-01.json").write_text(
        json.dumps([{"dateTime": "03/01/24 00:00:00", "value": "2000"}]))


def group_members(pgid: int) -> list[int]:
    """Live (not zombie) processes of a process group."""
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            stat = Path(f"/proc/{entry}/stat").read_text()
        except OSError:
            continue
        fields = stat[stat.rindex(")") + 2:].split()
        if int(fields[2]) == pgid and fields[0] != "Z":
            found.append(int(entry))
    return found


def alive(pid: int) -> bool:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return stat[stat.rindex(")") + 2] != "Z"


def run_script(code: str) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", code], cwd=SERVER_DIR, stdout=subprocess.PIPE, text=True)


def wait_until_gone(pids, seconds=5.0) -> list[int]:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and any(alive(p) for p in pids):
        time.sleep(0.02)
    return [p for p in pids if alive(p)]


def test_end_process_tree_takes_every_process_of_the_group_at_once():
    script = """
import subprocess, sys, api
api.lead_process_group()
kids = [subprocess.Popen(["sleep", "60"]) for _ in range(3)]
print(*[k.pid for k in kids], flush=True)
api.end_process_tree(True)
"""
    proc = run_script(script)
    try:
        kids = [int(p) for p in proc.stdout.readline().split()]
        assert wait_until_gone(kids) == []
        assert proc.wait(10) == 0
    finally:
        proc.kill()
        proc.wait()
        proc.stdout.close()


def test_the_forced_exit_run_by_a_timer_ends_the_process_and_its_group():
    """The forced exit runs in a threading.Timer, not in the main thread (where a signal
    handler cannot be changed): the process must still go, with every process of its group."""
    script = """
import subprocess, threading, time, api
api.lead_process_group()
kids = [subprocess.Popen(["sleep", "60"]) for _ in range(3)]
print(*[k.pid for k in kids], flush=True)
threading.Timer(0.2, api._force_exit, args=(True,)).start()
time.sleep(60)   # a server that did not stop; the timer must end it
"""
    proc = run_script(script)
    kids = []
    try:
        kids = [int(p) for p in proc.stdout.readline().split()]
        assert wait_until_gone(kids, 10) == []
        assert proc.wait(10) in (0, -9)
    finally:
        for pid in kids:
            if alive(pid):
                os.kill(pid, 9)
        proc.kill()
        proc.wait()
        proc.stdout.close()


def test_a_pool_worker_ends_when_the_server_that_started_it_is_killed():
    script = """
import os, signal, time
from concurrent.futures import ProcessPoolExecutor
from modules import etl
pool = ProcessPoolExecutor(2, initializer=etl.exit_with_parent)
futures = [pool.submit(time.sleep, 60) for _ in range(2)]
time.sleep(1)
print(*[p.pid for p in pool._processes.values()], flush=True)
os.kill(os.getpid(), signal.SIGKILL)
"""
    proc = run_script(script)
    workers = []
    try:
        workers = [int(p) for p in proc.stdout.readline().split()]
        assert len(workers) == 2
        assert wait_until_gone(workers) == []
    finally:
        for pid in workers:
            if alive(pid):
                os.kill(pid, 9)
        proc.kill()
        proc.wait()
        proc.stdout.close()


@pytest.mark.parametrize("how", ["shutdown line", "stdin closed"])
def test_no_process_is_left_when_the_server_is_stopped_during_a_run(tmp_path, how):
    write_export(tmp_path / "export")
    (tmp_path / "out").mkdir()
    env = {k: v for k, v in os.environ.items() if k != api.TOKEN_ENV}
    env.update({api.PORT_ENV: "0", api.STDIN_EOF_ENV: "1", api.TOKEN_ENV: TOKEN,
                "CLIENT_PUBLIC_DIR": str(tmp_path / "out"), "PYTHONUNBUFFERED": "1"})
    proc = subprocess.Popen([sys.executable, str(SERVER_DIR / "api.py")], env=env, cwd=SERVER_DIR,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(path, body=None):
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}", data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        with opener.open(request, timeout=10) as resp:
            return json.load(resp)

    try:
        line = proc.stdout.readline()
        assert line.startswith(api.READY_PREFIX)
        port = json.loads(line[len(api.READY_PREFIX):])["port"]
        # the server leads a group of its own, which its workers join
        call("/api/start", {"dob": "1990-01-01", "gender": "male", "height": 180, "weight": 75.0,
                            "data_path": str(tmp_path / "export")})
        deadline = time.monotonic() + 60
        while len(group_members(proc.pid)) < 2:
            assert time.monotonic() < deadline and call("/api/status")["state"] == "running", \
                "the run ended before any worker was seen"
            time.sleep(0.005)
        assert call("/api/status")["state"] == "running"

        if how == "shutdown line":
            proc.stdin.write("shutdown\n")
            proc.stdin.flush()
        else:
            proc.stdin.close()
        deadline = time.monotonic() + 10
        while group_members(proc.pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert group_members(proc.pid) == []
        assert proc.wait(10) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        proc.stdout.close()
