from modules import etl, metrics

def main():
    # 1. Load & Merge
    df = etl.merge_all_data()

    if df is not None:
        # 2. Calculate Metrics
        df = metrics.calculate_readiness(df)
        df = metrics.calculate_metabolic_metrics(df)

        # 3. Preview
        cols = ['resting_bpm', 'readiness_raw', 'bmr', 'active_calories']
        print("\n=== HEAD ===")
        print(df[[c for c in cols if c in df.columns]].head())

        # 4. Export
        df.to_csv("fitbit_analysis.csv")
        etl.export_to_json(df)

if __name__ == "__main__":
    main()