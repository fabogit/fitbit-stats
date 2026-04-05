# backend/modules/parsers.py
import json
import pandas as pd
import os


def parse_resting_heart_rate(file_path):
    """
    Parses 'resting_heart_rate-YYYY-MM-DD.json'.

    Structure: Nested JSON where daily values are inside 'value' -> 'value'.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        pd.DataFrame: A DataFrame indexed by 'date' with a 'resting_bpm' column.
                      Returns None if no valid records are found.
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
    Parses 'weight-YYYY-MM-DD.json'.

    IMPORTANT: Automatically converts weight from Pounds (Lbs) to Kilograms (Kg).

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        pd.DataFrame: Indexed by 'date' with 'weight' (in Kg) and 'bmi'.
                      Duplicates (multiple weigh-ins per day) are removed, keeping the first.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    if df.empty:
        return None
    df = df[['date', 'weight', 'bmi']]
    # Conversion LBS -> KG
    df['weight'] = (df['weight'] * 0.453592).round(1)
    df['date'] = pd.to_datetime(df['date'], format='%m/%d/%y')
    df.set_index('date', inplace=True)
    return df[~df.index.duplicated(keep='first')]


def parse_sleep_score_csv(file_path):
    """
    Parses 'sleep_score.csv'.

    This file contains the overall sleep quality score calculated by Fitbit.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Indexed by 'date', containing 'overall_score',
                      'deep_sleep_in_minutes', and 'restlessness'.
                      Aggregates multiple entries per day using max().
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    df.rename(columns={'timestamp': 'date'}, inplace=True)
    df['date'] = pd.to_datetime(
        df['date'], format='ISO8601', utc=True).dt.tz_convert(None).dt.normalize()
    cols = [c for c in ['overall_score', 'deep_sleep_in_minutes',
                        'restlessness'] if c in df.columns]
    df = df[cols + ['date']]
    return df.groupby('date').max()  # Simplified aggregation


def parse_simple_activity_json(file_path):
    """
    Parses simple daily activity files (e.g., 'very_active_minutes.json', 'sedentary_minutes.json').

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        pd.DataFrame: Indexed by 'date' with a single column named after the
                      activity type (derived from filename).
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    if df.empty:
        return None
    base_name = os.path.basename(file_path).split('-')[0]
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['date'] = pd.to_datetime(
        df['dateTime'], format='%m/%d/%y %H:%M:%S').dt.normalize()
    df.set_index('date', inplace=True)
    df.rename(columns={'value': base_name}, inplace=True)
    return df[[base_name]]


def parse_heart_rate_intraday_summary(file_path):
    """
    Parses 'heart_rate-YYYY-MM-DD.json' to get Daily Min, Max, and Avg BPM.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    if not data:
        return None

    # Intraday detail is inside 'value' -> 'bpm'
    records = []
    for entry in data:
        dt = entry.get('dateTime')
        val = entry.get('value', {})
        bpm = val.get('bpm')
        if dt and bpm:
            records.append({'dateTime': dt, 'bpm': bpm})

    if not records:
        return None
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(
        df['dateTime'], format='%m/%d/%y %H:%M:%S').dt.normalize()

    stats = df.groupby('date')['bpm'].agg(['min', 'max', 'mean']).reset_index()
    stats.rename(columns={'min': 'min_bpm',
                 'max': 'max_bpm', 'mean': 'avg_bpm'}, inplace=True)
    stats['avg_bpm'] = stats['avg_bpm'].round(1)
    stats.set_index('date', inplace=True)
    return stats


def parse_active_zones_csv(file_path):
    """
    Parses 'time_in_heart_rate_zone-YYYY-MM-DD.csv' (minute-by-minute logs).
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    if 'heart rate zone type' not in df.columns:
        return None

    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()

    # Group by date and zone type, count minutes (each row is 1 min)
    zone_map = {
        'OUT_OF_RANGE': 'zone_out_of_range',
        'FAT_BURN': 'zone_fat_burn',
        'CARDIO': 'zone_cardio',
        'PEAK': 'zone_peak',
        'LIGHT': 'zone_light'
    }

    # Pivot to get zones as columns
    pivot = df.groupby(['date', 'heart rate zone type']
                       ).size().unstack(fill_value=0)

    # Rename columns based on map
    rename_cols = {col: zone_map.get(
        col, f"zone_{col.lower().replace(' ', '_')}") for col in pivot.columns}
    pivot.rename(columns=rename_cols, inplace=True)

    return pivot


def parse_spo2_csv(file_path):
    """
    Parses 'Daily SpO2 - ... .csv'.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Indexed by 'date' with 'spo2_avg', 'spo2_min', 'spo2_max'.
                      Handles duplicates by averaging values.
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    df['date'] = pd.to_datetime(
        df['timestamp'], utc=True).dt.tz_convert(None).dt.normalize()
    df.rename(columns={'average_value': 'spo2_avg',
              'lower_bound': 'spo2_min', 'upper_bound': 'spo2_max'}, inplace=True)
    return df[['spo2_avg', 'spo2_min', 'spo2_max', 'date']].groupby('date').mean()


def parse_calories_intraday(file_path):
    """
    Parses 'calories-YYYY-MM-DD.json'.

    Input data is minute-by-minute. This function aggregates it to daily totals.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        pd.DataFrame: Indexed by 'date' with 'calories_total' (sum of the day).
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    if df.empty:
        return None
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['date'] = pd.to_datetime(
        df['dateTime'], format='%m/%d/%y %H:%M:%S').dt.normalize()
    return df.groupby('date')['value'].sum().reset_index().rename(columns={'value': 'calories_total'}).set_index('date')


def parse_sleep_json_detailed(file_path):
    """
    Parses 'sleep-YYYY-MM-DD.json' (Detailed Logs).

    Extracts specific sleep stages: Deep, Light, REM, and Awake.
    Handles mapping differences between 'classic' logs (naps) and 'stages' logs.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        pd.DataFrame: Indexed by 'date' with columns: 'sleep_deep', 'sleep_light',
                      'sleep_rem', 'sleep_awake'. Aggregates multiple sessions per day via sum().
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    records = []
    for entry in data:
        date_str = entry.get('dateOfSleep')
        summary = entry.get('levels', {}).get('summary', {})
        if date_str:
            light = summary.get('light', {}).get(
                'minutes', 0) + summary.get('asleep', {}).get('minutes', 0)
            deep = summary.get('deep', {}).get('minutes', 0)
            rem = summary.get('rem', {}).get('minutes', 0)
            awake = summary.get('wake', {}).get('minutes', 0) + summary.get(
                'awake', {}).get('minutes', 0) + summary.get('restless', {}).get('minutes', 0)
            records.append({'date': date_str, 'sleep_deep': deep,
                           'sleep_light': light, 'sleep_rem': rem, 'sleep_awake': awake})
    if not records:
        return None
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    df.set_index('date', inplace=True)
    return df.groupby('date').sum()


def parse_hrv_csv(file_path):
    """
    Parses 'Daily Heart Rate Variability Summary - ... .csv'.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Indexed by 'date' with 'rmssd' (Root Mean Square of Successive Differences).
                      Higher rMSSD generally indicates better recovery.
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    if 'rmssd' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df.set_index('date', inplace=True)
    return df[['rmssd']]


def parse_stress_csv(file_path):
    """
    Parses 'Stress Score.csv'.

    Filters out entries with 'NO_DATA' status or 0 score.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Indexed by 'date' with 'stress_score'.
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    df.columns = df.columns.str.strip()
    if 'DATE' not in df.columns or 'STRESS_SCORE' not in df.columns:
        return None
    df = df[df['STRESS_SCORE'] > 0]
    df['date'] = pd.to_datetime(df['DATE']).dt.normalize()
    df.set_index('date', inplace=True)
    df.rename(columns={'STRESS_SCORE': 'stress_score'}, inplace=True)
    return df[['stress_score']]


def parse_acwr_csv(file_path):
    """
    Parses 'cardio_acute_chronic_workload_ratio.csv'.
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    if 'ratio' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df.rename(columns={'ratio': 'acwr_ratio'}, inplace=True)
    df.set_index('date', inplace=True)
    return df[['acwr_ratio']]


def parse_vo2max_csv(file_path):
    """
    Parses 'demographic_vo2max.csv'.
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    if 'demographic vo2max' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df.rename(columns={'demographic vo2max': 'vo2max'}, inplace=True)
    df.set_index('date', inplace=True)
    return df[['vo2max']]


def parse_readiness_csv(file_path):
    """
    Parses 'daily_readiness.csv' to extract the true Fitbit Readiness Score.
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    if 'score' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df.rename(columns={'score': 'readiness_score'}, inplace=True)
    df.set_index('date', inplace=True)
    return df[['readiness_score']]


def parse_respiratory_rate_csv(file_path):
    """
    Parses 'daily_respiratory_rate.csv' for breath tracking.
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    if 'breaths per minute' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df.rename(columns={'breaths per minute': 'respiratory_rate'}, inplace=True)
    df.set_index('date', inplace=True)
    return df[['respiratory_rate']]


def parse_skin_temperature_csv(file_path):
    """
    Parses 'daily_sleep_temperature_derivations.csv' and calculates the variation.
    """
    try:
        df = pd.read_csv(file_path)
    except:
        return None
    if 'nightly temperature celsius' not in df.columns or 'baseline temperature celsius' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df['temperature_variation'] = df['nightly temperature celsius'] - \
        df['baseline temperature celsius']
    df.set_index('date', inplace=True)
    return df[['temperature_variation']]
