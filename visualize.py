import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. CONFIGURATION
# ==========================================
# Ensuring this matches the output from analyze.py
INPUT_FILE = "fitbit_analysis.csv"
OUTPUT_DIR = "plots"

# Create output folder if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Set visual style
sns.set_theme(style="whitegrid")
# Increase figure size slightly to accommodate margins
plt.rcParams['figure.figsize'] = (14, 8)

# ==========================================
# 2. LOAD DATA
# ==========================================


def load_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Please run analyze.py first.")
        return None

    df = pd.read_csv(INPUT_FILE)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

# ==========================================
# 3. PLOTTING FUNCTIONS
# ==========================================


def plot_weight_vs_calories_trend(df):
    """
    Double Y-axis: Shows Weight trend vs Calories burned.
    """
    df['cal_smooth'] = df['calories_total'].rolling(window=7).mean()
    df_weight = df.dropna(subset=['weight'])

    fig, ax1 = plt.subplots()

    # Left Axis: Weight
    color = 'black'
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Weight (Kg)', color=color)
    ax1.plot(df_weight.index, df_weight['weight'], color=color,
             marker='o', markersize=3, linestyle='-', alpha=0.7, label='Weight')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(False)

    # Right Axis: Calories
    ax2 = ax1.twinx()
    color = 'tab:orange'
    ax2.set_ylabel('Total Calories (7-day Avg)', color=color)
    ax2.plot(df.index, df['cal_smooth'], color=color,
             linewidth=2, label='Calories (7-day Avg)')
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title('Relationship: Body Weight vs Caloric Expenditure')

    # Rotate dates automatically and adjust layout
    fig.autofmt_xdate()
    fig.tight_layout()

    output_path = f"{OUTPUT_DIR}/weight_vs_calories.png"
    plt.savefig(output_path)
    print(f"-> Saved {output_path}")
    plt.close()


def plot_rhr_distribution(df):
    """
    Histogram + Density (KDE) of Resting Heart Rate.
    """
    plt.figure()

    sns.histplot(df['resting_bpm'], kde=True,
                 bins=20, color='crimson', alpha=0.6)

    mean_rhr = df['resting_bpm'].mean()
    plt.axvline(mean_rhr, color='black', linestyle='--',
                label=f'Mean: {mean_rhr:.1f}')

    plt.title('Resting Heart Rate (RHR) Distribution')
    plt.xlabel('Beats per minute (bpm)')
    plt.ylabel('Frequency (Days)')
    plt.legend()
    plt.tight_layout()

    output_path = f"{OUTPUT_DIR}/rhr_distribution.png"
    plt.savefig(output_path)
    print(f"-> Saved {output_path}")
    plt.close()


def plot_weight_vs_rhr_scatter(df):
    """
    Scatter plot: Weight vs Resting Heart Rate.
    """
    data = df.dropna(subset=['weight', 'resting_bpm'])

    plt.figure()

    sns.scatterplot(
        x='weight',
        y='resting_bpm',
        data=data,
        hue=data.index.month,
        palette='viridis',
        s=60,
        alpha=0.8
    )

    sns.regplot(x='weight', y='resting_bpm', data=data,
                scatter=False, color='red', line_kws={'alpha': 0.5})

    plt.title('Correlation: Weight vs Resting Heart Rate')
    plt.xlabel('Weight (Kg)')
    plt.ylabel('RHR (bpm)')
    plt.legend(title='Month', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    output_path = f"{OUTPUT_DIR}/weight_vs_rhr_scatter.png"
    plt.savefig(output_path)
    print(f"-> Saved {output_path}")
    plt.close()


def plot_correlation_matrix(df):
    """
    Generates a heatmap showing correlations between key metrics.
    """
    cols = ['resting_bpm', 'overall_score', 'deep_sleep_in_minutes',
            'calories_total', 'very_active_minutes', 'readiness_raw', 'weight']

    corr = df[cols].corr()

    # Increase figure size for this specific plot since labels are long
    plt.figure(figsize=(12, 10))

    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", vmin=-1, vmax=1)
    plt.title('Correlation Matrix')

    # Rotate labels to prevent cutoff
    plt.xticks(rotation=45, ha='right')  # Rotate bottom labels
    plt.yticks(rotation=0)              # Keep side labels straight
    plt.tight_layout()

    output_path = f"{OUTPUT_DIR}/correlation_matrix.png"
    plt.savefig(output_path)
    print(f"-> Saved {output_path}")
    plt.close()


def plot_trends(df):
    """
    Plots 7-day rolling averages for RHR and Readiness.
    """
    df['rhr_smooth'] = df['resting_bpm'].rolling(window=7).mean()
    df['readiness_smooth'] = df['readiness_raw'].rolling(window=7).mean()

    fig, ax1 = plt.subplots()

    color = 'tab:red'
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Resting Heart Rate (bpm)', color=color)
    ax1.plot(df.index, df['rhr_smooth'], color=color, label='RHR (7-day Avg)')
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()
    color = 'tab:blue'
    ax2.set_ylabel('Readiness Score (Z-Score)', color=color)
    ax2.plot(df.index, df['readiness_smooth'], color=color,
             linestyle='--', label='Readiness (7-day Avg)')
    ax2.tick_params(axis='y', labelcolor=color)

    ax2.axhline(0, color='gray', linestyle=':', alpha=0.5)

    plt.title('Health Trend: Heart Health vs Readiness')

    # Rotate dates automatically
    fig.autofmt_xdate()
    fig.tight_layout()

    output_path = f"{OUTPUT_DIR}/health_trends.png"
    plt.savefig(output_path)
    print(f"-> Saved {output_path}")
    plt.close()


def plot_activity_vs_sleep(df):
    """
    Scatter plot to see if high activity days lead to better sleep.
    """
    plt.figure()

    sns.regplot(x='calories_total', y='overall_score', data=df,
                scatter_kws={'alpha': 0.5}, line_kws={'color': 'red'})

    plt.title('Impact of Daily Calories on Sleep Score')
    plt.xlabel('Total Calories Burned')
    plt.ylabel('Sleep Score')
    plt.tight_layout()

    output_path = f"{OUTPUT_DIR}/activity_vs_sleep.png"
    plt.savefig(output_path)
    print(f"-> Saved {output_path}")
    plt.close()


def plot_weekly_distribution(df):
    """
    Boxplot showing performance by Day of the Week.
    """
    df['weekday'] = df.index.day_name()
    order = ['Monday', 'Tuesday', 'Wednesday',
             'Thursday', 'Friday', 'Saturday', 'Sunday']

    plt.figure()
    sns.boxplot(x='weekday', y='readiness_raw',
                data=df, order=order, hue='weekday', palette="Set2", legend=False)
    plt.title('Readiness Distribution by Day of Week')
    plt.ylabel('Readiness Score')

    # Rotate labels so "Wednesday" fits comfortably
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()

    output_path = f"{OUTPUT_DIR}/weekly_readiness.png"
    plt.savefig(output_path)
    print(f"-> Saved {output_path}")
    plt.close()


# ==========================================
# 4. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("--- Starting Visualization ---")

    df = load_data()

    if df is not None:
        plot_correlation_matrix(df)
        plot_trends(df)
        plot_activity_vs_sleep(df)
        plot_weekly_distribution(df)
        plot_weight_vs_calories_trend(df)
        plot_rhr_distribution(df)
        plot_weight_vs_rhr_scatter(df)

    print("\nAll plots generated in /plots folder.")
