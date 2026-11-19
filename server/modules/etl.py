import glob
import json
import os
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import pandas as pd
from modules import parsers


JSON_FILE = "dashboard_data.json"
WARNINGS_FILE = "etl_warnings.json"


def filter_by_date(df, start=None, end=None):
    """
    Keeps the rows between `start` and `end` (both inclusive, both optional).

    Ensures the DataFrame has a valid DatetimeIndex before applying the mask.

    Args:
        df (pd.DataFrame): The DataFrame to filter.
        start (datetime.date, optional): First day to keep.
        end (datetime.date, optional): Last day to keep.

    Returns:
        pd.DataFrame: A new DataFrame containing only rows within the date range.
    """
    if df is None or df.empty:
        return df
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except (ValueError, TypeError):
            return df

    # A DatetimeIndex cannot be compared with a datetime.date (TypeError in pandas 2+).
    mask = None
    if start:
        mask = (df.index >= pd.Timestamp(start))

    if end:
        if mask is not None:
            mask = mask & (df.index <= pd.Timestamp(end))
        else:
            mask = (df.index <= pd.Timestamp(end))

    if mask is not None:
        return df.loc[mask]
    return df


# Parsers heavy enough (hundreds of large files) to be worth a process pool.
# Decision (heart-rate speed-up): the min/max/avg BPM columns are kept, the
# parser is rewritten without pandas and its files are parsed in parallel.
# Skipping the source would drop these columns from dashboard_data.json.
PARALLEL_PARSERS = (parsers.heart_rate_intraday_detail,)
MAX_WORKERS = 8


def _safe_parse(parser_func, path):
    """Run a parser on one file; return (chunk, error) so errors don't abort a batch."""
    try:
        return parser_func(path), None
    except Exception as e:
        return None, e


def _parse_files(files, parser_func):
    """Parse files in order, in a process pool for heavy parsers when it is worthwhile."""
    work = partial(_safe_parse, parser_func)
    workers = min(MAX_WORKERS, os.cpu_count() or 1)
    if parser_func in PARALLEL_PARSERS and workers > 1 and len(files) > workers:
        try:
            with ProcessPoolExecutor(workers) as pool:
                return list(pool.map(work, files, chunksize=4))
        except Exception as e:
            print(f"   Process pool unavailable ({e}); parsing sequentially.")
    return [work(f) for f in files]


def describe_error(error, paths=()):
    """Short, user-facing text for an exception. Never contains any of `paths`.

    Used for the reason a file was skipped and for the message of a failed run.
    """
    if isinstance(error, OSError) and error.strerror:
        text = error.strerror
    else:
        text = str(error) or "no details"
    # Longest first: a folder is a prefix of the paths inside it.
    for p in sorted({str(p) for p in paths if p}, key=len, reverse=True):
        text = text.replace(p, "")
    return f"{type(error).__name__}: {' '.join(text.split())}"[:200]


def _skip_reason(error, path):
    """Short, user-facing reason a file was skipped. Never contains a folder path."""
    return describe_error(error, (path, os.path.dirname(path)))


# How the rows of the same day coming from different files of one source are
# combined (see _combine_duplicate_days). A rule is one of:
#   "sum"                 additive values (the parts of a split day add up)
#   "min" / "max"         daily minimum / maximum
#   "last"                snapshot values: the row of the last file in name order
#   ("session", i)        field i of the sessions listed in the "_sessions" helper
#                         column, each session counted once by its id (the same
#                         session can be in two overlapping files), then added up
#   ("session_mean", i)   same sessions, mean of field i over those where it is
#                         not None (the last row's value if there are none)
#   ("ratio", num, den, decimals)
#                         an average recomputed as sum(num) / sum(den) over the
#                         helper columns the parser exposes (names start with an
#                         underscore and are dropped from the result)
# A column without a rule is a snapshot ("last").
def _sum_of(*columns):
    return {c: "sum" for c in columns}


RULES_HEART_RATE = {
    "min_bpm": "min", "max_bpm": "max",
    "avg_bpm": ("ratio", "_bpm_sum", "_bpm_n", 1),
    "_bpm_sum": "sum", "_bpm_n": "sum",
}
RULES_EXERCISE = {
    "exercise_duration": ("session", 1), "exercise_calories": ("session", 2),
    "exercise_count": ("session", 3), "exercise_aef": ("session_mean", 4),
}
RULES_STEPS = _sum_of("steps")
RULES_DISTANCE = _sum_of("distance")
RULES_CALORIES = _sum_of("calories_total")
RULES_SLEEP_STAGES = {
    "sleep_deep": ("session", 1), "sleep_light": ("session", 2),
    "sleep_rem": ("session", 3), "sleep_awake": ("session", 4),
}
RULES_ZONES = _sum_of("zone_out_of_range", "zone_light", "zone_moderate", "zone_vigorous",
                      "zone_fat_burn", "zone_cardio", "zone_peak")
RULES_ACTIVITY_MINUTES = _sum_of("very_active_minutes", "moderately_active_minutes",
                                 "lightly_active_minutes", "sedentary_minutes")


SESSIONS_COLUMN = "_sessions"


def _unique_sessions(groups):
    """{day: sessions} from the per-file session lists of each day.

    A session with an id found in more than one file counts once; if the copies
    differ, the version of the last file (in name order) is used. Sessions
    without an id are all kept.
    """
    unique = {}
    for day, lists in groups:
        found = {}
        for n, session in enumerate(s for lst in lists for s in lst):
            found[session[0] if session[0] is not None else ("no-id", n)] = session
        unique[day] = list(found.values())
    return unique


def _combine_duplicate_days(df, rules):
    """
    Reduce a frame with several rows per day (one per file the day appears in)
    to one row per day, with the rule of each column (see RULES_*).

    Days that appear once are returned untouched. Rows must be in file order
    (files sorted by name), which is what the "last" rule relies on.
    """
    dup = df.index.duplicated(keep=False)
    if not dup.any():
        return df
    rest, multi = df[~dup], df[dup]
    grouped = multi.groupby(level=0)
    last = multi[~multi.index.duplicated(keep='last')]
    combined = {}
    sessions_by_day = None
    for col in multi.columns:
        rule = rules.get(col, "last")
        if rule == "sum":
            combined[col] = grouped[col].sum(min_count=1)
        elif rule == "min":
            combined[col] = grouped[col].min()
        elif rule == "max":
            combined[col] = grouped[col].max()
        elif rule == "last":
            combined[col] = last[col]
        elif rule[0] in ("session", "session_mean"):
            if sessions_by_day is None:
                sessions_by_day = _unique_sessions(grouped[SESSIONS_COLUMN])
            field = rule[1]
            if rule[0] == "session":
                combined[col] = pd.Series(
                    {day: sum(s[field] for s in found) for day, found in sessions_by_day.items()})
            else:
                values = {day: [s[field] for s in found if s[field] is not None]
                          for day, found in sessions_by_day.items()}
                combined[col] = pd.Series({
                    day: sum(v) / len(v) if v else last.at[day, col] for day, v in values.items()})
        else:
            _, num, den, decimals = rule
            num_sum, den_sum = grouped[num].sum(), grouped[den].sum()
            ratio = num_sum / den_sum.where(den_sum > 0)
            if decimals is not None:
                ratio = ratio.round(decimals)
            # nothing to average over in any file: fall back to the last row's value
            combined[col] = ratio.where(den_sum > 0, last[col])
    combined = pd.DataFrame(combined).rename_axis(df.index.name)
    return combined if rest.empty else pd.concat([rest, combined])


def load_collection(data_dir, folder_name, file_pattern, parser_func, warnings=None, combine=None):
    """
    Scans a specific folder for files matching a pattern, parses them,
    and aggregates them into a single DataFrame.

    Handles timezone normalization (stripping timezones) and the days that appear
    in more than one file, to ensure a clean time-series. Files are read in name
    order, so the result does not depend on the order the file system lists them.

    Args:
        data_dir (str | Path): Root folder of the export.
        folder_name (str): Subfolder name within data_dir.
        file_pattern (str): Glob pattern (e.g., "*.json").
        parser_func (function): Function to parse a single file into a DataFrame.
        warnings (list, optional): Receives one {"file", "reason"} dict (file name
            only, no folder) for every file that was skipped because it could not
            be parsed.
        combine (dict, optional): Rule per column for a day that appears in more
            than one file (see RULES_*); columns without a rule keep the value
            of the last file in name order.

    Returns:
        pd.DataFrame: Combined and sorted DataFrame for the specific metric, one
        row per day. Helper columns (names starting with "_") are removed.
    """
    search_path = os.path.join(data_dir, folder_name, file_pattern)
    files = sorted(glob.glob(search_path))
    if not files:
        return pd.DataFrame()

    print(f"   Loading {len(files)} files for {file_pattern}...")

    frames = []
    for f, (chunk, error) in zip(files, _parse_files(files, parser_func)):
        if error is not None:
            reason = _skip_reason(error, f)
            print(f"   Skipped {os.path.basename(f)}: {reason}")
            if warnings is not None:
                warnings.append({"file": os.path.basename(f), "reason": reason})
        elif chunk is not None and not chunk.empty:
            frames.append(chunk)

    if not frames:
        return pd.DataFrame()

    full_df = pd.concat(frames)

    # Normalize Timezone (Make naive) to allow merging different sources
    if isinstance(full_df.index, pd.DatetimeIndex) and full_df.index.tz is not None:
        full_df.index = full_df.index.tz_localize(None)

    # A day can appear in several files (the export is split by date range):
    # combine its parts per column instead of dropping all but one.
    full_df = _combine_duplicate_days(full_df, combine or {})
    full_df = full_df.drop(columns=[c for c in full_df.columns if str(c).startswith("_")])

    full_df = full_df.sort_index()
    return full_df


def merge_all_data(data_dir, start=None, end=None, progress_callback=None, warnings=None):
    """
    Main ETL Orchestrator.

    1. Defines the loading plan for all metrics (Heart Rate, Sleep, Activity, etc.).
    2. Loads and parses each collection independently.
    3. Merges all collections into a single Master DataFrame using Outer Join.
    4. Fills NaN values with 0 for activity-based columns.
    5. Performs final cleanup to remove empty or future rows based on calorie data.

    Args:
        data_dir (str | Path): Root folder of the export.
        start (datetime.date, optional): First day to keep (inclusive).
        end (datetime.date, optional): Last day to keep (inclusive).
        progress_callback: Optional callable(pct, msg) for progress reporting.
        warnings: Optional list; receives {"file", "reason"} for every file that
            was skipped because it could not be parsed (see load_collection).

    Returns:
        pd.DataFrame: The fully processed Master Dataset ready for analysis.
    """
    # start / end are applied only when explicitly set; the range of the data
    # itself comes from the merged index, never from file names.
    date_str = f"{start or 'first day'} to {end or 'last day'}"
    print(f"\n=== BUILDING MASTER DATASET ({date_str}) ===")

    # Define Loading Plan: (Folder, Pattern, Parser, Label[, duplicate-day rules])
    load_plan = [
        ("Global Export Data", "resting_heart_rate-*.json",
         parsers.parse_resting_heart_rate, "Resting heart rate"),
        ("Global Export Data", "heart_rate-*.json",
         parsers.heart_rate_intraday_detail, "Heart rate intraday", RULES_HEART_RATE),
        ("Global Export Data", "steps-*.json", parsers.parse_steps_json, "Steps", RULES_STEPS),
        ("Global Export Data", "distance-*.json", parsers.parse_distance_json, "Distance",
         RULES_DISTANCE),
        ("Global Export Data", "exercise-*.json", parsers.parse_exercise_json, "Exercise sessions",
         RULES_EXERCISE),
        ("Global Export Data", "weight-*.json", parsers.parse_weight, "Weight"),
        ("Global Export Data", "calories-*.json", parsers.parse_calories_intraday, "Calories",
         RULES_CALORIES),
        ("Sleep Score", "sleep_score.csv", parsers.parse_sleep_score_csv, "Sleep scores"),
        ("Global Export Data", "sleep-*.json", parsers.sleep_stages_detail, "Sleep stages",
         RULES_SLEEP_STAGES),
        ("Oxygen Saturation (SpO2)", "Daily SpO2 - *.csv", parsers.parse_spo2_csv, "SpO2"),
        ("Heart Rate Variability",
         "Daily Heart Rate Variability Summary - *.csv", parsers.parse_hrv_csv, "HRV"),
        ("Stress Score", "Stress Score.csv", parsers.parse_stress_csv, "Stress scores"),
        ("Global Export Data", "very_active_minutes-*.json",
         parsers.parse_simple_activity_json, "Active minutes", RULES_ACTIVITY_MINUTES),
        ("Global Export Data", "moderately_active_minutes-*.json",
         parsers.parse_simple_activity_json, "Moderate activity", RULES_ACTIVITY_MINUTES),
        ("Global Export Data", "lightly_active_minutes-*.json",
         parsers.parse_simple_activity_json, "Light activity", RULES_ACTIVITY_MINUTES),
        ("Global Export Data", "sedentary_minutes-*.json",
         parsers.parse_simple_activity_json, "Sedentary minutes", RULES_ACTIVITY_MINUTES),
        ("Physical Activity_GoogleData",
         "cardio_acute_chronic_workload_ratio.csv", parsers.parse_acwr_csv, "ACWR"),
        ("Physical Activity_GoogleData",
         "demographic_vo2max.csv", parsers.parse_vo2max_csv, "VO2 Max"),
        ("Physical Activity_GoogleData",
         "daily_readiness.csv", parsers.parse_readiness_csv, "Readiness"),
        ("Physical Activity_GoogleData", "daily_respiratory_rate.csv",
         parsers.parse_respiratory_rate_csv, "Respiratory rate"),
        ("Physical Activity_GoogleData", "daily_sleep_temperature_derivations.csv",
         parsers.parse_skin_temperature_csv, "Skin temperature"),
        ("Physical Activity_GoogleData", "time_in_heart_rate_zone_*.csv",
         parsers.parse_active_zones_csv, "HR zones", RULES_ZONES),
    ]

    total = len(load_plan)
    datasets = []
    for i, (folder, pattern, func, label, *rules) in enumerate(load_plan):
        # Progress from 10% to 65% spread across all collections
        pct = 10 + int((i / total) * 55)
        if progress_callback:
            progress_callback(pct, f"Loading {label}")
        datasets.append(load_collection(data_dir, folder, pattern, func, warnings, *rules))

    if progress_callback:
        progress_callback(65, "Merging datasets")

    # Filter empty datasets
    datasets = [d for d in datasets if not d.empty]
    if not datasets:
        return None

    # Merge Strategy: Outer Join starting from the first non-empty dataset
    master_df = datasets[0]
    for i in range(1, len(datasets)):
        master_df = master_df.join(datasets[i], how='outer')

    master_df = filter_by_date(master_df, start, end)

    # Fill NaNs for activity metrics (logical 0). The zone_* and sleep_* columns
    # are left out on purpose: a day without zone or sleep data must stay empty,
    # not 0 (a 0-minute night would drag the 7-day sleep mean down).
    cols_zero = [
        'very_active_minutes', 'moderately_active_minutes', 'lightly_active_minutes', 'sedentary_minutes',
        'calories_total',
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


def export_to_json(df, output_dir, filename=JSON_FILE):
    """
    Exports the processed Master DataFrame to a JSON file format suitable for the React Dashboard.

    The file is saved directly to the client's public folder so it can be served via HTTP.

    Args:
        df (pd.DataFrame): The Master Dataset to export.
        output_dir (str | Path): Folder that receives the file.
        filename (str): Name of the file (the pipeline writes a temporary name first).
    """
    output_path = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)

    # Reset index to include 'date' as a column in the JSON
    export_df = df.reset_index()
    export_df['date'] = export_df['date'].dt.strftime('%Y-%m-%d')

    export_df.to_json(output_path, orient='records')


def export_warnings(warnings, output_dir, filename=WARNINGS_FILE):
    """Writes the skipped-file warnings of the last run next to dashboard_data.json.

    An empty list is written too, so a clean run clears the warnings of the
    previous one.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, "w") as f:
        json.dump(warnings, f)
