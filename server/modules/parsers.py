# backend/modules/parsers.py
"""Parsers: one per source, driven by its declaration in load_plan.py.

Generic sources are read by read_json_daily / read_csv_daily from their declaration; the
irregular ones have a function of their own (Special). Every parser returns a
DataFrame indexed by 'date', or None when the file has no data. Columns whose
name starts with "_" are helpers for the ETL, which drops them after
combining the files of a source.
"""
import json
from functools import partial
from typing import NamedTuple

import pandas as pd

from modules.sources import Agg, Column, CsvDaily, Day, Difference, JsonDaily, Source, Special


def _read_csv(file_path):
    """Read a CSV file; a file that cannot be read raises, it is never skipped silently.

    The ETL catches the error per file and reports the file as a warning.
    """
    try:
        return pd.read_csv(file_path)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as e:
        raise ValueError(f"not a readable CSV file ({type(e).__name__})") from e


def _read_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)


# --- generic readers ---

def _present(df, columns: tuple[Column, ...], date_field: str):
    """The declared columns found in df, or None when the date or a required one is missing."""
    if date_field not in df.columns:
        return None
    present = []
    for c in columns:
        if all(i in df.columns for i in c.inputs):
            present.append(c)
        elif c.required:
            return None
    return present or None


def _values(df, c: Column, numeric: bool):
    if isinstance(c.field, Difference):
        v = df[c.field.minuend] - df[c.field.subtrahend]
    else:
        v = df[c.field or c.name]
    if numeric:
        v = pd.to_numeric(v, errors='coerce')
    if c.scale is not None:
        v = v * c.scale
    if c.decimals is not None:
        v = v.round(c.decimals)
    return v


def _frame(df, present, dates, numeric, agg: Agg | None):
    """The declared columns of df, indexed by day and reduced to one row per day with `agg`."""
    out = pd.DataFrame({c.name: _values(df, c, numeric) for c in present})
    out.index = pd.DatetimeIndex(dates, name='date')
    if agg is None:
        return out
    if agg is Agg.FIRST:
        # not groupby.first(): that would skip a NaN column by column
        return out[~out.index.duplicated(keep='first')]
    return out.groupby(level=0).agg(agg.value)


def read_json_daily(reader: JsonDaily, columns, file_path):
    """Read one file of a JsonDaily source: a list of records with a date field.

    Values are converted to numbers (what cannot be converted becomes NaN),
    scaled and rounded as declared, then reduced to one row per day with
    `reader.per_day`. A declared column that is not required may be missing
    from the file; a missing required column or date gives no data (None).
    """
    df = pd.DataFrame(_read_json(file_path))
    if df.empty:
        return None
    present = _present(df, columns, reader.date_field)
    if present is None:
        return None
    dates = pd.to_datetime(df[reader.date_field], format=reader.date_format).dt.normalize()
    return _frame(df, present, dates, True, reader.per_day)


def read_csv_daily(reader: CsvDaily, columns, file_path):
    """Read one file of a CsvDaily source: a CSV with a date column.

    Same rules as read_json_daily, except that values are kept as they are
    read (no number conversion) and rows can be filtered first (`keep_rows`).
    """
    df = _read_csv(file_path)
    df.columns = df.columns.str.strip()
    present = _present(df, columns, reader.date_field)
    if present is None:
        return None
    if reader.keep_rows is not None:
        df = df[reader.keep_rows(df)]
    raw = df[reader.date_field]
    if reader.day is Day.UTC:
        dates = pd.to_datetime(raw, format=reader.date_format, utc=True).dt.tz_convert(None)
    else:
        dates = pd.to_datetime(raw, format=reader.date_format)
    return _frame(df, present, dates.dt.normalize(), False, reader.per_day)


# --- special sources ---

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
    Parses 'time_in_heart_rate_zone_YYYY-MM-DD.csv' (minute-by-minute logs).
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
    """The function path -> DataFrame | None that reads one file of `source`.

    For a Special source it is the function itself (a module-level function,
    so a process pool can pickle it); for the others a partial of the reader.
    """
    reader = source.reader
    if isinstance(reader, Special):
        return reader.parse
    read = read_json_daily if isinstance(reader, JsonDaily) else read_csv_daily
    return partial(read, reader, source.columns)


def parse(source: Source, file_path):
    """Read one file of `source`: the same frame the ETL gets, helper columns included."""
    return parser_for(source)(file_path)


def drop_helpers(df):
    """The frame without the helper columns (names starting with "_")."""
    if df is None:
        return None
    return df.drop(columns=[c for c in df.columns if str(c).startswith("_")])
