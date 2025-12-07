import pandas as pd
import os
import sys

# ==========================================
# CONFIGURATION
# ==========================================
DATA_FILE = "fitbit_analysis.csv"


def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Please run analyze.py first.")
        sys.exit(1)

    df = pd.read_csv(DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df


def get_status_emoji(value, mean, std, metric_type='lower_is_better'):
    """
    Returns an emoji based on how much the value deviates from the mean (Z-Score).
    """
    if pd.isna(value) or pd.isna(mean) or pd.isna(std) or std == 0:
        return "⚪️ DATA N/A"

    z_score = (value - mean) / std

    if metric_type == 'lower_is_better':
        # E.g. RHR: Lower is better
        if z_score < -1.0:
            return "🟢 EXCELLENT"
        if z_score > 1.0:
            return "🔴 WARNING"
        return "⚪️ NORMAL"
    else:
        # E.g. Sleep Score: Higher is better
        if z_score > 1.0:
            return "🟢 EXCELLENT"
        if z_score < -1.0:
            return "🔴 WARNING"
        return "⚪️ NORMAL"


def generate_briefing():
    df = load_data()

    # Get the last available row (the latest synchronized day)
    latest_day = df.iloc[-1]
    latest_date = df.index[-1].strftime('%d %B %Y')

    print(f"\n==========================================")
    print(f" 📅 DAILY BRIEFING: {latest_date}")
    print(f"==========================================\n")

    # --- 1. HEALTH & RECOVERY ---
    print("❤️  HEALTH & RECOVERY")

    # RHR Analysis
    rhr_val = latest_day['resting_bpm']
    rhr_mean = df['resting_bpm'].mean()
    rhr_std = df['resting_bpm'].std()

    if pd.notna(rhr_val):
        # Calculate percentile (you are better than X% of your days)
        rhr_better_than = (df['resting_bpm'] > rhr_val).mean() * 100
        print(f"   • RHR: {rhr_val:.1f} bpm")
        print(
            f"     Status: {get_status_emoji(rhr_val, rhr_mean, rhr_std, 'lower_is_better')}")
        print(
            f"     Insight: Your heart is beating slower than {rhr_better_than:.0f}% of your recorded days.\n")
    else:
        print("   • RHR: No data for today.\n")

    # Sleep Analysis
    if pd.notna(latest_day.get('overall_score')):
        sleep_val = latest_day['overall_score']
        sleep_better_than = (df['overall_score'] < sleep_val).mean() * 100
        print(f"   • Sleep Score: {sleep_val:.0f}")
        print(
            f"     Status: {get_status_emoji(sleep_val, df['overall_score'].mean(), df['overall_score'].std(), 'higher_is_better')}")
        print(
            f"     Insight: You slept better than {sleep_better_than:.0f}% of your nights.\n")

    # --- 2. READINESS ---
    print("🔋 READINESS (Daily Form)")
    readiness = latest_day.get('readiness_raw')

    if pd.notna(readiness):
        if readiness > 1.0:
            advice = "🚀 PEAK CONDITION! Today is the right day for intense training or a personal record."
        elif readiness < -1.0:
            advice = "💤 BODY STRESSED. Consider active recovery, yoga, or a light walk. Avoid maximal effort."
        else:
            advice = "⚖️ NORMAL CONDITION. Train according to your usual schedule."
        print(f"   • Score: {readiness:.2f}")
        print(f"   • Advice: {advice}\n")
    else:
        print("   • Score: Not available (missing RHR or Sleep data)\n")

    # --- 3. METABOLISM & ACTIVITY ---
    print("🔥 METABOLISM & ACTIVITY")
    print(f"   • Total Calories: {latest_day['calories_total']:.0f} kcal")

    if pd.notna(latest_day.get('bmr')):
        print(f"     ├─ Base (BMR):  {latest_day['bmr']:.0f} kcal")
        print(f"     └─ Active Burn: {latest_day['active_calories']:.0f} kcal")

    if pd.notna(latest_day.get('intensity_index')):
        print(
            f"   • Intensity Index: {latest_day['intensity_index']:.1f} kcal/min")

    print(
        f"   • Very Active Minutes: {latest_day['very_active_minutes']:.0f} min")

    if pd.notna(latest_day.get('weight')):
        # FIX: Changed label to Kg
        print(f"   • Weight: {latest_day['weight']:.1f} Kg")

    print(f"\n==========================================")


if __name__ == "__main__":
    generate_briefing()
