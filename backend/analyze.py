import os
import json
import glob

import pandas as pd

# ==========================================
# 1. CONFIGURATION
# ==========================================
# Base directory for data
DATA_DIR = "data"

# Analysis timeframe
START_DATE = "2024-04-01"
END_DATE = None

# ==========================================
# 1.1 USER METRICS (For BMR Calculation)
# ==========================================
# Mifflin-St Jeor Equation constants
USER_HEIGHT_CM = 180   # Update with your height
USER_AGE = 38          # Update with your age
USER_GENDER = 'male'   # 'male' or 'female'

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================


def filter_by_date(df):
    """
    Filters the DataFrame based on START_DATE and optionally END_DATE.
    Expects the DataFrame to have a DateTimeIndex.
    """
    if df is None or df.empty:
        return df

    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception as e:
            print(f"Error converting index to datetime: {e}")
            return df

    # Logic: Start Date is mandatory, End Date is optional
    if END_DATE:
        mask = (df.index >= START_DATE) & (df.index <= END_DATE)
    else:
        mask = (df.index >= START_DATE)

    return df.loc[mask]


def load_collection(folder_name, file_pattern, parser_func):
    """
    Generic engine to load multiple files.
    UPDATED: Includes a final deduplication safety net.
    """
    search_path = os.path.join(DATA_DIR, folder_name, file_pattern)
    files = glob.glob(search_path)

    if not files:
        print(f"Warning: No files found for pattern: {search_path}")
        return pd.DataFrame()

    print(f"Found {len(files)} files for {file_pattern}...")

    all_data_frames = []

    for file_path in files:
        try:
            df_chunk = parser_func(file_path)
            if df_chunk is not None and not df_chunk.empty:
                all_data_frames.append(df_chunk)
        except Exception as e:
            print(f"Error processing file {os.path.basename(file_path)}: {e}")

    if not all_data_frames:
        return pd.DataFrame()

    full_df = pd.concat(all_data_frames)

    # Force timezone removal
    if isinstance(full_df.index, pd.DatetimeIndex) and full_df.index.tz is not None:
        full_df.index = full_df.index.tz_localize(None)

    # === SAFETY NET: DEDUPLICATE INDEX ===
    # If duplicated days persist (e.g. from multiple files), keep the last or average.
    # We choose to keep the last loaded for simplicity, assuming data is sequential.
    if full_df.index.duplicated().any():
        print(
            f"   -> Note: Removed {full_df.index.duplicated().sum()} duplicate index entries.")
        full_df = full_df[~full_df.index.duplicated(keep='last')]
    # =====================================

    if not full_df.empty:
        full_df = full_df.sort_index()

    filtered_df = filter_by_date(full_df)

    print(
        f"-> Loaded {len(filtered_df)} rows for {file_pattern} (Filtered {START_DATE} to {END_DATE})")
    return filtered_df

# ==========================================
# 3. SPECIFIC PARSERS
# ==========================================


def parse_resting_heart_rate(file_path):
    """
    Parser for 'resting_heart_rate-*.json'.
    Structure: List of objects where 'value' contains 'date' and 'value'.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    records = []
    for entry in data:
        val_obj = entry.get('value', {})
        date_str = val_obj.get('date')
        bpm = val_obj.get('value')

        if date_str and bpm:
            records.append({'date': date_str, 'resting_bpm': bpm})

    if not records:
        return None

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'], format='%m/%d/%y')
    df.set_index('date', inplace=True)
    return df

def parse_weight(file_path):
    """
    Parser for 'weight-*.json'.
    NOTE: Fitbit often exports in LBS. We convert to KG immediately.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    if df.empty:
        return None

    # Keep necessary columns
    df = df[['date', 'weight', 'bmi']]

    # === CONVERSION: LBS -> KG ===
    # Assume raw data is in pounds if the value is > 100 with a normal BMI.
    # (Or always apply if you're sure the export is in pounds.)
    df['weight'] = df['weight'] * 0.453592
    df['weight'] = df['weight'].round(1)
    # ==============================

    df['date'] = pd.to_datetime(df['date'], format='%m/%d/%y')
    df.set_index('date', inplace=True)

    # Deduplicate: keep first reading of the day
    df = df[~df.index.duplicated(keep='first')]
    return df

def parse_sleep_score_csv(file_path):
    """
    Parser for 'sleep_score.csv'.
    Handles duplicates (naps) by aggregating.
    Logic: Sum minutes, Max score.
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Skipping bad CSV {file_path}: {e}")
        return None

    df.rename(columns={'timestamp': 'date'}, inplace=True)

    # Parse ISO8601 and remove timezone
    df['date'] = pd.to_datetime(df['date'], format='ISO8601', utc=True)
    df['date'] = df['date'].dt.tz_convert(None).dt.normalize()

    # Keep useful columns
    cols_to_keep = ['overall_score', 'deep_sleep_in_minutes', 'restlessness']
    cols = [c for c in cols_to_keep if c in df.columns]
    df = df[cols + ['date']]  # Ensure date is kept for grouping

    # === AGGREGATE DUPLICATES (NAPS) ===
    # Define how to aggregate each column
    agg_rules = {
        # Keep the best score of the day (Main Sleep)
        'overall_score': 'max',
        'deep_sleep_in_minutes': 'sum',  # Sum deep sleep from all sessions
        'restlessness': 'mean'           # Average restlessness
    }
    # Only use rules for columns that actually exist
    actual_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
    df = df.groupby('date').agg(actual_rules)

    return df


def parse_simple_activity_json(file_path):
    """
    Parser for simple daily summaries (sedentary, very active, etc).
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    if df.empty:
        return None

    base_name = os.path.basename(file_path).split('-')[0]
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Explicit format matches "09/26/25 00:00:00"
    df['date'] = pd.to_datetime(
        df['dateTime'], format='%m/%d/%y %H:%M:%S').dt.normalize()

    df.set_index('date', inplace=True)
    df.rename(columns={'value': base_name}, inplace=True)
    return df[[base_name]]


def parse_spo2_csv(file_path):
    """
    Parser for 'Daily SpO2 - *.csv'.
    Handles duplicates by averaging.
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None

    # Load as UTC explicitly, then convert to None (Naive)
    df['date'] = pd.to_datetime(
        df['timestamp'], utc=True).dt.tz_convert(None).dt.normalize()

    df.rename(columns={
        'average_value': 'spo2_avg',
        'lower_bound': 'spo2_min',
        'upper_bound': 'spo2_max'
    }, inplace=True)

    cols = ['spo2_avg', 'spo2_min', 'spo2_max', 'date']
    df = df[cols]
    df = df.groupby('date').mean()

    return df


def parse_calories_intraday(file_path):
    """
    Parser for 'calories-*.json'. Aggregates minute-by-minute data.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    if df.empty:
        return None

    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['dateTime'] = pd.to_datetime(df['dateTime'], format='%m/%d/%y %H:%M:%S')
    df['date'] = df['dateTime'].dt.normalize()

    daily_cals = df.groupby('date')['value'].sum().reset_index()
    daily_cals.rename(columns={'value': 'calories_total'}, inplace=True)
    daily_cals.set_index('date', inplace=True)
    return daily_cals

# ==========================================
# 4. ANALYSIS LOGIC
# ==========================================


def calculate_readiness(df):
    """
    Calculates 'Readiness' score based on Sleep and RHR Z-Scores.
    """
    if 'overall_score' not in df.columns or 'resting_bpm' not in df.columns:
        print("Cannot calculate Readiness: Missing Sleep or RHR columns.")
        return df

    # Z-Scores: (Value - Mean) / StdDev
    sleep_z = (df['overall_score'] - df['overall_score'].mean()
               ) / df['overall_score'].std()

    # Invert RHR (lower is better)
    rhr_z = (df['resting_bpm'] - df['resting_bpm'].mean()) / \
        df['resting_bpm'].std()

    # Readiness = Good Sleep (+Z) - Bad Heart Rate (+Z)
    df['readiness_raw'] = sleep_z - rhr_z
    return df


def calculate_metabolic_metrics(df):
    """
    Calculates metabolic stats: BMR, Active Calories, and Intensity Index.
    Uses Mifflin-St Jeor Equation for BMR.
    """
    # 1. Handle missing weights for daily BMR calculation
    # We forward-fill (use yesterday's weight) then backward-fill (for start of data)
    if 'weight' in df.columns:
        df['weight_filled'] = df['weight'].ffill().bfill()
    else:
        # Fallback if no weight data exists at all (use a default value)
        df['weight_filled'] = 79.0

    # 2. Calculate BMR (Basal Metabolic Rate)
    # Formula: (10 * weight) + (6.25 * height) - (5 * age) + s
    # s is +5 for males, -161 for females
    s = 5 if USER_GENDER == 'male' else -161

    df['bmr'] = (10 * df['weight_filled']) + (6.25 * USER_HEIGHT_CM) - (5 * USER_AGE) + s

    # 3. Calculate Active Calories
    # Active = Total Burned - BMR
    # Clip at 0 to prevent negative numbers if data is weird
    df['active_calories'] = (df['calories_total'] - df['bmr']).clip(lower=0)

    # 4. Calculate Intensity Index (Calories / Active Minute)
    # First, ensure we have all columns to avoid KeyErrors
    cols = ['lightly_active_minutes', 'moderately_active_minutes', 'very_active_minutes']
    for col in cols:
        if col not in df.columns: df[col] = 0.0

    df['total_active_minutes'] = (
        df['lightly_active_minutes'] +
        df['moderately_active_minutes'] +
        df['very_active_minutes']
    )

    # Calculate index (handle division by zero)
    df['intensity_index'] = df.apply(
        lambda row: row['active_calories'] / row['total_active_minutes']
        if row['total_active_minutes'] > 0 else 0, axis=1
    )

    return df


def merge_all_data():
    """
    Orchestrates loading all metrics and merging them into a Master DataFrame.
    """
    print(f"\n=== BUILDING MASTER DATASET ({START_DATE} to {END_DATE}) ===")

    datasets = [
        load_collection("Global Export Data", "resting_heart_rate-*.json", parse_resting_heart_rate),
        load_collection("Global Export Data", "weight-*.json", parse_weight),
        load_collection("Global Export Data", "calories-*.json", parse_calories_intraday),
        load_collection("Sleep Score", "sleep_score.csv", parse_sleep_score_csv),
        load_collection("Oxygen Saturation (SpO2)", "Daily SpO2 - *.csv", parse_spo2_csv),

        # Activity Minutes (All Zones)
        load_collection("Global Export Data", "very_active_minutes-*.json", parse_simple_activity_json),
        load_collection("Global Export Data", "moderately_active_minutes-*.json", parse_simple_activity_json),
        load_collection("Global Export Data", "lightly_active_minutes-*.json", parse_simple_activity_json),
        load_collection("Global Export Data", "sedentary_minutes-*.json", parse_simple_activity_json),
    ]

    # Filter out empty loads
    datasets = [d for d in datasets if d is not None and not d.empty]

    if not datasets:
        print("No data loaded!")
        return None

    # Merge
    master_df = datasets[0]
    for i in range(1, len(datasets)):
        current_df = datasets[i]
        # Safety check for duplicates in chunk
        if current_df.index.duplicated().any():
            current_df = current_df.groupby(current_df.index).mean()
        master_df = master_df.join(current_df, how='outer')

    # Filter Date Range
    master_df = filter_by_date(master_df)

    # Fill NaNs for activity metrics (logical 0)
    cols_zero_fill = [
        'very_active_minutes', 'moderately_active_minutes',
        'lightly_active_minutes', 'sedentary_minutes',
        'calories_total'
    ]
    for c in cols_zero_fill:
        if c in master_df.columns:
            master_df[c] = master_df[c].fillna(0)

    # Final Deduplication
    if master_df.index.duplicated().any():
        print("Resolving final index duplicates via Mean...")
        master_df = master_df.groupby(master_df.index).mean()

    if 'calories_total' in master_df.columns:
        initial_rows = len(master_df)
        master_df = master_df[master_df['calories_total'] > 0]
        dropped = initial_rows - len(master_df)
        if dropped > 0:
            print(f"   -> Cleaned {dropped} empty/future rows based on 0 calories.")

    print(f"-> Master Dataset created with {master_df.shape[0]} days and {master_df.shape[1]} columns.")
    return master_df


def export_to_json(df):
    """
    Exports the Master DataFrame to a JSON file for the React App.
    Path: ../client/public/dashboard_data.json (Relative to backend/)
    """
    output_dir = os.path.join("..", "client", "public")
    output_path = os.path.join(output_dir, "dashboard_data.json")

    # Create dashboard folder if not exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Reset index to make 'date' a column, then format it as string (YYYY-MM-DD)
    # This makes it easier for JS to read
    export_df = df.reset_index()
    export_df['date'] = export_df['date'].dt.strftime('%Y-%m-%d')

    # Export to JSON (Records format: [{date: '...', rhr: 60}, {date: '...', rhr: 61}])
    export_df.to_json(output_path, orient='records')
    print(f"-> Dashboard data exported to: {output_path}")


# ==========================================
# 5. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    # 1. Build Data
    df = merge_all_data()

    if df is not None:
        # 2. Calculate Metrics
        df = calculate_readiness(df)
        df = calculate_metabolic_metrics(df)

        # 3. Display Results (Console)
        print("\n=== ANALYSIS RESULT HEAD ===")
        print(df[['resting_bpm', 'readiness_raw', 'bmr', 'active_calories', 'intensity_index']].head())

        # 4. Save to CSV (Archive)
        df.to_csv("fitbit_analysis.csv")
        print(f"\nSaved CSV analysis.")

        # 5. Export JSON for Dashboard
        export_to_json(df)