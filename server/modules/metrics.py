import config
import pandas as pd
import numpy as np
from typing import Literal


def calculate_readiness(df):
    """ Calculates Z-Score based Readiness. """
    if 'overall_score' not in df.columns or 'resting_bpm' not in df.columns:
        print("Warning: Missing Sleep or RHR columns for Readiness.")
        return df

    sleep_z = (df['overall_score'] - df['overall_score'].mean()
               ) / df['overall_score'].std()
    rhr_z = (df['resting_bpm'] - df['resting_bpm'].mean()) / \
        df['resting_bpm'].std()

    df['readiness_raw'] = sleep_z - rhr_z
    return df


def calculate_metabolic_metrics(df):
    """ Calculates BMR (Mifflin-St Jeor), Active Calories, and Intensity. """

    # 1. Fill Weight
    if 'weight' in df.columns:
        # Interpolate missing values linearly to represent gradual changes
        df['weight_filled'] = df['weight'].interpolate(method='linear')
        # Fill remaining NaNs (edges or if no data points) with user configured fallback
        df['weight_filled'] = df['weight_filled'].fillna(config.USER_WEIGHT_KG)
    else:
        df['weight_filled'] = config.USER_WEIGHT_KG

    # 2. BMR
    if not config.USER_GENDER or not config.USER_DOB or not config.USER_HEIGHT_CM:
        df['bmr'] = 0.0
        df['active_calories'] = 0.0
    else:
        s: Literal[-161, 5] = 5 if config.USER_GENDER == 'male' else -161

        # Calculate age dynamically based on DOB and the record's date (index)
        try:
            dob = pd.to_datetime(config.USER_DOB)
            # df.index is expected to be a DatetimeIndex
            age_series = (df.index - dob).days / 365.25
            df['bmr'] = (10 * df['weight_filled']) + \
                (6.25 * config.USER_HEIGHT_CM) - (5 * age_series) + s
        except Exception as e:
            print(f"BMR Error: {e}")
            df['bmr'] = 0.0

        # 3. Active Calories
        df['active_calories'] = (
            df['calories_total'] - df['bmr']).clip(lower=0)

    # 4. Intensity Index
    cols = ['lightly_active_minutes',
            'moderately_active_minutes', 'very_active_minutes']
    for col in cols:
        if col not in df.columns:
            df[col] = 0.0

    df['total_active_minutes'] = (
        df['lightly_active_minutes'] +
        df['moderately_active_minutes'] +
        df['very_active_minutes']
    )

    df['intensity_index'] = df.apply(
        lambda row: row['active_calories'] / row['total_active_minutes']
        if row['total_active_minutes'] > 0 else 0, axis=1
    )

    return df


def calculate_advanced_metrics(df):
    """ Calculates Sleep Efficiency, Sleep Debt, Autonomic Balance, Activity/Sedentary Ratio, and Active TDEE Contribution. """

    # 1. Sleep Efficiency
    sleep_cols = ['sleep_deep', 'sleep_light', 'sleep_rem', 'sleep_awake']
    if all(c in df.columns for c in sleep_cols):
        total_sleep = df['sleep_deep'] + df['sleep_light'] + df['sleep_rem']
        total_bed = total_sleep + df['sleep_awake']
        df['sleep_efficiency'] = (total_sleep / total_bed * 100).round(1)
        df.loc[total_bed == 0, 'sleep_efficiency'] = None

    # 2. Sleep Debt (Rolling 7 days)
    if all(c in df.columns for c in sleep_cols[:3]):
        total_sleep = df['sleep_deep'] + df['sleep_light'] + df['sleep_rem']
        rolling_avg_sleep = total_sleep.rolling('7D', min_periods=1).mean()
        df['sleep_debt'] = (total_sleep - rolling_avg_sleep).round(1)

    # 3. Autonomic Balance (RMSSD / Resting BPM)
    if 'rmssd' in df.columns and 'resting_bpm' in df.columns:
        df['autonomic_balance'] = (df['rmssd'] / df['resting_bpm']).round(2)

    # 4. Activity vs Sedentary Ratio
    if 'total_active_minutes' in df.columns and 'sedentary_minutes' in df.columns:
        # Ignore divide by zero warnings with pd.Series division
        df['active_sedentary_ratio'] = np.where(
            df['sedentary_minutes'] > 0,
            (df['total_active_minutes'] / df['sedentary_minutes']).round(3),
            0.0
        )

    # 5. Active TDEE Contribution
    if 'active_calories' in df.columns and 'calories_total' in df.columns:
        df['active_tdee_ratio'] = np.where(
            df['calories_total'] > 0,
            ((df['active_calories'] / df['calories_total']) * 100).round(1),
            0.0
        )

    # 6. TRIMP (Training Impulse)
    if all(c in df.columns for c in ['zone_fat_burn', 'zone_cardio', 'zone_peak']):
        df['trimp'] = (df['zone_fat_burn'] * 1 + df['zone_cardio'] * 2.5 + df['zone_peak'] * 4).round(1)
    else:
        df['trimp'] = 0.0

    # 7. Training Monotony & Strain
    if 'trimp' in df.columns:
        trimp_mean = df['trimp'].rolling('7D', min_periods=3).mean()
        trimp_std = df['trimp'].rolling('7D', min_periods=3).std()
        df['training_monotony'] = np.where((trimp_std > 0) & (pd.notna(trimp_std)), (trimp_mean / trimp_std).round(2), 0)
        trimp_sum = df['trimp'].rolling('7D', min_periods=1).sum()
        df['training_strain'] = (trimp_sum * df['training_monotony']).round(1)

    # 8. Illness Predictor (Daily & Trend)
    if 'temperature_variation' in df.columns and 'respiratory_rate' in df.columns:
        # sick_flag_daily
        df['sick_flag_daily'] = np.where(
            (df['temperature_variation'] > 0.7) & 
            (df['respiratory_rate'] > df['respiratory_rate'].shift(1) + 1),
            True, False
        )
        
        # sick_flag_trend
        temp_baseline = df['temperature_variation'].rolling('7D', min_periods=3).mean()
        resp_baseline = df['respiratory_rate'].rolling('7D', min_periods=3).mean()
        df['sick_flag_trend'] = np.where(
            (df['temperature_variation'] > temp_baseline + 0.5) & 
            (df['respiratory_rate'] > resp_baseline + 1),
            True, False
        )

    # 9. HRV Coefficient of Variation (CV)
    if 'rmssd' in df.columns:
        rmssd_mean = df['rmssd'].rolling('7D', min_periods=3).mean()
        rmssd_std = df['rmssd'].rolling('7D', min_periods=3).std()
        df['hrv_cv'] = np.where((rmssd_mean > 0) & (pd.notna(rmssd_std)), (rmssd_std / rmssd_mean).round(3), None)

    # 10. ACWR Supercompensation & Injury Risk
    if 'acwr_ratio' in df.columns:
        df['supercompensation_flag'] = np.where((df['acwr_ratio'] >= 1.0) & (df['acwr_ratio'] <= 1.3), True, False)
        df['injury_risk_flag'] = np.where(df['acwr_ratio'] > 1.3, True, False)

    # 11. Aerobic Efficiency Factor (AEF) cleanup
    if 'exercise_aef' in df.columns:
        df['exercise_aef'] = df['exercise_aef'].fillna(0.0).round(2)

    return df
