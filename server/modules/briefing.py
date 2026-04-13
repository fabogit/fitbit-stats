import pandas as pd
import os
import json
from datetime import datetime

import config

# ==========================================
# CONFIGURATION
# ==========================================
DATA_FILE = os.path.join(config.CLIENT_PUBLIC_DIR, "fitbit_analysis.csv")

def get_status_emoji(value, mean, std, metric_type='lower_is_better'):
    """
    Returns an emoji and status text based on Z-Score.
    """
    if pd.isna(value) or pd.isna(mean) or pd.isna(std) or std == 0:
        return "⚪️", "N/A"

    z_score = (value - mean) / std

    if metric_type == 'lower_is_better':
        if z_score < -1.0:
            return "🟢", "EXCELLENT"
        if z_score > 1.0:
            return "🔴", "WARNING"
        return "⚪️", "NORMAL"
    else:  # higher_is_better (Sleep, HRV)
        if z_score > 1.0:
            return "🟢", "EXCELLENT"
        if z_score < -1.0:
            return "🔴", "WARNING"
        return "⚪️", "NORMAL"

def calculate_age(dob_str, target_date):
    """ Calculates age correctly at the given target_date. """
    try:
        dob = pd.to_datetime(dob_str)
        age = target_date.year - dob.year - \
            ((target_date.month, target_date.day) < (dob.month, dob.day))
        return age
    except:
        return 0

def load_data():
    """Loads the processed fitbit_analysis.csv dataset and indexes it by date."""
    if not os.path.exists(DATA_FILE):
        return None

    df = pd.read_csv(DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

def load_metrics(target_date=None):
    """ Loads user metrics from session_config.json and calculates age relative to target_date. """
    metrics = {"age": "N/A", "gender": "N/A", "height": "N/A"}
    config_path = os.path.join(config.CLIENT_PUBLIC_DIR, "session_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                sc = json.load(f)
                dob = sc.get("dob")
                if dob and target_date:
                    metrics["age"] = calculate_age(dob, target_date)
                else:
                    metrics["age"] = sc.get("age", "N/A")

                metrics["gender"] = sc.get("gender", "N/A")
                metrics["height"] = sc.get("height", "N/A")
        except:
            pass
    return metrics

def get_daily_brief(target_date_str=None):
    """Generates a structured daily briefing summary."""
    df = load_data()
    if df is None:
        return {"error": "Data file not found. Run ETL first."}

    # Select target date
    if target_date_str:
        try:
            t_date = pd.to_datetime(target_date_str)
            if t_date not in df.index:
                # Find the closest preceding date
                t_date = df.index[df.index <= t_date].max()
            latest_day = df.loc[t_date]
        except:
            latest_day = df.iloc[-1]
            t_date = df.index[-1]
    else:
        latest_day = df.iloc[-1]
        t_date = df.index[-1]

    user_metrics = load_metrics(t_date)
    display_date = t_date.strftime('%d %B %Y')
    profile_str = f"{user_metrics['age']}yo {user_metrics['gender']}"

    sections = []

    # --- 1. PHYSIOLOGY & RECOVERY ---
    physiology_metrics = []
    
    # RHR
    rhr = latest_day.get('resting_bpm')
    if pd.notna(rhr):
        emoji, status = get_status_emoji(rhr, df['resting_bpm'].mean(), df['resting_bpm'].std(), 'lower_is_better')
        physiology_metrics.append({
            "label": "Resting HR",
            "value": f"{rhr:.1f} bpm",
            "status": status,
            "statusEmoji": emoji
        })

    # HRV
    hrv = latest_day.get('rmssd')
    if pd.notna(hrv):
        emoji, status = get_status_emoji(hrv, df['rmssd'].mean(), df['rmssd'].std(), 'higher_is_better')
        physiology_metrics.append({
            "label": "HRV (rMSSD)",
            "value": f"{hrv:.1f} ms",
            "status": status,
            "statusEmoji": emoji
        })

    # Stress
    stress = latest_day.get('stress_score')
    if pd.notna(stress):
        physiology_metrics.append({
            "label": "Stress Score",
            "value": f"{stress:.0f}/100",
            "status": "N/A",
            "statusEmoji": "⚪️"
        })

    sections.append({
        "title": "PHYSIOLOGY & RECOVERY",
        "icon": "❤️",
        "metrics": physiology_metrics
    })

    # --- 2. SLEEP QUALITY ---
    sleep_metrics = []
    sleep_score = latest_day.get('overall_score')
    sleep_advice = None
    
    if pd.notna(sleep_score):
        emoji, status = get_status_emoji(sleep_score, df['overall_score'].mean(), df['overall_score'].std(), 'higher_is_better')
        
        deep = latest_day.get('sleep_deep', 0)
        rem = latest_day.get('sleep_rem', 0)
        
        sleep_metrics.append({
            "label": "Sleep Score",
            "value": f"{sleep_score:.0f} / 100",
            "status": status,
            "statusEmoji": emoji
        })
        
        sleep_advice = f"{deep:.0f}m Deep + {rem:.0f}m REM cycles recorded."
    else:
        sleep_metrics.append({
            "label": "Sleep Score",
            "value": "No data",
            "status": "N/A",
            "statusEmoji": "⚪️"
        })

    sections.append({
        "title": "SLEEP QUALITY",
        "icon": "💤",
        "metrics": sleep_metrics,
        "advice": sleep_advice
    })

    # --- 3. READINESS ---
    readiness_metrics = []
    readiness = latest_day.get('readiness_raw')
    readiness_advice = None
    
    if pd.notna(readiness):
        if readiness > 1.0:
            readiness_advice = "🚀 GO HARD! System primed."
        elif readiness < -1.0:
            readiness_advice = "💤 REST DAY. High stress detected."
        else:
            readiness_advice = "⚖️ STEADY. Train normally."
        
        readiness_metrics.append({
            "label": "Readiness Index",
            "value": f"{readiness:.2f}",
            "status": "READY" if readiness > 0 else "FATIGUED",
            "statusEmoji": "⚡️"
        })
    else:
        readiness_advice = "Not enough data for readiness calculation."

    sections.append({
        "title": "READINESS",
        "icon": "🔋",
        "metrics": readiness_metrics,
        "advice": readiness_advice
    })

    # --- 4. METABOLISM & ACTIVITY ---
    metabolism_metrics = []
    cals = latest_day.get('calories_total')
    if pd.notna(cals):
        metabolism_metrics.append({
            "label": "Total Burn",
            "value": f"{cals:.0f} kcal",
            "status": "ACTIVE",
            "statusEmoji": "🔥"
        })
        
        active_cals = latest_day.get('active_calories')
        if pd.notna(active_cals):
            metabolism_metrics.append({
                "label": "Active Energy",
                "value": f"{active_cals:.0f} kcal",
                "status": "BURNED",
                "statusEmoji": "🏃"
            })

    intensity = latest_day.get('intensity_index')
    if pd.notna(intensity):
        metabolism_metrics.append({
            "label": "Intensity",
            "value": f"{intensity:.1f} kcal/min",
            "status": "N/A",
            "statusEmoji": "📈"
        })

    weight = latest_day.get('weight')
    if pd.notna(weight):
        metabolism_metrics.append({
            "label": "Weight",
            "value": f"{weight:.1f} Kg",
            "status": "N/A",
            "statusEmoji": "⚖️"
        })

    sections.append({
        "title": "METABOLISM & ACTIVITY",
        "icon": "🔥",
        "metrics": metabolism_metrics
    })

    return {
        "date": display_date,
        "profile": profile_str,
        "sections": sections
    }
