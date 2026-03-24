import argparse
import os
from modules import etl, metrics
import config

import json

def load_session_config():
    config_path = "session_config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                sc = json.load(f)
                config.USER_DOB = sc.get('dob', config.USER_DOB)
                config.USER_HEIGHT_CM = sc.get('height', config.USER_HEIGHT_CM)
                config.USER_WEIGHT_KG = sc.get('weight', config.USER_WEIGHT_KG)
                config.USER_GENDER = sc.get('gender', config.USER_GENDER)
                config.DATA_DIR = sc.get('data_path', config.DATA_DIR)
                print(f"   -> Loaded session config: DOB {config.USER_DOB}, {config.USER_HEIGHT_CM}cm, {config.USER_WEIGHT_KG}kg, {config.USER_GENDER}")
        except Exception as e:
            print(f"Error loading session config: {e}")

def main():
    parser = argparse.ArgumentParser(description="Fitbit Stats ETL Engine")
    parser.add_argument("--data-dir", type=str, help="Directory containing Fitbit JSON exports")
    parser.add_argument("--out-dir", type=str, help="Directory to save dashboard_data.json")
    parser.add_argument("--dob", type=str, help="User Date of Birth (YYYY-MM-DD)")
    parser.add_argument("--height", type=int, help="User height in cm for BMR calculation")
    parser.add_argument("--weight", type=float, help="User weight in kg for BMR calculation default fallback")
    parser.add_argument("--gender", type=str, choices=["male", "female"], help="User gender for BMR calculation")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    # 0. Load shared session config first
    load_session_config()

    # Override with CLI arguments if provided
    if args.data_dir: config.DATA_DIR = args.data_dir
    if args.out_dir: config.CLIENT_PUBLIC_DIR = args.out_dir
    if args.dob: config.USER_DOB = args.dob
    if args.height: config.USER_HEIGHT_CM = args.height
    if args.weight: config.USER_WEIGHT_KG = args.weight
    if args.gender: config.USER_GENDER = args.gender
    if args.start_date: config.START_DATE = args.start_date
    if args.end_date: config.END_DATE = args.end_date

    # Validation: Ensure we have the metrics
    if not config.USER_DOB or not config.USER_HEIGHT_CM or not config.USER_GENDER:
        print("\n[main.py] ERROR: Biometric metrics (dob, height, gender) are not set.")
        print("Please provide them via CLI or ensure session_config.json exists.\n")
        return

    # 1. Load & Merge
    df = etl.merge_all_data()

    if df is not None:
        # 2. Calculate Metrics
        df = metrics.calculate_readiness(df)
        df = metrics.calculate_metabolic_metrics(df)

        # 3. Preview
        cols = ['resting_bpm', 'readiness_raw', 'bmr', 'active_calories']
        print("\n=== HEAD ===")
        print(df[[c for c in cols if c in df.columns]].head())

        # 4. Export
        df.to_csv("fitbit_analysis.csv") # Required for daily_brief.py
        etl.export_to_json(df)

if __name__ == "__main__":
    main()
