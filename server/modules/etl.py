import glob
import multiprocessing
import os
import threading
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import pandas as pd
import applog
from modules import parsers
from modules.load_plan import LOAD_PLAN
from modules.sources import Agg, FromSessions, Ratio


JSON_FILE = "dashboard_data.json"

logger = applog.get_logger("etl")


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


MAX_WORKERS = 8


def exit_with_parent():
    """Initializer of the pool workers: a worker ends as soon as the process that started it is gone.

    Without it, workers outlive a server that was stopped or killed (an out-of-memory
    kill, the desktop application closing it) and keep working on their file, and
    holding its memory, until they notice that nobody wants the result.
    """
    parent = multiprocessing.parent_process()
    if parent is None:
        return

    def watch():
        parent.join()  # returns when the parent ends, however it ends
        os._exit(0)

    threading.Thread(target=watch, name="parent-watch", daemon=True).start()


def _safe_parse(parser_func, path):
    """Run a parser on one file; return (chunk, error) so errors don't abort a batch."""
    try:
        return parser_func(path), None
    except Exception as e:
        return None, e


def _parse_files(files, parser_func, parallel=False):
    """Parse files in order, in a process pool for heavy sources when it is worthwhile.

    Decision (heart-rate speed-up): the heart-rate source is declared `parallel`
    in the load plan; its parser avoids pandas and its files go to a pool.
    """
    work = partial(_safe_parse, parser_func)
    workers = min(MAX_WORKERS, os.cpu_count() or 1)
    if parallel and workers > 1 and len(files) > workers:
        try:
            with ProcessPoolExecutor(workers, initializer=exit_with_parent) as pool:
                return list(pool.map(work, files, chunksize=4))
        except Exception as e:
            logger.warning("Process pool unavailable (%s); parsing sequentially.", type(e).__name__)
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


def _combine_duplicate_days(df, rules, default=Agg.LAST):
    """
    Reduce a frame with several rows per day (one per file the day appears in)
    to one row per day, with the rule of each column (Column.combine in the
    load plan; `default` for columns without one).

    Days that appear once are returned untouched. Rows must be in file order
    (files sorted by name), which is what the LAST rule relies on.
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
        rule = rules.get(col, default)
        match rule:
            case Agg.SUM:
                combined[col] = grouped[col].sum(min_count=1)
            case Agg.MIN:
                combined[col] = grouped[col].min()
            case Agg.MAX:
                combined[col] = grouped[col].max()
            case Agg.LAST:
                combined[col] = last[col]
            case FromSessions(field=field, mean=mean):
                if sessions_by_day is None:
                    sessions_by_day = _unique_sessions(grouped[SESSIONS_COLUMN])
                if not mean:
                    combined[col] = pd.Series(
                        {day: sum(getattr(s, field) for s in found) for day, found in sessions_by_day.items()})
                else:
                    values = {day: [getattr(s, field) for s in found if getattr(s, field) is not None]
                              for day, found in sessions_by_day.items()}
                    combined[col] = pd.Series({
                        day: sum(v) / len(v) if v else last.at[day, col] for day, v in values.items()})
            case Ratio(numerator=num, denominator=den, decimals=decimals):
                num_sum, den_sum = grouped[num].sum(), grouped[den].sum()
                ratio = num_sum / den_sum.where(den_sum > 0)
                if decimals is not None:
                    ratio = ratio.round(decimals)
                # nothing to average over in any file: fall back to the last row's value
                combined[col] = ratio.where(den_sum > 0, last[col])
            case _:
                raise ValueError(f"no combine rule {rule!r} for column {col!r}")
    combined = pd.DataFrame(combined).rename_axis(df.index.name)
    return combined if rest.empty else pd.concat([rest, combined])


def load_collection(data_dir, folder_name, file_pattern, parser_func, warnings=None, combine=None,
                    default=Agg.LAST, parallel=False):
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
            than one file (Source.rules); columns without a rule follow `default`
            (by default the value of the last file in name order).
        default (Agg): rule of the columns not in `combine` (Source.other_columns).
        parallel (bool): parse the files in a process pool (Source.parallel).

    Returns:
        pd.DataFrame: Combined and sorted DataFrame for the specific metric, one
        row per day. Helper columns (names starting with "_") are removed.
    """
    search_path = os.path.join(data_dir, folder_name, file_pattern)
    files = sorted(glob.glob(search_path))
    if not files:
        return pd.DataFrame()

    logger.debug("Loading %d files for %s", len(files), file_pattern)

    frames = []
    skipped = 0
    for f, (chunk, error) in zip(files, _parse_files(files, parser_func, parallel)):
        if error is not None:
            reason = _skip_reason(error, f)
            skipped += 1
            logger.debug("Skipped %s: %s", os.path.basename(f), reason)
            if warnings is not None:
                warnings.append({"file": os.path.basename(f), "reason": reason})
        elif chunk is not None and not chunk.empty:
            frames.append(chunk)

    if skipped:
        logger.info("Skipped %d files of %s", skipped, file_pattern)

    if not frames:
        return pd.DataFrame()

    full_df = pd.concat(frames)

    # Normalize Timezone (Make naive) to allow merging different sources
    if isinstance(full_df.index, pd.DatetimeIndex) and full_df.index.tz is not None:
        full_df.index = full_df.index.tz_localize(None)

    # A day can appear in several files (the export is split by date range):
    # combine its parts per column instead of dropping all but one.
    full_df = _combine_duplicate_days(full_df, combine or {}, default)
    full_df = full_df.drop(columns=[c for c in full_df.columns if str(c).startswith("_")])

    full_df = full_df.sort_index()
    return full_df


def load_source(data_dir, source, warnings=None):
    """load_collection for one source of the load plan."""
    return load_collection(data_dir, source.folder, source.pattern, parsers.parser_for(source),
                           warnings, source.rules, source.other_columns, source.parallel)


def merge_all_data(data_dir, start=None, end=None, progress_callback=None, warnings=None):
    """
    Main ETL Orchestrator.

    1. Follows the loading plan (load_plan.LOAD_PLAN) for all metrics (Heart Rate, Sleep, Activity, etc.).
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
    logger.info("Building the master dataset")

    total = len(LOAD_PLAN)
    datasets = []
    for i, source in enumerate(LOAD_PLAN):
        # Progress from 10% to 65% spread across all sources
        pct = 10 + int((i / total) * 55)
        if progress_callback:
            progress_callback(pct, f"Loading {source.label}")
        datasets.append(load_source(data_dir, source, warnings))

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
            logger.info("Cleaned %d empty rows.", initial - len(master_df))

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
