# main.py
from validation.validate_results import validate_data, bar_chart_metrics

def main():
    real_data_csv = "D:/Documents/E_Plus_2030_py/output/mock_data.csv"
    sim_data_csv  = "D:/Documents/E_Plus_2030_py/output/results/merged_daily_mean.csv"

    print("=== Starting Validation ===")
    metric_results = validate_data(real_data_csv, sim_data_csv,
                                   threshold_cv_rmse=30.0)

    # Print a summary of metrics for each Building-Variable combo
    print("\n=== Validation Summary ===")
    for key, mvals in metric_results.items():
        b_id, var_name = key
        print(f"Building={b_id}, Var={var_name} => "
              f"MBE={mvals['MBE']:.2f}, CV(RMSE)={mvals['CVRMSE']:.2f}, "
              f"NMBE={mvals['NMBE']:.2f}, Pass={mvals['Pass']}")

    # Show a bar chart with CV(RMSE) across all items:
    bar_chart_metrics(metric_results, title="CV(RMSE) Validation Results")

if __name__ == "__main__":
    main()
