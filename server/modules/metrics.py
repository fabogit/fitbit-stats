import config
import pandas as pd
from typing import Literal


def calculate_readiness(df):
    """ Calculates Z-Score based Readiness. """
    if 'overall_score' not in df.columns or 'resting_bpm' not in df.columns:
        print("Warning: Missing Sleep or RHR columns for Readiness.")
        return df

    sleep_z = (df['overall_score'] - df['overall_score'].mean()) / df['overall_score'].std()
    rhr_z = (df['resting_bpm'] - df['resting_bpm'].mean()) / df['resting_bpm'].std()

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
    s: Literal[-161, 5] = 5 if config.USER_GENDER == 'male' else -161

    # Calculate age dynamically based on DOB and the record's date (index)
    dob = pd.to_datetime(config.USER_DOB)

    # df.index is expected to be a DatetimeIndex
    age_series = (df.index - dob).days / 365.25

    df['bmr'] = (10 * df['weight_filled']) + (6.25 * config.USER_HEIGHT_CM) - (5 * age_series) + s

    # 3. Active Calories
    df['active_calories'] = (df['calories_total'] - df['bmr']).clip(lower=0)

    # 4. Intensity Index
    cols = ['lightly_active_minutes', 'moderately_active_minutes', 'very_active_minutes']
    for col in cols:
        if col not in df.columns: df[col] = 0.0

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
