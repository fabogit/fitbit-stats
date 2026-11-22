import argparse
import sys
from datetime import date
from pathlib import Path

import applog
import config
from modules.pipeline import NoDataError, run_pipeline
from modules.run_config import EtlConfig, profile_from_mapping, read_session_config


def progress(pct, msg):
    """Print a progress line (PROGRESS:<percent>:<message>) on stdout for the command line."""
    print(f"PROGRESS:{pct}:{msg}", flush=True)


def build_config(args) -> EtlConfig | None:
    """The configuration of this run, or None when the biometrics are not set.

    Precedence, per value: command line arguments, then session_config.json
    (read from the output folder), then the environment.
    """
    output_dir = Path(args.out_dir or config.CLIENT_PUBLIC_DIR)
    session = read_session_config(output_dir)
    if session:
        print("   -> Loaded session config")

    values = config.profile_values_from_env()
    values.update({k: session[k] for k in ("dob", "gender", "height", "weight") if k in session})
    values.update({k: v for k, v in (("dob", args.dob), ("gender", args.gender),
                                     ("height", args.height), ("weight", args.weight)) if v})
    profile = profile_from_mapping(values)
    if profile is None:
        return None

    return EtlConfig(
        data_dir=Path(args.data_dir or session.get("data_path") or config.default_data_dir()),
        output_dir=output_dir,
        profile=profile,
        start_date=args.start_date or config.date_from_env("START_DATE"),
        end_date=args.end_date or config.date_from_env("END_DATE"),
    )


def main():
    """Entrypoint for the Fitbit Stats ETL Engine: builds the run configuration and runs the pipeline."""
    parser = argparse.ArgumentParser(description="Fitbit Stats ETL Engine")
    parser.add_argument("--data-dir", type=str,
                        help="Directory containing Fitbit JSON exports")
    parser.add_argument("--out-dir", type=str,
                        help="Directory to save dashboard_data.json")
    parser.add_argument("--dob", type=str,
                        help="User Date of Birth (YYYY-MM-DD)")
    parser.add_argument("--height", type=int,
                        help="User height in cm for BMR calculation")
    parser.add_argument("--weight", type=float,
                        help="User weight in kg for BMR calculation default fallback")
    parser.add_argument(
        "--gender", type=str, choices=["male", "female"], help="User gender for BMR calculation")
    parser.add_argument("--start-date", type=date.fromisoformat,
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=date.fromisoformat, help="End date (YYYY-MM-DD)")

    args = parser.parse_args()
    applog.configure_logging(plain=True)  # the messages of the ETL, as plain lines on stderr

    progress(5, "Loading configuration")
    try:
        cfg = build_config(args)
    except ValueError as e:
        print(f"\n[main.py] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Validation: Ensure we have the metrics
    if cfg is None:
        print(
            "\n[main.py] ERROR: Biometric metrics (dob, height, weight, gender) are not set.")
        print("Please provide them via CLI or ensure session_config.json contains them.\n")
        return

    try:
        result = run_pipeline(cfg, progress)
    except NoDataError as e:
        for w in e.warnings:
            print(f"[main.py] WARNING: skipped {w['file']} ({w['reason']})", file=sys.stderr)
        print("[main.py] ERROR: No valid data found in the specified directory.", file=sys.stderr)
        sys.exit(1)

    for w in result.warnings:
        print(f"[main.py] WARNING: skipped {w['file']} ({w['reason']})", file=sys.stderr)

    # Preview
    cols = ['resting_bpm', 'readiness_raw', 'bmr',
            'active_calories', 'sleep_efficiency', 'autonomic_balance']
    print("\n=== HEAD ===")
    print(result.df[[c for c in cols if c in result.df.columns]].head())


if __name__ == "__main__":
    main()
