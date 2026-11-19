import os
import subprocess
import sys
import threading
import time

import config

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    FileSystemEventHandler = object

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

# Seconds without any file event before the ETL starts. The timer restarts on
# every event, so a long copy produces a single run once it has finished.
QUIET_SECONDS = float(os.environ.get("WATCH_QUIET_SECONDS", "5"))

DATA_EXTENSIONS = (".json", ".csv")


def session_config_path():
    """The API writes session_config.json into CLIENT_PUBLIC_DIR."""
    return os.path.join(config.CLIENT_PUBLIC_DIR, "session_config.json")


def run_etl():
    """Spawns a subprocess to execute the ETL pipeline using main.py."""
    print("\n[watch.py] Running ETL...", flush=True)
    # Pass any arguments down to main.py
    subprocess.run([sys.executable, "main.py"] + sys.argv[1:], check=False)
    print("\n[watch.py] ETL run complete.", flush=True)


class QuietPeriodTrigger:
    """Runs `action` once, `quiet` seconds after the last call to `poke()`.

    Every poke cancels the pending timer and starts a new one. Runs are
    serialised: pokes that arrive while the action is running schedule another
    run afterwards, so changes made during a run are never lost.
    """

    def __init__(self, action, quiet=QUIET_SECONDS):
        self.action = action
        self.quiet = quiet
        self._lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._timer = None

    def poke(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.quiet, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def cancel(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _fire(self):
        with self._run_lock:
            self.action()


class DataHandler(FileSystemEventHandler):
    def __init__(self, trigger=None):
        self.trigger = trigger or QuietPeriodTrigger(run_etl)

    def _handle(self, event, path):
        if event.is_directory:
            return
        # Only trigger on relevant data files
        if not str(path).lower().endswith(DATA_EXTENSIONS):
            return
        print(f"[watch.py] Change detected: {path}. "
              f"ETL starts after {self.trigger.quiet:g}s without changes.", flush=True)
        self.trigger.poke()

    def on_created(self, event):
        self._handle(event, event.src_path)

    def on_modified(self, event):
        self._handle(event, event.src_path)

    def on_moved(self, event):
        self._handle(event, event.dest_path)


if __name__ == "__main__":
    if not HAS_WATCHDOG:
        print("watchdog module not found, running ETL once and exiting.")
        run_etl()
        sys.exit(0)

    # Ensure dir exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Run ONLY if session_config.json exists (implies user has configured it once)
    if os.path.exists(session_config_path()):
        print("[watch.py] Initializing with existing session config...", flush=True)
        run_etl()
    else:
        print("[watch.py] No session config found. Waiting for UI configuration...", flush=True)

    print(f"\n[watch.py] Watching {DATA_DIR} for changes...", flush=True)
    event_handler = DataHandler()
    observer = Observer()
    observer.schedule(event_handler, path=DATA_DIR, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        event_handler.trigger.cancel()
        observer.stop()
    observer.join()
