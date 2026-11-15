#!/usr/bin/env python3
"""Generate a small synthetic Fitbit-style export for demos and tests.

All values are invented and the output is fully deterministic for a given
(--start, --days, --seed). The folder layout and file formats match what the
server ETL reads (see server/modules/etl.py and server/modules/parsers.py).

Usage:
    python scripts/generate_sample_export.py OUT_DIR [--days 60] [--start 2024-01-01] [--seed 42]

Only the Python standard library is used. Nothing is written inside the
repository unless you point OUT_DIR there.
"""
import argparse
import csv
import json
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

CHUNK_DAYS = 30  # one file per 30-day block, like the real monthly exports
LBS_PER_KG = 1 / 0.453592


def mdy(d):
    return d.strftime("%m/%d/%y")


def mdy_time(d, hh=0, mm=0, ss=0):
    return f"{mdy(d)} {hh:02d}:{mm:02d}:{ss:02d}"


def iso_z(d, hh=0, mm=0):
    return f"{d.isoformat()}T{hh:02d}:{mm:02d}:00Z"


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True), encoding="utf-8")


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def chunks(days):
    """Split the list of days into consecutive blocks of CHUNK_DAYS."""
    for i in range(0, len(days), CHUNK_DAYS):
        yield days[i:i + CHUNK_DAYS]


def build_day_models(rng, days):
    """Invent a per-day profile that all sources derive from."""
    models = []
    for i, d in enumerate(days):
        weekend = d.weekday() >= 5
        wave = math.sin(i / 9.0)
        active = max(0.35, rng.gauss(1.0 + (0.15 if weekend else 0), 0.25))
        models.append({
            "date": d,
            "active": active,
            "steps": int(max(2500, 8200 * active + 900 * wave)),
            "resting": round(61 - 2.5 * wave + rng.gauss(0, 1.2)),
            "sleep_total": int(max(300, rng.gauss(425, 40))),
            "workout": rng.random() < 0.35,
            "wave": wave,
        })
    return models


def split_total(rng, total, weights):
    """Split an integer total into len(weights) parts proportional to noisy weights."""
    noisy = [max(0.0, w * rng.uniform(0.7, 1.3)) for w in weights]
    s = sum(noisy) or 1.0
    parts = [int(total * n / s) for n in noisy]
    parts[0] += total - sum(parts)
    return parts


def slot_weights(slots_per_day):
    """Daytime-heavy activity profile over the day's slots."""
    out = []
    for s in range(slots_per_day):
        hour = s * 24 / slots_per_day
        out.append(max(0.0, math.sin((hour - 6) / 16 * math.pi)) if 6 <= hour <= 22 else 0.0)
    return out


def gen_daily_json_series(out, rng, models, prefix, value_fn, slots=96, fmt=str):
    """Intraday series (steps, distance, calories) written in 30-day files."""
    folder = out / "Global Export Data"
    for block in chunks(models):
        rows = []
        for m in block:
            d = m["date"]
            parts = value_fn(m, slots)
            for s, v in enumerate(parts):
                minutes = s * (1440 // slots)
                rows.append({"dateTime": mdy_time(d, minutes // 60, minutes % 60), "value": fmt(v)})
        write_json(folder / f"{prefix}-{block[0]["date"].isoformat()}.json", rows)


def gen_global_export(out, rng, models):
    folder = out / "Global Export Data"

    # Resting heart rate: nested 'value' -> 'value'
    for block in chunks(models):
        rows = [{"dateTime": mdy_time(m["date"]),
                 "value": {"date": mdy(m["date"]), "value": m["resting"], "error": 0.0}}
                for m in block]
        write_json(folder / f"resting_heart_rate-{block[0]['date'].isoformat()}.json", rows)

    # Intraday heart rate (every 15 minutes)
    for block in chunks(models):
        rows = []
        for m in block:
            for s in range(96):
                hour = s * 15 / 60
                base = m["resting"] + (0 if hour < 6 else 18 * max(0.0, math.sin((hour - 6) / 16 * math.pi)))
                bpm = int(base * rng.uniform(0.92, 1.12) + (35 * m["active"] if m["workout"] and 18 <= hour < 19 else 0))
                rows.append({"dateTime": mdy_time(m["date"], s * 15 // 60, s * 15 % 60),
                             "value": {"bpm": bpm, "confidence": 2}})
        write_json(folder / f"heart_rate-{block[0]['date'].isoformat()}.json", rows)

    # Steps, distance (centimeters, as Fitbit exports it) and calories
    gen_daily_json_series(out, rng, models, "steps", lambda m, n: split_total(rng, m["steps"], slot_weights(n)))
    gen_daily_json_series(out, rng, models, "distance",
                          lambda m, n: split_total(rng, int(m["steps"] * 74), slot_weights(n)))

    def calories(m, n):
        base = 1500 + 0.12 * m["steps"] + (280 if m["workout"] else 0)
        weights = [0.3 + w for w in slot_weights(n)]
        total = int(base * 10)  # tenths, then scaled below
        return [p / 10.0 for p in split_total(rng, total, weights)]
    gen_daily_json_series(out, rng, models, "calories", calories, fmt=lambda v: f"{v:.2f}")

    # Activity minutes (one entry per day)
    def minutes_files(name, fn):
        for block in chunks(models):
            rows = [{"dateTime": mdy_time(m["date"]), "value": str(int(fn(m)))} for m in block]
            write_json(folder / f"{name}-{block[0]['date'].isoformat()}.json", rows)
    minutes_files("very_active_minutes", lambda m: max(0, 22 * m["active"] + (30 if m["workout"] else 0) + rng.gauss(0, 5)))
    minutes_files("moderately_active_minutes", lambda m: max(0, 28 * m["active"] + rng.gauss(0, 6)))
    minutes_files("lightly_active_minutes", lambda m: max(60, 190 * m["active"] + rng.gauss(0, 20)))
    minutes_files("sedentary_minutes", lambda m: max(400, 780 - 80 * m["active"] + rng.gauss(0, 30)))

    # Exercise sessions
    for block in chunks(models):
        rows = []
        for m in block:
            if not m["workout"]:
                continue
            minutes = rng.choice([30, 40, 45, 55, 60])
            rows.append({
                "logId": rng.randint(10**10, 10**11 - 1),
                "activityName": rng.choice(["Run", "Walk", "Bike", "Workout"]),
                "startTime": mdy_time(m["date"], 18, 0),
                "duration": minutes * 60000,
                "calories": int(minutes * rng.uniform(7, 11)),
                "averageHeartRate": int(rng.uniform(120, 155)),
            })
        write_json(folder / f"exercise-{block[0]['date'].isoformat()}.json", rows)

    # Weight (pounds in the export; the parser converts to kg) - one weigh-in a week
    rows_all = []
    weight_kg = 72.0
    for i, m in enumerate(models):
        weight_kg += rng.gauss(0, 0.08)
        if i % 7 == 0:
            height_m = 1.75
            rows_all.append({
                "logId": rng.randint(10**12, 10**13 - 1),
                "weight": round(weight_kg * LBS_PER_KG, 1),
                "bmi": round(weight_kg / height_m ** 2, 2),
                "date": mdy(m["date"]),
                "time": "07:30:00",
                "source": "API",
            })
    for block in chunks(models):
        first, last = block[0]["date"], block[-1]["date"]
        rows = [r for r in rows_all if first <= datetime.strptime(r["date"], "%m/%d/%y").date() <= last]
        write_json(folder / f"weight-{first.isoformat()}.json", rows)

    # Sleep sessions with stage summaries
    for block in chunks(models):
        rows = []
        for m in block:
            total = m["sleep_total"]
            wake = int(total * rng.uniform(0.07, 0.12))
            deep = int(total * rng.uniform(0.12, 0.2))
            rem = int(total * rng.uniform(0.18, 0.24))
            light = total - wake - deep - rem
            rows.append({
                "logId": rng.randint(10**10, 10**11 - 1),
                "dateOfSleep": m["date"].isoformat(),
                "duration": (total + wake) * 60000,
                "minutesAsleep": total,
                "type": "stages",
                "levels": {"summary": {
                    "deep": {"count": 4, "minutes": deep},
                    "light": {"count": 20, "minutes": light},
                    "rem": {"count": 6, "minutes": rem},
                    "wake": {"count": 22, "minutes": wake},
                }},
            })
        write_json(folder / f"sleep-{block[0]['date'].isoformat()}.json", rows)


def gen_sleep_and_vitals(out, rng, models):
    write_csv(
        out / "Sleep Score" / "sleep_score.csv",
        ["sleep_log_entry_id", "timestamp", "overall_score", "composition_score", "revitalization_score",
         "duration_score", "deep_sleep_in_minutes", "resting_heart_rate", "restlessness"],
        [[10**10 + i, iso_z(m["date"], 7, 0), int(max(55, min(95, 80 + 6 * m["wave"] + rng.gauss(0, 4)))),
          int(rng.uniform(18, 25)), int(rng.uniform(65, 90)), int(rng.uniform(70, 100)),
          int(m["sleep_total"] * rng.uniform(0.12, 0.2)), m["resting"], round(rng.uniform(0.08, 0.18), 4)]
         for i, m in enumerate(models)])

    for block in chunks(models):
        first, last = block[0]["date"], block[-1]["date"]
        write_csv(
            out / "Oxygen Saturation (SpO2)" / f"Daily SpO2 - {first.isoformat()}-{last.isoformat()}.csv",
            ["timestamp", "average_value", "lower_bound", "upper_bound"],
            [[iso_z(m["date"]), round(rng.uniform(95.0, 97.5), 1), round(rng.uniform(92.0, 94.5), 1),
              round(rng.uniform(98.0, 99.5), 1)] for m in block])
        write_csv(
            out / "Heart Rate Variability" / f"Daily Heart Rate Variability Summary - {first.strftime('%Y-%m')}-({first.day:02d}).csv",
            ["timestamp", "rmssd", "nremhr", "entropy"],
            [[iso_z(m["date"]), round(42 + 6 * m["wave"] + rng.gauss(0, 4), 3),
              round(m["resting"] + 1.5, 3), round(rng.uniform(2.3, 2.9), 3)] for m in block])

    write_csv(
        out / "Stress Score" / "Stress Score.csv",
        ["DATE", "UPDATED_AT", "STRESS_SCORE", "SLEEP_POINTS", "MAX_SLEEP_POINTS", "RESPONSIVENESS_POINTS",
         "MAX_RESPONSIVENESS_POINTS", "EXERTION_POINTS", "MAX_EXERTION_POINTS", "STATUS", "CALCULATION_FAILED"],
        [[m["date"].isoformat(), iso_z(m["date"], 23, 0), int(max(35, min(90, 68 + 8 * m["wave"] + rng.gauss(0, 5)))),
          int(rng.uniform(20, 30)), 30, int(rng.uniform(18, 28)), 30, int(rng.uniform(10, 25)), 40, "READY", "false"]
         for m in models])


def gen_google_data(out, rng, models):
    folder = out / "Physical Activity_GoogleData"
    src = "Synthetic"
    write_csv(folder / "cardio_acute_chronic_workload_ratio.csv", ["timestamp", "ratio", "label", "data source"],
              [[iso_z(m["date"]), round(max(0.5, 1.0 + 0.2 * m["wave"] + rng.gauss(0, 0.08)), 3), "OPTIMAL", src]
               for m in models])
    vo2 = 42.0
    vo2_rows = []
    for m in models:
        vo2 += rng.gauss(0.02, 0.1)
        vo2_rows.append([iso_z(m["date"]), round(vo2, 2), src])
    write_csv(folder / "demographic_vo2max.csv", ["timestamp", "demographic vo2max", "data source"], vo2_rows)
    write_csv(folder / "daily_readiness.csv",
              ["timestamp", "score", "type", "sleep readiness", "heart rate variability readiness",
               "resting heart rate readiness", "data source"],
              [[iso_z(m["date"]), int(max(30, min(98, 72 + 10 * m["wave"] + rng.gauss(0, 6)))), "READY",
                "MEDIUM", "HIGH", "MEDIUM", src] for m in models])
    write_csv(folder / "daily_respiratory_rate.csv", ["timestamp", "breaths per minute", "data source"],
              [[iso_z(m["date"]), round(rng.uniform(13.5, 16.5), 1), src] for m in models])
    write_csv(folder / "daily_sleep_temperature_derivations.csv",
              ["timestamp", "nightly temperature celsius", "baseline temperature celsius",
               "relative nightly stddev 30d celsius", "data source"],
              [[iso_z(m["date"]), round(33.8 + rng.gauss(0, 0.3), 2), 33.8, 0.35, src] for m in models])

    # Time in heart-rate zones: one row per minute spent in a zone, one file per calendar month
    by_month = {}
    for m in models:
        by_month.setdefault((m["date"].year, m["date"].month), []).append(m)
    for (year, month), block in sorted(by_month.items()):
        rows = []
        for m in block:
            d = m["date"]
            plan = [("OUT_OF_RANGE", int(rng.uniform(40, 80))), ("FAT_BURN", int(rng.uniform(20, 60))),
                    ("CARDIO", int(rng.uniform(5, 25))), ("PEAK", int(rng.uniform(0, 8)) if m["workout"] else 0)]
            minute = 7 * 60
            for zone, count in plan:
                for _ in range(count):
                    rows.append([iso_z(d, minute // 60 % 24, minute % 60), zone, src])
                    minute += 1
        write_csv(folder / f"time_in_heart_rate_zone_{year}-{month:02d}-01.csv",
                  ["timestamp", "heart rate zone type", "data source"], rows)


def generate(out_dir, days=60, start=date(2024, 1, 1), seed=42):
    """Write the synthetic export under out_dir. Returns the output Path."""
    out = Path(out_dir)
    rng = random.Random(seed)
    day_list = [start + timedelta(days=i) for i in range(days)]
    models = build_day_models(rng, day_list)
    gen_global_export(out, rng, models)
    gen_sleep_and_vitals(out, rng, models)
    gen_google_data(out, rng, models)
    return out


def main():
    p = argparse.ArgumentParser(description="Generate a synthetic Fitbit-style export (all values invented).")
    p.add_argument("out_dir", help="Output folder (required; created if missing)")
    p.add_argument("--days", type=int, default=60, help="Number of days (default 60)")
    p.add_argument("--start", type=date.fromisoformat, default=date(2024, 1, 1), help="First day, YYYY-MM-DD")
    p.add_argument("--seed", type=int, default=42, help="Random seed (default 42)")
    a = p.parse_args()
    out = generate(a.out_dir, a.days, a.start, a.seed)
    print(f"Sample export written to {out}")


if __name__ == "__main__":
    main()
