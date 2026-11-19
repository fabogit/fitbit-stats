# backend/modules/parsers.py
import json
from typing import NamedTuple

import pandas as pd
import os

from modules.sources import Source


def _read_csv(file_path):
    """Read a CSV file; a file that cannot be read raises, it is never skipped silently.

    The ETL catches the error per file and reports the file as a warning.
    """
    try:
        return pd.read_csv(file_path)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as e:
        raise ValueError(f"not a readable CSV file ({type(e).__name__})") from e


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
    df = df.set_index('date')
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
    df = df.set_index('date')
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
    df = _read_csv(file_path)
    df = df.rename(columns={'timestamp': 'date'})
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
    df = df.set_index('date')
    df = df.rename(columns={'value': base_name})
    return df[[base_name]]


def parse_heart_rate_intraday(file_path):
    """
    Parses 'heart_rate-YYYY-MM-DD.json': daily min, max and average BPM.

    Returns a DataFrame indexed by 'date' with 'min_bpm', 'max_bpm' and
    'avg_bpm', plus two helper columns, '_bpm_sum' and '_bpm_n' (sum and count
    of the day's samples in this file). They let the ETL recompute the average
    of a day that is split across two files; the ETL drops every column that
    starts with an underscore. Returns None when the file has no valid samples.

    This source is about 94% of the ETL time, so the ~33,000 samples per file
    are aggregated with plain dicts keyed by day instead of building a pandas
    DataFrame and converting every timestamp. Output is identical to the old
    pandas implementation (avg_bpm rounded to one decimal).
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    if not data:
        return None

    # Intraday detail is inside 'value' -> 'bpm'. Timestamps look like
    # 'MM/DD/YY HH:MM:SS', so the first 8 characters identify the day.
    acc = {}
    for entry in data:
        dt = entry.get('dateTime')
        bpm = entry.get('value', {}).get('bpm')
        if not dt or not bpm:
            continue
        day = dt[:8]
        a = acc.get(day)
        if a is None:
            acc[day] = [bpm, bpm, bpm, 1]
        else:
            if bpm < a[0]:
                a[0] = bpm
            if bpm > a[1]:
                a[1] = bpm
            a[2] += bpm
            a[3] += 1

    if not acc:
        return None
    days = sorted(acc, key=lambda d: (d[6:8], d[0:2], d[3:5]))
    index = pd.to_datetime(days, format='%m/%d/%y')
    index.name = 'date'
    return pd.DataFrame({
        'min_bpm': [acc[d][0] for d in days],
        'max_bpm': [acc[d][1] for d in days],
        'avg_bpm': [round(acc[d][2] / acc[d][3], 1) for d in days],
        '_bpm_sum': [acc[d][2] for d in days],
        '_bpm_n': [acc[d][3] for d in days],
    }, index=index)


# Current export names (OUT_OF_RANGE, LIGHT, MODERATE, VIGOROUS) plus the
# older FAT_BURN, CARDIO and PEAK, which are still accepted.
ZONE_NAMES = {
    'OUT_OF_RANGE': 'zone_out_of_range',
    'LIGHT': 'zone_light',
    'MODERATE': 'zone_moderate',
    'VIGOROUS': 'zone_vigorous',
    'FAT_BURN': 'zone_fat_burn',
    'CARDIO': 'zone_cardio',
    'PEAK': 'zone_peak',
}


def parse_active_zones_csv(file_path):
    """
    Parses 'time_in_heart_rate_zone-YYYY-MM-DD.csv' (minute-by-minute logs).
    """
    df = _read_csv(file_path)
    if 'heart rate zone type' not in df.columns:
        return None

    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()

    # Group by date and zone type, count minutes (each row is 1 min)
    # Pivot to get zones as columns
    pivot = df.groupby(['date', 'heart rate zone type']
                       ).size().unstack(fill_value=0)

    # Rename columns based on map
    rename_cols = {col: ZONE_NAMES.get(
        col, f"zone_{col.lower().replace(' ', '_')}") for col in pivot.columns}
    pivot = pivot.rename(columns=rename_cols)

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
    df = _read_csv(file_path)
    df['date'] = pd.to_datetime(
        df['timestamp'], utc=True).dt.tz_convert(None).dt.normalize()
    df = df.rename(columns={'average_value': 'spo2_avg',
                            'lower_bound': 'spo2_min', 'upper_bound': 'spo2_max'})
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


class SleepSession(NamedTuple):
    log_id: object
    deep: int
    light: int
    rem: int
    awake: int


def parse_sleep_stages(file_path):
    """
    Parses 'sleep-YYYY-MM-DD.json' (Detailed Logs).

    Extracts specific sleep stages: Deep, Light, REM and Awake, in minutes.
    Handles mapping differences between 'classic' logs (naps) and 'stages' logs
    (asleep counts as light, awake and restless as awake). A day's sessions are
    added up.

    Returns a DataFrame indexed by 'date' with 'sleep_deep', 'sleep_light',
    'sleep_rem' and 'sleep_awake', plus a helper column '_sessions': for each
    day, the list of SleepSession (logId, deep, light, rem, awake) of its
    sessions in this file. Consecutive export files can both contain the same
    session; the ETL uses the logId to count it once when it combines a day
    found in two files, and drops every column that starts with an underscore.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    records = []
    sessions = {}
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
            sessions.setdefault(date_str, []).append(
                SleepSession(entry.get('logId'), deep, light, rem, awake))
    if not records:
        return None
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    df = df.set_index('date')
    out = df.groupby('date').sum()
    out['_sessions'] = pd.Series(
        [sessions[d.strftime('%Y-%m-%d')] for d in out.index], index=out.index, dtype=object)
    return out


def parse_hrv_csv(file_path):
    """
    Parses 'Daily Heart Rate Variability Summary - ... .csv'.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Indexed by 'date' with 'rmssd' (Root Mean Square of Successive Differences).
                      Higher rMSSD generally indicates better recovery.
    """
    df = _read_csv(file_path)
    if 'rmssd' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df = df.set_index('date')
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
    df = _read_csv(file_path)
    df.columns = df.columns.str.strip()
    if 'DATE' not in df.columns or 'STRESS_SCORE' not in df.columns:
        return None
    df = df[df['STRESS_SCORE'] > 0]
    df['date'] = pd.to_datetime(df['DATE']).dt.normalize()
    df = df.set_index('date')
    df = df.rename(columns={'STRESS_SCORE': 'stress_score'})
    return df[['stress_score']]


def parse_acwr_csv(file_path):
    """
    Parses 'cardio_acute_chronic_workload_ratio.csv'.
    """
    df = _read_csv(file_path)
    if 'ratio' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df = df.rename(columns={'ratio': 'acwr_ratio'})
    df = df.set_index('date')
    return df[['acwr_ratio']]


def parse_vo2max_csv(file_path):
    """
    Parses 'demographic_vo2max.csv'.
    """
    df = _read_csv(file_path)
    if 'demographic vo2max' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df = df.rename(columns={'demographic vo2max': 'vo2max'})
    df = df.set_index('date')
    return df[['vo2max']]


def parse_readiness_csv(file_path):
    """
    Parses 'daily_readiness.csv' to extract the true Fitbit Readiness Score.
    """
    df = _read_csv(file_path)
    if 'score' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df = df.rename(columns={'score': 'readiness_score'})
    df = df.set_index('date')
    return df[['readiness_score']]


def parse_respiratory_rate_csv(file_path):
    """
    Parses 'daily_respiratory_rate.csv' for breath tracking.
    """
    df = _read_csv(file_path)
    if 'breaths per minute' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df = df.rename(columns={'breaths per minute': 'respiratory_rate'})
    df = df.set_index('date')
    return df[['respiratory_rate']]


def parse_skin_temperature_csv(file_path):
    """
    Parses 'daily_sleep_temperature_derivations.csv' and calculates the variation.
    """
    df = _read_csv(file_path)
    if 'nightly temperature celsius' not in df.columns or 'baseline temperature celsius' not in df.columns:
        return None
    df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
    df['temperature_variation'] = df['nightly temperature celsius'] - \
        df['baseline temperature celsius']
    df = df.set_index('date')
    return df[['temperature_variation']]


def parse_steps_json(file_path):
    """Parses 'steps-YYYY-MM-DD.json'."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    if df.empty:
        return None
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['date'] = pd.to_datetime(df['dateTime'], format='%m/%d/%y %H:%M:%S').dt.normalize()
    return df.groupby('date')['value'].sum().reset_index().rename(columns={'value': 'steps'}).set_index('date')


def parse_distance_json(file_path):
    """Parses 'distance-YYYY-MM-DD.json'."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    if df.empty:
        return None
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['date'] = pd.to_datetime(df['dateTime'], format='%m/%d/%y %H:%M:%S').dt.normalize()
    return df.groupby('date')['value'].sum().reset_index().rename(columns={'value': 'distance'}).set_index('date')


class ExerciseSession(NamedTuple):
    log_id: object
    duration: float
    calories: float
    count: int
    aef: float | None


def parse_exercise_json(file_path):
    """
    Parses 'exercise-*.json'.

    Returns a DataFrame indexed by 'date' with 'exercise_duration' (minutes),
    'exercise_calories', 'exercise_count' and 'exercise_aef' (mean of
    calories / average heart rate over the day's sessions that have a heart
    rate), plus a helper column '_sessions': for each day, the list of
    ExerciseSession (logId, minutes, calories, 1, efficiency or None) of its
    sessions in this file. Consecutive export files can both contain the same
    session; the ETL uses the logId to count it once when it combines a day
    found in two files, and drops every column that starts with an underscore.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    if not data:
        return None
    records = []
    for entry in data:
        dt = entry.get('startTime')
        if not dt:
            continue
        dur_ms = entry.get('duration', 0)
        dur_min = dur_ms / 60000.0
        cals = entry.get('calories', 0)

        recs = {
            'date': dt,
            'exercise_duration': dur_min,
            'exercise_calories': cals,
            'exercise_count': 1
        }
        aef = None
        avg_hr = entry.get('averageHeartRate')
        if avg_hr and avg_hr > 0:
            aef = cals / avg_hr
            recs['exercise_aef'] = aef
        recs['_session'] = ExerciseSession(entry.get('logId'), dur_min, cals, 1, aef)

        records.append(recs)

    if not records:
        return None

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'], format='%m/%d/%y %H:%M:%S').dt.normalize()

    sessions = {}
    for day, session in zip(df['date'], df['_session']):
        sessions.setdefault(day, []).append(session)
    df = df.drop(columns='_session')

    aggs = {
        'exercise_duration': 'sum',
        'exercise_calories': 'sum',
        'exercise_count': 'sum'
    }
    if 'exercise_aef' in df.columns:
        aggs['exercise_aef'] = 'mean'
    else:
        df['exercise_aef'] = 0.0
        aggs['exercise_aef'] = 'mean'

    stats = df.groupby('date').agg(aggs)
    stats['_sessions'] = pd.Series(
        [sessions[d] for d in stats.index], index=stats.index, dtype=object)
    return stats


def parser_for(source: Source):
    """The function path -> DataFrame | None that reads one file of `source`."""
    return source.reader.parse


def parse(source: Source, file_path):
    """Read one file of `source`: the same frame the ETL gets, helper columns included."""
    return parser_for(source)(file_path)


def drop_helpers(df):
    """The frame without the helper columns (names starting with "_")."""
    if df is None:
        return None
    return df.drop(columns=[c for c in df.columns if str(c).startswith("_")])
