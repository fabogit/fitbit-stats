import argparse
import os
import sys
from modules import etl, metrics
from modules.run_config import Profile
import config

import json
from datetime import date


def load_session_config():
    """Loads biometric properties from the local session_config.json if available."""
    config_path = os.path.join(config.CLIENT_PUBLIC_DIR, "session_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                sc = json.load(f)
                config.USER_DOB = sc.get('dob', config.USER_DOB)
                config.USER_HEIGHT_CM = sc.get('height', config.USER_HEIGHT_CM)
                config.USER_WEIGHT_KG = sc.get('weight', config.USER_WEIGHT_KG)
                config.USER_GENDER = sc.get('gender', config.USER_GENDER)
                config.DATA_DIR = sc.get('data_path', config.DATA_DIR)
                print(
                    f"   -> Loaded session config: DOB {config.USER_DOB}, {config.USER_HEIGHT_CM}cm, {config.USER_WEIGHT_KG}kg, {config.USER_GENDER}")
        except Exception as e:
            print(f"Error loading session config: {e}")


def progress(pct, msg):
    """Emit a structured progress line for the API to parse and broadcast via WebSocket."""
    print(f"PROGRESS:{pct}:{msg}", flush=True)


def main():
    """Entrypoint for the Fitbit Stats ETL Engine. Orchestrates data merging, metric calculation, and output export."""
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
    parser.add_argument("--start-date", type=str,
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    # 0. Load shared session config first
    progress(5, "Loading configuration")
    load_session_config()

    # Override with CLI arguments if provided
    if args.data_dir:
        config.DATA_DIR = args.data_dir
    if args.out_dir:
        config.CLIENT_PUBLIC_DIR = args.out_dir
    if args.dob:
        config.USER_DOB = args.dob
    if args.height:
        config.USER_HEIGHT_CM = args.height
    if args.weight:
        config.USER_WEIGHT_KG = args.weight
    if args.gender:
        config.USER_GENDER = args.gender
    if args.start_date:
        config.START_DATE = args.start_date
    if args.end_date:
        config.END_DATE = args.end_date

    # Validation: Ensure we have the metrics
    if not config.USER_DOB or not config.USER_HEIGHT_CM or not config.USER_GENDER or not config.USER_WEIGHT_KG:
        print(
            "\n[main.py] ERROR: Biometric metrics (dob, height, weight, gender) are not set.")
        print("Please provide them via CLI or ensure session_config.json contains them.\n")
        return

    profile = Profile(dob=date.fromisoformat(config.USER_DOB), gender=config.USER_GENDER,
                      height_cm=config.USER_HEIGHT_CM, weight_kg=config.USER_WEIGHT_KG)

    # 1. Load & Merge
    progress(10, "Loading and merging data files")
    warnings = []
    start = date.fromisoformat(config.START_DATE) if config.START_DATE else None
    end = date.fromisoformat(config.END_DATE) if config.END_DATE else None
    df = etl.merge_all_data(config.DATA_DIR, start, end, progress_callback=progress, warnings=warnings)
    etl.export_warnings(warnings, config.CLIENT_PUBLIC_DIR)
    for w in warnings:
        print(f"[main.py] WARNING: skipped {w['file']} ({w['reason']})", file=sys.stderr)

    if df is not None:
        # 2. Calculate Metrics
        progress(70, "Calculating readiness metrics")
        df = metrics.calculate_readiness(df)

        progress(75, "Calculating metabolic metrics")
        df = metrics.calculate_metabolic_metrics(df, profile)

        progress(80, "Calculating advanced metrics")
        df = metrics.calculate_advanced_metrics(df)

        # 3. Preview
        cols = ['resting_bpm', 'readiness_raw', 'bmr',
                'active_calories', 'sleep_efficiency', 'autonomic_balance']
        print("\n=== HEAD ===")
        print(df[[c for c in cols if c in df.columns]].head())

        # 4. Export
        progress(90, "Exporting analysis CSV")
        # Required for BRIEFING module, which reads it from CLIENT_PUBLIC_DIR
        os.makedirs(config.CLIENT_PUBLIC_DIR, exist_ok=True)
        df.to_csv(os.path.join(config.CLIENT_PUBLIC_DIR, "fitbit_analysis.csv"))

        progress(95, "Exporting dashboard JSON")
        etl.export_to_json(df, config.CLIENT_PUBLIC_DIR)

        progress(100, "Complete")
    else:
        print("[main.py] ERROR: No valid data found in the specified directory.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
