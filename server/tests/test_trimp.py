import json

import pandas as pd

from modules import etl, metrics, parsers



def write_zone_file(path, minutes_by_day):
    """minutes_by_day: {'2024-03-04': {'LIGHT': 10, ...}} one row per minute."""
    lines = ["timestamp,heart rate zone type,data source"]
    for day, zones in minutes_by_day.items():
        minute = 0
        for zone, count in zones.items():
            for _ in range(count):
                lines.append(f"{day}T{minute // 60:02d}:{minute % 60:02d}:00Z,{zone},x")
                minute += 1
    path.write_text("\n".join(lines) + "\n")


def test_parser_maps_current_and_old_zone_names(tmp_path):
    f = tmp_path / "time_in_heart_rate_zone_2024-03-01.csv"
    write_zone_file(f, {"2024-03-04": {"OUT_OF_RANGE": 5, "LIGHT": 3, "MODERATE": 2,
                                       "VIGOROUS": 1, "FAT_BURN": 1, "CARDIO": 1, "PEAK": 1}})
    row = parsers.parse_active_zones_csv(str(f)).iloc[0]
    assert row["zone_out_of_range"] == 5
    assert row["zone_light"] == 3
    assert row["zone_moderate"] == 2
    assert row["zone_vigorous"] == 1
    assert (row["zone_fat_burn"], row["zone_cardio"], row["zone_peak"]) == (1, 1, 1)


def zone_frame(rows):
    idx = pd.to_datetime([d for d, _ in rows])
    return pd.DataFrame([z for _, z in rows], index=idx)


def test_trimp_from_current_zone_names():
    df = zone_frame([("2024-03-04", {"zone_light": 10, "zone_moderate": 4, "zone_vigorous": 2})])
    out = metrics.calculate_advanced_metrics(df)
    assert out["trimp"].iloc[0] == 10 * 1 + 4 * 2.5 + 2 * 4


def test_trimp_still_accepts_old_zone_names():
    df = zone_frame([("2024-03-04", {"zone_fat_burn": 10, "zone_cardio": 4, "zone_peak": 2})])
    out = metrics.calculate_advanced_metrics(df)
    assert out["trimp"].iloc[0] == 28


def test_monotony_and_strain_nonzero_for_varied_week():
    rows = [(f"2024-03-{d:02d}", {"zone_light": 10 * d, "zone_moderate": d, "zone_vigorous": d % 3})
            for d in range(4, 11)]
    out = metrics.calculate_advanced_metrics(zone_frame(rows))
    assert (out["trimp"] > 0).all()
    assert out["training_monotony"].iloc[-1] > 0
    assert out["training_strain"].iloc[-1] > 0


def test_days_without_zone_data_are_null_not_zero():
    rows = [("2024-03-04", {"zone_light": 10}), ("2024-03-05", {"zone_light": float("nan")}),
            ("2024-03-06", {"zone_light": 20}), ("2024-03-07", {"zone_light": 30})]
    out = metrics.calculate_advanced_metrics(zone_frame(rows))
    assert pd.isna(out.loc["2024-03-05", "trimp"])
    assert pd.isna(out.loc["2024-03-05", "training_monotony"])
    assert pd.isna(out.loc["2024-03-05", "training_strain"])
    assert out.loc["2024-03-06", "trimp"] == 20


def test_etl_end_to_end_leaves_uncovered_days_empty(tmp_path):
    cal = tmp_path / "Global Export Data"
    cal.mkdir()
    days = ["03/04/24", "03/05/24", "03/06/24"]
    (cal / "calories-2024-03-01.json").write_text(
        json.dumps([{"dateTime": f"{d} 12:00:00", "value": "10"} for d in days]))
    zdir = tmp_path / "Physical Activity_GoogleData"
    zdir.mkdir()
    write_zone_file(zdir / "time_in_heart_rate_zone_2024-03-01.csv",
                    {"2024-03-04": {"LIGHT": 10, "MODERATE": 4, "VIGOROUS": 2}})
    df = metrics.calculate_advanced_metrics(etl.merge_all_data(tmp_path))
    assert df["trimp"].iloc[0] == 28
    assert df["trimp"].iloc[1:].isna().all()
