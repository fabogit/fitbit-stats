"""Metrics on short hand-built series; expected values are worked out in comments."""
import numpy as np
import pandas as pd
import pytest

from modules import metrics


def frame(columns, start="2024-03-28"):
    n = len(next(iter(columns.values())))
    return pd.DataFrame(columns, index=pd.date_range(start, periods=n))


# --- readiness ---

def test_readiness_zscores():
    # sleep 70, 80, 90: mean 80, std 10 -> z -1, 0, 1
    # rhr 60, 58, 56: mean 58, std 2 -> z 1, 0, -1 ; raw = sleep_z - rhr_z
    df = pd.DataFrame({"overall_score": [70.0, 80.0, 90.0], "resting_bpm": [60.0, 58.0, 56.0]})
    out = metrics.calculate_readiness(df)
    assert out["readiness_raw"].tolist() == [-2.0, 0.0, 2.0]


def test_readiness_missing_columns_adds_nothing():
    out = metrics.calculate_readiness(pd.DataFrame({"overall_score": [70.0, 80.0]}))
    assert "readiness_raw" not in out.columns


# --- weight ---

def test_weight_is_interpolated_between_weigh_ins(set_profile):
    set_profile()
    df = frame({"calories_total": [2000.0] * 5, "weight": [80.0, np.nan, np.nan, np.nan, 78.0]})
    out = metrics.calculate_metabolic_metrics(df)
    assert out["weight_filled"].tolist() == [80.0, 79.5, 79.0, 78.5, 78.0]


def test_configured_weight_is_used_without_weigh_ins(set_profile):
    set_profile(weight=75.0)
    out = metrics.calculate_metabolic_metrics(frame({"calories_total": [2000.0] * 3}))
    assert out["weight_filled"].tolist() == [75.0] * 3


def test_configured_weight_fills_days_before_the_first_weigh_in(set_profile):
    set_profile(weight=75.0)
    df = frame({"calories_total": [2000.0] * 4, "weight": [np.nan, np.nan, 80.0, 80.0]})
    out = metrics.calculate_metabolic_metrics(df)
    assert out["weight_filled"].tolist()[:2] == [75.0, 75.0]


# --- BMR, active calories, intensity ---

def metabolic_row(set_profile, calories, minutes=(60, 20, 10), **profile):
    set_profile(**profile)
    df = frame({"calories_total": [calories], "weight": [80.0],
                "lightly_active_minutes": [float(minutes[0])],
                "moderately_active_minutes": [float(minutes[1])],
                "very_active_minutes": [float(minutes[2])]})
    return metrics.calculate_metabolic_metrics(df).iloc[0]


def test_bmr_male_known_profile(set_profile):
    # born 1984-03-28, row 2024-03-28: 14610 days / 365.25 = 40.0 years
    # 10 x 80 + 6.25 x 180 - 5 x 40 + 5 = 800 + 1125 - 200 + 5
    assert metabolic_row(set_profile, 2500.0)["bmr"] == pytest.approx(1730.0)


def test_bmr_female_known_profile(set_profile):
    # same profile with the female constant: 800 + 1125 - 200 - 161
    assert metabolic_row(set_profile, 2500.0, gender="female")["bmr"] == pytest.approx(1564.0)


def test_bmr_age_follows_the_row_date(set_profile):
    set_profile()
    df = frame({"calories_total": [2500.0, 2500.0], "weight": [80.0, 80.0]})
    out = metrics.calculate_metabolic_metrics(df)
    # one day later: age 14611 / 365.25 = 40.00274 -> 1730 - 5 x 0.00274 = 1729.986
    assert out["bmr"].iloc[1] == pytest.approx(1729.986, abs=0.01)


def test_active_calories_and_intensity(set_profile):
    row = metabolic_row(set_profile, 2500.0)
    assert row["active_calories"] == pytest.approx(770.0)             # 2500 - 1730
    assert row["total_active_minutes"] == 90
    assert row["intensity_index"] == pytest.approx(770.0 / 90)


def test_active_calories_never_negative(set_profile):
    row = metabolic_row(set_profile, 1500.0)                          # below the BMR
    assert row["active_calories"] == 0.0
    assert row["intensity_index"] == 0


def test_intensity_is_zero_without_active_minutes(set_profile):
    row = metabolic_row(set_profile, 2500.0, minutes=(0, 0, 0))
    assert row["intensity_index"] == 0


@pytest.mark.parametrize("missing", ["gender", "dob", "height"])
def test_incomplete_profile_gives_no_positive_bmr(set_profile, missing):
    # Not pinned on purpose: whether an incomplete profile gives 0.0 or NaN is
    # undecided. Only: no exception, and no positive BMR or active calories.
    empty = {"gender": "", "dob": "", "height": 0}
    set_profile(**{missing: empty[missing]})
    df = frame({"calories_total": [2500.0], "weight": [80.0]})
    out = metrics.calculate_metabolic_metrics(df)
    assert not (out["bmr"] > 0).any()
    assert not (out["active_calories"] > 0).any()


# --- sleep ---

def sleep_frame(totals, deep=0, rem=0, awake=0):
    return frame({"sleep_deep": [deep] * len(totals), "sleep_light": totals,
                  "sleep_rem": [rem] * len(totals), "sleep_awake": [awake] * len(totals)})


def test_sleep_efficiency():
    df = frame({"sleep_deep": [60], "sleep_light": [240], "sleep_rem": [90], "sleep_awake": [30]})
    # 390 asleep / 420 in bed = 92.857 %
    assert metrics.calculate_advanced_metrics(df)["sleep_efficiency"].iloc[0] == 92.9


def test_sleep_efficiency_without_time_in_bed_is_null():
    out = metrics.calculate_advanced_metrics(sleep_frame([0]))
    assert pd.isna(out["sleep_efficiency"].iloc[0])


def test_sleep_debt_values():
    # nights 400, 440, 360; mean so far (including the day) 400, 420, 400
    out = metrics.calculate_advanced_metrics(sleep_frame([400, 440, 360]))
    assert out["sleep_debt"].tolist() == [0.0, 20.0, -40.0]


def test_sleep_debt_window_is_seven_days_including_today():
    # day 8 sees days 2..8: (700 + 6 x 400) / 7 = 442.857 -> 400 - 442.857
    # (a 6-day window would give 0.0, an 8-day one -75.0)
    out = metrics.calculate_advanced_metrics(sleep_frame([700, 700] + [400] * 6))
    assert out["sleep_debt"].iloc[-1] == -42.9


# --- simple ratios ---

def test_autonomic_balance():
    df = frame({"rmssd": [45.0, 42.0], "resting_bpm": [60.0, 61.0]})
    # 45 / 60 = 0.75 ; 42 / 61 = 0.6885
    assert metrics.calculate_advanced_metrics(df)["autonomic_balance"].tolist() == [0.75, 0.69]


def test_active_sedentary_ratio():
    df = frame({"total_active_minutes": [90.0, 90.0], "sedentary_minutes": [600.0, 0.0]})
    assert metrics.calculate_advanced_metrics(df)["active_sedentary_ratio"].tolist() == [0.15, 0.0]


def test_active_tdee_ratio():
    df = frame({"active_calories": [770.0, 0.0], "calories_total": [2500.0, 0.0]})
    # 770 / 2500 = 30.8 % ; no calories -> 0
    assert metrics.calculate_advanced_metrics(df)["active_tdee_ratio"].tolist() == [30.8, 0.0]


# --- training load over a rolling week ---

def test_monotony_and_strain_known_values():
    out = metrics.calculate_advanced_metrics(frame({"zone_light": [10, 20, 30, 10]}))
    # Days 1-2 have fewer than 3 samples: not pinned (see the comment below).
    # Day 3: values 10, 20, 30 -> mean 20, std 10 -> monotony 2.0, strain 60 x 2.0
    assert out["training_monotony"].iloc[2] == 2.0
    assert out["training_strain"].iloc[2] == 120.0
    # Day 4: 10, 20, 30, 10 -> mean 17.5, std sqrt(275 / 3) = 9.574 -> 1.83
    assert out["training_monotony"].iloc[3] == 1.83
    assert out["training_strain"].iloc[3] == 128.1       # 70 x 1.83


def test_training_window_is_seven_days():
    # Day 1 and day 2 are far from the rest. On day 9 the window holds days
    # 3..9, so the result must equal the one computed on those days alone.
    values = [200, 100, 10, 20, 30, 10, 20, 30, 10]
    full = metrics.calculate_advanced_metrics(frame({"zone_light": values}))
    tail = metrics.calculate_advanced_metrics(frame({"zone_light": values[2:]}, start="2024-03-30"))
    assert full["training_monotony"].iloc[-1] == tail["training_monotony"].iloc[-1]
    assert full["training_strain"].iloc[-1] == tail["training_strain"].iloc[-1]
    assert full["training_monotony"].iloc[-1] > 0


def test_hrv_cv_known_values():
    out = metrics.calculate_advanced_metrics(frame({"rmssd": [40.0, 50.0, 60.0, 45.0]}))
    # Day 3: mean 50, std 10 -> 0.2. Day 4: mean 48.75, std 8.539 -> 0.175
    assert out["hrv_cv"].iloc[2] == 0.2
    assert out["hrv_cv"].iloc[3] == 0.175
    assert out["hrv_cv"].iloc[:2].isna().all()   # fewer than 3 samples


# --- illness flags ---

def test_sick_flags_on_a_clear_case():
    df = frame({"temperature_variation": [0.1, 0.2, 0.1, 0.9],
                "respiratory_rate": [14.0, 14.0, 14.0, 16.0]})
    out = metrics.calculate_advanced_metrics(df)
    # Day 4: 0.9 > 0.7 and 16 > 14 + 1 ; trend: 0.9 > 0.325 + 0.5 and 16 > 14.5 + 1
    assert out["sick_flag_daily"].tolist() == [False, False, False, True]
    assert out["sick_flag_trend"].tolist() == [False, False, False, True]


@pytest.mark.parametrize("temperature, respiration", [
    (0.7, 16.0),    # temperature exactly at the threshold
    (0.9, 15.0),    # respiration exactly 1 above the day before
])
def test_sick_flag_daily_thresholds_are_strict(temperature, respiration):
    df = frame({"temperature_variation": [0.0, temperature], "respiratory_rate": [14.0, respiration]})
    assert not metrics.calculate_advanced_metrics(df)["sick_flag_daily"].iloc[1]


# --- ACWR flags ---

@pytest.mark.parametrize("ratio, supercompensation, injury", [
    (0.99, False, False),
    (1.0, True, False),
    (1.3, True, False),
    (1.31, False, True),
])
def test_acwr_flag_thresholds(ratio, supercompensation, injury):
    out = metrics.calculate_advanced_metrics(frame({"acwr_ratio": [ratio]}))
    assert bool(out["supercompensation_flag"].iloc[0]) is supercompensation
    assert bool(out["injury_risk_flag"].iloc[0]) is injury


# --- exercise efficiency ---

def test_exercise_aef_is_rounded_to_two_decimals():
    # Not pinned on purpose: what a missing value becomes (0.0 or NaN).
    out = metrics.calculate_advanced_metrics(frame({"exercise_aef": [0.7519, 1.0]}))
    assert out["exercise_aef"].iloc[0] == 0.75


# --- missing columns ---

def test_blocks_are_skipped_when_their_columns_are_missing():
    out = metrics.calculate_advanced_metrics(frame({"steps": [1000.0, 2000.0]}))
    for col in ("sleep_efficiency", "sleep_debt", "autonomic_balance", "active_sedentary_ratio",
                "active_tdee_ratio", "sick_flag_daily", "hrv_cv", "supercompensation_flag"):
        assert col not in out.columns, col
    assert out["trimp"].isna().all()
