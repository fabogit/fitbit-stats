import time
import subprocess
import os
import sys

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")


def run_etl():
    """Spawns a subprocess to execute the ETL pipeline using main.py."""
    print("\\n[watch.py] Running ETL...")
    # Pass any arguments down to main.py
    subprocess.run(["python", "main.py"] + sys.argv[1:], check=False)
    print("\\n[watch.py] ETL run complete.")


if not HAS_WATCHDOG:
    print("watchdog module not found, running ETL once and exiting.")
    run_etl()
    sys.exit(0)


class DataHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_run = time.time()

    def on_modified(self, event):
        if event.is_directory:
            return

        # Only trigger on relevant data files
        if not event.src_path.lower().endswith(('.json', '.csv')):
            return

        # Debounce to prevent multiple runs for a single batch of file changes
        current_time = time.time()
        if current_time - self.last_run > 10.0:  # Increased debounce
            self.last_run = current_time
            print(
                f"[watch.py] File modified: {event.src_path}. Triggering ETL in 2s...")
            time.sleep(2)
            run_etl()


if __name__ == "__main__":
    # Ensure dir exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Run ONLY if session_config.json exists (implies user has configured it once)
    if os.path.exists("session_config.json"):
        print("[watch.py] Initializing with existing session config...")
        run_etl()
    else:
        print("[watch.py] No session config found. Waiting for UI configuration...")

    print(f"\n[watch.py] Watching {DATA_DIR} for changes...")
    event_handler = DataHandler()
    observer = Observer()
    observer.schedule(event_handler, path=DATA_DIR, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
