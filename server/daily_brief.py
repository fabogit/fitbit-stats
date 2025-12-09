import pandas as pd
import os
import sys

# ==========================================
# CONFIGURATION
# ==========================================
DATA_FILE = "fitbit_analysis.csv"

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Please run main.py first.")
        sys.exit(1)

    df = pd.read_csv(DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

def get_status_emoji(value, mean, std, metric_type='lower_is_better'):
    """
    Returns an emoji based on Z-Score.
    """
    if pd.isna(value) or pd.isna(mean) or pd.isna(std) or std == 0:
        return "⚪️ N/A"

    z_score = (value - mean) / std

    if metric_type == 'lower_is_better':
        if z_score < -1.0: return "🟢 EXCELLENT"
        if z_score > 1.0:  return "🔴 WARNING"
        return "⚪️ NORMAL"
    else: # higher_is_better (Sleep, HRV)
        if z_score > 1.0:  return "🟢 EXCELLENT"
        if z_score < -1.0: return "🔴 WARNING"
        return "⚪️ NORMAL"

def generate_briefing():
    df = load_data()

    # Get the last available row
    latest_day = df.iloc[-1]
    latest_date = df.index[-1].strftime('%d %B %Y')

    print(f"\n==========================================")
    print(f" 📅 DAILY BRIEFING: {latest_date}")
    print(f"==========================================\n")

    # --- 1. HEALTH & RECOVERY ---
    print("❤️  PHYSIOLOGY & RECOVERY")

    # RHR
    rhr = latest_day.get('resting_bpm')
    if pd.notna(rhr):
        print(f"   • RHR: {rhr:.1f} bpm")
        print(f"     Status: {get_status_emoji(rhr, df['resting_bpm'].mean(), df['resting_bpm'].std(), 'lower_is_better')}")

    # HRV
    hrv = latest_day.get('rmssd')
    if pd.notna(hrv):
        print(f"   • HRV (rMSSD): {hrv:.1f} ms")
        print(f"     Status: {get_status_emoji(hrv, df['rmssd'].mean(), df['rmssd'].std(), 'higher_is_better')}")

    # Stress
    stress = latest_day.get('stress_score')
    if pd.notna(stress):
        print(f"   • Stress Score: {stress:.0f} (Higher is better)")

    # --- 2. SLEEP ---
    print("\n💤 SLEEP QUALITY")
    sleep_score = latest_day.get('overall_score')
    if pd.notna(sleep_score):
        print(f"   • Score: {sleep_score:.0f} / 100")
        print(f"     Status: {get_status_emoji(sleep_score, df['overall_score'].mean(), df['overall_score'].std(), 'higher_is_better')}")

        # Sleep Composition
        deep = latest_day.get('sleep_deep', 0)
        rem = latest_day.get('sleep_rem', 0)
        print(f"     Composition: {deep:.0f}m Deep + {rem:.0f}m REM")
    else:
        print("   • No sleep data.")

    # --- 3. READINESS ---
    print("\n🔋 READINESS (Daily Form)")
    readiness = latest_day.get('readiness_raw')
    if pd.notna(readiness):
        if readiness > 1.0:
            advice = "🚀 GO HARD! System primed."
        elif readiness < -1.0:
            advice = "💤 REST DAY. High stress detected."
        else:
            advice = "⚖️ STEADY. Train normally."
        print(f"   • Index: {readiness:.2f}")
        print(f"   • Advice: {advice}")
    else:
        print("   • Not available.")

    # --- 4. ACTIVITY ---
    print("\n🔥 METABOLISM & ACTIVITY")
    cals = latest_day.get('calories_total')
    if pd.notna(cals):
        print(f"   • Total Burn: {cals:.0f} kcal")
        if pd.notna(latest_day.get('active_calories')):
            print(f"     └─ Active: {latest_day['active_calories']:.0f} kcal")

    intensity = latest_day.get('intensity_index')
    if pd.notna(intensity):
        print(f"   • Intensity: {intensity:.1f} kcal/min")

    weight = latest_day.get('weight')
    if pd.notna(weight):
        print(f"   • Weight: {weight:.1f} Kg")

    print(f"\n==========================================")

if __name__ == "__main__":
    generate_briefing()