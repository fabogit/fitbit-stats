"""The load plan: every source of the export the ETL reads, declared once.

The order is the loading order (and the order of the progress messages, and
of the columns of the merged table).
"""
from modules import parsers
from modules.sources import (Agg, Column, CsvDaily, Day, Difference, FromSessions, JsonDaily, Ratio,
                             Source, Special)

GLOBAL = "Global Export Data"
GOOGLE = "Physical Activity_GoogleData"
LBS_TO_KG = 0.453592


def _summed(*names):
    return tuple(Column(n, combine=Agg.SUM) for n in names)


def _daily_sum(name):
    """The "value" of every record of the file, added up per day."""
    return (Column(name, "value", combine=Agg.SUM),)


def _activity_minutes(name, label):
    return Source(name, label, GLOBAL, f"{name}-*.json", JsonDaily(), _daily_sum(name))


def _stress_rows_with_a_score(df):
    """Rows with a score above 0 and, when the file has a status, one with data."""
    keep = df['STRESS_SCORE'] > 0
    if 'STATUS' in df.columns:
        keep &= df['STATUS'] != 'NO_DATA'
    return keep


def _google_csv(key, label, pattern, column, field):
    return Source(key, label, GOOGLE, pattern, CsvDaily(), (Column(column, field),))


LOAD_PLAN: tuple[Source, ...] = (
    Source("resting_heart_rate", "Resting heart rate", GLOBAL, "resting_heart_rate-*.json",
           Special(parsers.parse_resting_heart_rate), (Column("resting_bpm"),)),
    Source("heart_rate", "Heart rate intraday", GLOBAL, "heart_rate-*.json",
           Special(parsers.parse_heart_rate_intraday), (
               Column("min_bpm", combine=Agg.MIN),
               Column("max_bpm", combine=Agg.MAX),
               Column("avg_bpm", combine=Ratio("_bpm_sum", "_bpm_n", decimals=1)),
               Column("_bpm_sum", combine=Agg.SUM),
               Column("_bpm_n", combine=Agg.SUM),
           ), parallel=True),
    Source("steps", "Steps", GLOBAL, "steps-*.json",
           JsonDaily(per_day=Agg.SUM), _daily_sum("steps")),
    Source("distance", "Distance", GLOBAL, "distance-*.json",
           JsonDaily(per_day=Agg.SUM), _daily_sum("distance")),
    Source("exercise", "Exercise sessions", GLOBAL, "exercise-*.json",
           Special(parsers.parse_exercise_json), (
               Column("exercise_duration", combine=FromSessions("duration")),
               Column("exercise_calories", combine=FromSessions("calories")),
               Column("exercise_count", combine=FromSessions("count")),
               Column("exercise_aef", combine=FromSessions("aef", mean=True)),
               Column("_sessions"),
           )),
    Source("weight", "Weight", GLOBAL, "weight-*.json",
           JsonDaily(date_field="date", date_format="%m/%d/%y", per_day=Agg.FIRST), (
               Column("weight", scale=LBS_TO_KG, decimals=1),
               Column("bmi", required=False),
           )),
    Source("calories", "Calories", GLOBAL, "calories-*.json",
           JsonDaily(per_day=Agg.SUM), _daily_sum("calories_total")),
    Source("sleep_score", "Sleep scores", "Sleep Score", "sleep_score.csv",
           CsvDaily(day=Day.UTC, date_format="ISO8601", per_day=Agg.MAX), (
               Column("overall_score", required=False),
               Column("deep_sleep_in_minutes", required=False),
               Column("restlessness", required=False),
           )),
    Source("sleep_stages", "Sleep stages", GLOBAL, "sleep-*.json",
           Special(parsers.parse_sleep_stages), (
               Column("sleep_deep", combine=FromSessions("deep")),
               Column("sleep_light", combine=FromSessions("light")),
               Column("sleep_rem", combine=FromSessions("rem")),
               Column("sleep_awake", combine=FromSessions("awake")),
               Column("_sessions"),
           )),
    Source("spo2", "SpO2", "Oxygen Saturation (SpO2)", "Daily SpO2 - *.csv",
           CsvDaily(day=Day.UTC, per_day=Agg.MEAN), (
               Column("spo2_avg", "average_value"),
               Column("spo2_min", "lower_bound"),
               Column("spo2_max", "upper_bound"),
           )),
    Source("hrv", "HRV", "Heart Rate Variability", "Daily Heart Rate Variability Summary - *.csv",
           CsvDaily(), (Column("rmssd"),)),
    Source("stress", "Stress scores", "Stress Score", "Stress Score.csv",
           CsvDaily(date_field="DATE", keep_rows=_stress_rows_with_a_score),
           (Column("stress_score", "STRESS_SCORE"),)),
    _activity_minutes("very_active_minutes", "Active minutes"),
    _activity_minutes("moderately_active_minutes", "Moderate activity"),
    _activity_minutes("lightly_active_minutes", "Light activity"),
    _activity_minutes("sedentary_minutes", "Sedentary minutes"),
    _google_csv("acwr", "ACWR", "cardio_acute_chronic_workload_ratio.csv", "acwr_ratio", "ratio"),
    _google_csv("vo2max", "VO2 Max", "demographic_vo2max.csv", "vo2max", "demographic vo2max"),
    _google_csv("readiness", "Readiness", "daily_readiness.csv", "readiness_score", "score"),
    _google_csv("respiratory_rate", "Respiratory rate", "daily_respiratory_rate.csv",
                "respiratory_rate", "breaths per minute"),
    Source("skin_temperature", "Skin temperature", GOOGLE, "daily_sleep_temperature_derivations.csv",
           CsvDaily(), (Column("temperature_variation", Difference(
               "nightly temperature celsius", "baseline temperature celsius")),)),
    Source("active_zones", "HR zones", GOOGLE, "time_in_heart_rate_zone_*.csv",
           Special(parsers.parse_active_zones_csv),
           _summed(*parsers.ZONE_NAMES.values()), other_columns=Agg.SUM),
)

SOURCES = {s.key: s for s in LOAD_PLAN}
