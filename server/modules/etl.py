import glob
import os
import pandas as pd
import config
from modules import parsers


def filter_by_date(df):
    """
    Filters the DataFrame based on the configured START_DATE and optional END_DATE.

    Ensures the DataFrame has a valid DatetimeIndex before applying the mask.

    Args:
        df (pd.DataFrame): The DataFrame to filter.

    Returns:
        pd.DataFrame: A new DataFrame containing only rows within the date range.
    """
    if df is None or df.empty:
        return df
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except:
            return df

    mask = None
    if config.START_DATE:
        mask = (df.index >= config.START_DATE)

    if config.END_DATE:
        if mask is not None:
            mask = mask & (df.index <= config.END_DATE)
        else:
            mask = (df.index <= config.END_DATE)

    if mask is not None:
        return df.loc[mask]
    return df


def load_collection(folder_name, file_pattern, parser_func):
    """
    Scans a specific folder for files matching a pattern, parses them,
    and aggregates them into a single DataFrame.

    Handles timezone normalization (stripping timezones) and index deduplication
    to ensure a clean time-series.

    Args:
        folder_name (str): Subfolder name within DATA_DIR.
        file_pattern (str): Glob pattern (e.g., "*.json").
        parser_func (function): Function to parse a single file into a DataFrame.

    Returns:
        pd.DataFrame: Combined and sorted DataFrame for the specific metric.
    """
    search_path = os.path.join(config.DATA_DIR, folder_name, file_pattern)
    files = glob.glob(search_path)
    if not files:
        return pd.DataFrame()

    print(f"   Loading {len(files)} files for {file_pattern}...")

    frames = []
    for f in files:
        try:
            chunk = parser_func(f)
            if chunk is not None and not chunk.empty:
                frames.append(chunk)
        except Exception as e:
            print(f"Error {f}: {e}")

    if not frames:
        return pd.DataFrame()

    full_df = pd.concat(frames)

    # Normalize Timezone (Make naive) to allow merging different sources
    if isinstance(full_df.index, pd.DatetimeIndex) and full_df.index.tz is not None:
        full_df.index = full_df.index.tz_localize(None)

    # Deduplicate index: Keep the last entry if overlaps occur
    if full_df.index.duplicated().any():
        full_df = full_df[~full_df.index.duplicated(keep='last')]

    full_df = full_df.sort_index()
    return full_df


def get_data_date_range():
    """
    Scans the data directory to find the earliest and latest available dates.
    Uses 'calories-*.json' as the reliable anchor for date coverage.
    """
    search_path = os.path.join(
        config.DATA_DIR, "Global Export Data", "calories-*.json")
    files = glob.glob(search_path)
    if not files:
        return None, None

    dates = []
    for f in files:
        try:
            # Extract date from filename: calories-YYYY-MM-DD.json
            date_part = os.path.basename(f).replace(
                'calories-', '').replace('.json', '')
            dates.append(pd.to_datetime(date_part))
        except:
            continue

    if not dates:
        return None, None
    return min(dates).strftime('%Y-%m-%d'), max(dates).strftime('%Y-%m-%d')


def merge_all_data():
    """
    Main ETL Orchestrator.

    1. Defines the loading plan for all metrics (Heart Rate, Sleep, Activity, etc.).
    2. Loads and parses each collection independently.
    3. Merges all collections into a single Master DataFrame using Outer Join.
    4. Fills NaN values with 0 for activity-based columns.
    5. Performs final cleanup to remove empty or future rows based on calorie data.

    Returns:
        pd.DataFrame: The fully processed Master Dataset ready for analysis.
    """
    # Auto-detect date range if not explicitly set
    detected_start, detected_end = get_data_date_range()
    if not config.START_DATE and detected_start:
        config.START_DATE = detected_start
    if not config.END_DATE and detected_end:
        config.END_DATE = detected_end

    date_str = f"{config.START_DATE} to {config.END_DATE}" if config.START_DATE else "All Time"
    print(f"\n=== BUILDING MASTER DATASET ({date_str}) ===")

    # Define Loading Plan: (Folder, Pattern, Parser)
    load_plan = [
        ("Global Export Data", "resting_heart_rate-*.json",
         parsers.parse_resting_heart_rate),
        ("Global Export Data", "heart_rate-*.json",
         parsers.parse_heart_rate_intraday_summary),
        ("Global Export Data", "steps-*.json", parsers.parse_steps_json),
        ("Global Export Data", "distance-*.json", parsers.parse_distance_json),
        ("Global Export Data", "exercise-*.json", parsers.parse_exercise_json),
        ("Global Export Data", "weight-*.json", parsers.parse_weight),
        ("Global Export Data", "calories-*.json", parsers.parse_calories_intraday),
        ("Sleep Score", "sleep_score.csv", parsers.parse_sleep_score_csv),
        ("Global Export Data", "sleep-*.json", parsers.parse_sleep_json_detailed),
        ("Oxygen Saturation (SpO2)", "Daily SpO2 - *.csv", parsers.parse_spo2_csv),
        ("Heart Rate Variability",
         "Daily Heart Rate Variability Summary - *.csv", parsers.parse_hrv_csv),
        ("Stress Score", "Stress Score.csv", parsers.parse_stress_csv),
        ("Global Export Data", "very_active_minutes-*.json",
         parsers.parse_simple_activity_json),
        ("Global Export Data", "moderately_active_minutes-*.json",
         parsers.parse_simple_activity_json),
        ("Global Export Data", "lightly_active_minutes-*.json",
         parsers.parse_simple_activity_json),
        ("Global Export Data", "sedentary_minutes-*.json",
         parsers.parse_simple_activity_json),
        ("Physical Activity_GoogleData",
         "cardio_acute_chronic_workload_ratio.csv", parsers.parse_acwr_csv),
        ("Physical Activity_GoogleData",
         "demographic_vo2max.csv", parsers.parse_vo2max_csv),
        ("Physical Activity_GoogleData",
         "daily_readiness.csv", parsers.parse_readiness_csv),
        ("Physical Activity_GoogleData", "daily_respiratory_rate.csv",
         parsers.parse_respiratory_rate_csv),
        ("Physical Activity_GoogleData", "daily_sleep_temperature_derivations.csv",
         parsers.parse_skin_temperature_csv),
        ("Physical Activity_GoogleData", "time_in_heart_rate_zone_*.csv",
         parsers.parse_active_zones_csv),
    ]

    datasets = []
    for folder, pattern, func in load_plan:
        datasets.append(load_collection(folder, pattern, func))

    # Filter empty datasets
    datasets = [d for d in datasets if not d.empty]
    if not datasets:
        return None

    # Merge Strategy: Outer Join starting from the first non-empty dataset
    master_df = datasets[0]
    for i in range(1, len(datasets)):
        current = datasets[i]
        # Align indexes before merge just in case
        if current.index.duplicated().any():
            current = current.groupby(current.index).mean()
        master_df = master_df.join(current, how='outer')

    master_df = filter_by_date(master_df)

    # Fill NaNs for activity and sleep metrics (logical 0)
    cols_zero = [
        'very_active_minutes', 'moderately_active_minutes', 'lightly_active_minutes', 'sedentary_minutes',
        'calories_total', 'sleep_deep', 'sleep_light', 'sleep_rem', 'sleep_awake',
        'zone_out_of_range', 'zone_fat_burn', 'zone_cardio', 'zone_peak', 'zone_light',
        'steps', 'distance', 'exercise_duration', 'exercise_calories', 'exercise_count'
    ]
    for c in cols_zero:
        if c in master_df.columns:
            master_df[c] = master_df[c].fillna(0)

    # Final Cleanup: Remove rows where no calories were burned (implies no data recorded)
    if 'calories_total' in master_df.columns:
        initial = len(master_df)
        master_df = master_df[master_df['calories_total'] > 0]
        if len(master_df) < initial:
            print(f"   -> Cleaned {initial - len(master_df)} empty rows.")

    return master_df


def export_to_json(df):
    """
    Exports the processed Master DataFrame to a JSON file format suitable for the React Dashboard.

    The file is saved directly to the client's public folder so it can be served via HTTP.

    Args:
        df (pd.DataFrame): The Master Dataset to export.
    """
    output_path = os.path.join(config.CLIENT_PUBLIC_DIR, "dashboard_data.json")
    if not os.path.exists(config.CLIENT_PUBLIC_DIR):
        os.makedirs(config.CLIENT_PUBLIC_DIR, exist_ok=True)

    # Reset index to include 'date' as a column in the JSON
    export_df = df.reset_index()
    export_df['date'] = export_df['date'].dt.strftime('%Y-%m-%d')

    export_df.to_json(output_path, orient='records')
    print(f"-> Dashboard JSON exported to: {output_path}")

    # ALSO: If a 'dist' folder exists (production build), update it too!
    # This ensures that even after a build, the dashboard remains fresh.
    dist_dir = config.CLIENT_PUBLIC_DIR.replace("public", "dist")
    if os.path.exists(dist_dir):
        dist_path = os.path.join(dist_dir, "dashboard_data.json")
        export_df.to_json(dist_path, orient='records')
        print(f"-> Syncing to production build: {dist_path}")
