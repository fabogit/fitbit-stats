"""The load plan: every source of the export the ETL reads, declared once.

The order is the loading order (and the order of the progress messages, and
of the columns of the merged table).
"""
from modules import parsers
from modules.sources import Agg, Column, FromSessions, Ratio, Source, Special

GLOBAL = "Global Export Data"
GOOGLE = "Physical Activity_GoogleData"


def _summed(*names):
    return tuple(Column(n, combine=Agg.SUM) for n in names)


def _activity_minutes(name, label):
    return Source(name, label, GLOBAL, f"{name}-*.json",
                  Special(parsers.parse_simple_activity_json), _summed(name))


def _google_csv(key, label, pattern, column, parse):
    return Source(key, label, GOOGLE, pattern, Special(parse), (Column(column),))


LOAD_PLAN: tuple[Source, ...] = (
    Source("resting_heart_rate", "Resting heart rate", GLOBAL, "resting_heart_rate-*.json",
           Special(parsers.parse_resting_heart_rate), (Column("resting_bpm"),)),
    Source("heart_rate", "Heart rate intraday", GLOBAL, "heart_rate-*.json",
           Special(parsers.parse_heart_rate_intraday), (
               Column("min_bpm", Agg.MIN),
               Column("max_bpm", Agg.MAX),
               Column("avg_bpm", Ratio("_bpm_sum", "_bpm_n", decimals=1)),
               Column("_bpm_sum", Agg.SUM),
               Column("_bpm_n", Agg.SUM),
           ), parallel=True),
    Source("steps", "Steps", GLOBAL, "steps-*.json",
           Special(parsers.parse_steps_json), _summed("steps")),
    Source("distance", "Distance", GLOBAL, "distance-*.json",
           Special(parsers.parse_distance_json), _summed("distance")),
    Source("exercise", "Exercise sessions", GLOBAL, "exercise-*.json",
           Special(parsers.parse_exercise_json), (
               Column("exercise_duration", FromSessions("duration")),
               Column("exercise_calories", FromSessions("calories")),
               Column("exercise_count", FromSessions("count")),
               Column("exercise_aef", FromSessions("aef", mean=True)),
               Column("_sessions"),
           )),
    Source("weight", "Weight", GLOBAL, "weight-*.json",
           Special(parsers.parse_weight), (Column("weight"), Column("bmi"))),
    Source("calories", "Calories", GLOBAL, "calories-*.json",
           Special(parsers.parse_calories_intraday), _summed("calories_total")),
    Source("sleep_score", "Sleep scores", "Sleep Score", "sleep_score.csv",
           Special(parsers.parse_sleep_score_csv), (
               Column("overall_score"),
               Column("deep_sleep_in_minutes"),
               Column("restlessness"),
           )),
    Source("sleep_stages", "Sleep stages", GLOBAL, "sleep-*.json",
           Special(parsers.parse_sleep_stages), (
               Column("sleep_deep", FromSessions("deep")),
               Column("sleep_light", FromSessions("light")),
               Column("sleep_rem", FromSessions("rem")),
               Column("sleep_awake", FromSessions("awake")),
               Column("_sessions"),
           )),
    Source("spo2", "SpO2", "Oxygen Saturation (SpO2)", "Daily SpO2 - *.csv",
           Special(parsers.parse_spo2_csv), (
               Column("spo2_avg"), Column("spo2_min"), Column("spo2_max"))),
    Source("hrv", "HRV", "Heart Rate Variability", "Daily Heart Rate Variability Summary - *.csv",
           Special(parsers.parse_hrv_csv), (Column("rmssd"),)),
    Source("stress", "Stress scores", "Stress Score", "Stress Score.csv",
           Special(parsers.parse_stress_csv), (Column("stress_score"),)),
    _activity_minutes("very_active_minutes", "Active minutes"),
    _activity_minutes("moderately_active_minutes", "Moderate activity"),
    _activity_minutes("lightly_active_minutes", "Light activity"),
    _activity_minutes("sedentary_minutes", "Sedentary minutes"),
    _google_csv("acwr", "ACWR", "cardio_acute_chronic_workload_ratio.csv", "acwr_ratio",
                parsers.parse_acwr_csv),
    _google_csv("vo2max", "VO2 Max", "demographic_vo2max.csv", "vo2max",
                parsers.parse_vo2max_csv),
    _google_csv("readiness", "Readiness", "daily_readiness.csv", "readiness_score",
                parsers.parse_readiness_csv),
    _google_csv("respiratory_rate", "Respiratory rate", "daily_respiratory_rate.csv",
                "respiratory_rate", parsers.parse_respiratory_rate_csv),
    _google_csv("skin_temperature", "Skin temperature",
                "daily_sleep_temperature_derivations.csv", "temperature_variation",
                parsers.parse_skin_temperature_csv),
    Source("active_zones", "HR zones", GOOGLE, "time_in_heart_rate_zone_*.csv",
           Special(parsers.parse_active_zones_csv),
           _summed(*parsers.ZONE_NAMES.values())),
)

SOURCES = {s.key: s for s in LOAD_PLAN}
