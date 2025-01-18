"""
Example script for running a sensitivity analysis on scenario-based simulations.

Workflow:
1) Collect scenario definitions from CSV files in output/scenarios/.
2) For each scenario, (optionally) generate an IDF & run EnergyPlus, or skip if already done.
3) Load the simulation results from 'merged_daily_mean_mocked.csv' (or your actual file).
4) Merge scenario parameters with results.
5) Perform a simple correlation-based sensitivity analysis (or partial correlation).
6) Save a 'sensitivity_report.csv' summarizing which parameters most affect the outputs.
7) Optionally feed top parameters into calibration/next steps.

Author: Example
"""
import os
import numpy as np
import pandas as pd
from pathlib import Path

# If you want advanced sensitivity, you might do:
# from SALib.analyze import sobol
# from SALib.sample import saltelli
# etc.


def load_scenario_file(filepath):
    """
    Load a scenario CSV (e.g. 'scenario_params_dhw.csv') into a pandas DataFrame.
    Expects columns: [scenario_index, ogc_fid, param_name, assigned_value].
    """
    df = pd.read_csv(filepath)
    return df


def generate_idf_and_run_simulations(all_scenarios_df, scenario_name):
    """
    Placeholder function that:
    1. Groups scenario data by scenario_index.
    2. For each scenario, merges all assigned parameters into an IDF.
    3. Runs E+ or calls the existing 'modification/' pipeline, saving results.

    In a real pipeline, you'd call:
      - modification.main_modifi.apply_... for each scenario
      - epw.run_epw_sims.simulate_all(...) 
    Here we just print and assume the user runs them or has results already.
    """
    grouped = all_scenarios_df.groupby("scenario_index")
    for scenario_idx, subdf in grouped:
        print(f"\n[INFO] Running scenario: {scenario_name}, idx={scenario_idx}")
        # 1. Merge param sets from subdf
        # 2. Generate IDF file -> "scenario_{scenario_idx}.idf"
        # 3. Run E+ or skip if done
        # ...
        # We'll just demonstrate logging:
        param_summary = subdf[["param_name", "assigned_value"]].head(5).to_dict(orient="records")
        print(f"[DEBUG] Example param subset: {param_summary}")
    print(f"[INFO] Completed sim for all scenarios in {scenario_name}")


def load_sim_results(results_csv):
    """
    Load your merged E+ results from CSV, e.g. 'merged_daily_mean_mocked.csv'.
    Expected columns: [BuildingID, VariableName, 01-Jan, 02-Jan, ...].
    We'll pivot to wide format or keep as is for correlation.
    """
    df = pd.read_csv(results_csv)
    return df


def prepare_sensitivity_data(scenarios_dict, sim_results):
    """
    Merge scenario parameters with simulation results to build a dataset for correlation analysis.
    Steps:
      1) Convert scenario parameters to wide form (param columns).
      2) Link scenario_index -> BuildingID or some identifying key in sim_results.
      3) Extract or aggregate the relevant output metrics (e.g. total consumption).
    """

    # ------------- Part A: Combine all scenario CSVs into one DataFrame -------------
    all_scenarios = []
    for scenario_name, df_scenario in scenarios_dict.items():
        df_temp = df_scenario.copy()
        df_temp["scenario_type"] = scenario_name
        all_scenarios.append(df_temp)
    combined_df = pd.concat(all_scenarios, ignore_index=True)

    # Pivot so each param_name becomes a column, scenario_index is the row
    pivot_df = combined_df.pivot_table(
        index=["scenario_index", "ogc_fid"],
        columns="param_name",
        values="assigned_value",
        aggfunc="first"  # if multiple, just take the first
    ).reset_index()

    # ------------- Part B: Link to simulation results -------------
    # Assume scenario_index matches BuildingID in results
    pivot_df.rename(columns={"scenario_index": "BuildingID"}, inplace=True)

    # Melt and sum daily results in sim_results
    melted = sim_results.melt(
        id_vars=["BuildingID", "VariableName"],
        var_name="Day",
        value_name="Value"
    )
    daily_sum = melted.groupby(["BuildingID", "VariableName"])["Value"].sum().reset_index()
    daily_sum.rename(columns={"Value": "TotalEnergy_J"}, inplace=True)

    # Merge param pivot with daily sums
    merged_sens_df = pd.merge(
        pivot_df, daily_sum,
        on="BuildingID",
        how="inner"
    )
    return merged_sens_df


def compute_sensitivity(merged_sens_df, target_variable="Heating:EnergyTransfer [J](Hourly)"):
    """
    Example: Filter to the target_variable, then compute correlation
    of each parameter with 'TotalEnergy_J'. 
    Returns a DataFrame with 'Parameter' and 'Correlation'.
    """
    df_var = merged_sens_df[merged_sens_df["VariableName"] == target_variable].copy()
    if df_var.empty:
        print(f"[WARN] No rows found for variable={target_variable}, cannot compute sensitivity.")
        return pd.DataFrame()

    exclude_cols = ["BuildingID", "ogc_fid", "VariableName", "TotalEnergy_J"]
    param_cols = [c for c in df_var.columns if c not in exclude_cols]

    correlations = []
    for col in param_cols:
        if pd.api.types.is_numeric_dtype(df_var[col]):
            corr = df_var[[col, "TotalEnergy_J"]].corr().iloc[0, 1]
            correlations.append((col, corr))
        else:
            correlations.append((col, np.nan))

    corr_df = pd.DataFrame(correlations, columns=["Parameter", "Correlation"])
    corr_df["AbsCorrelation"] = corr_df["Correlation"].abs()
    corr_df.sort_values("AbsCorrelation", ascending=False, inplace=True)
    return corr_df


def main():
    """
    Main function to illustrate a sensitivity analysis pipeline.
    """
    # 1) Load scenario CSVs from 'output/scenarios' folder
    scenarios_folder = r"D:\Documents\E_Plus_2030_py\output\scenarios"
    scenario_files = {
        "dhw": "scenario_params_dhw.csv",
        "elec": "scenario_params_elec.csv",
        "fenez": "scenario_params_fenez.csv",
        "hvac": "scenario_params_hvac.csv",
        "vent": "scenario_params_vent.csv",
    }

    scenarios_dict = {}
    for name, fname in scenario_files.items():
        fpath = os.path.join(scenarios_folder, fname)
        if os.path.exists(fpath):
            print(f"[INFO] Loading scenario file for {name}: {fpath}")
            df_scenario = load_scenario_file(fpath)
            scenarios_dict[name] = df_scenario
        else:
            print(f"[WARN] File not found: {fpath} - skipping.")
    
    # 2) (Optionally) Generate IDFs & Run E+ for each scenario set
    for scenario_name, df_scenario in scenarios_dict.items():
        generate_idf_and_run_simulations(df_scenario, scenario_name)

    # 3) Load aggregated simulation results
    results_csv = r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv"
    sim_results = load_sim_results(results_csv)

    # 4) Prepare DataFrame merging param values with results
    merged_sens_df = prepare_sensitivity_data(scenarios_dict, sim_results)

    # 5) Perform correlation-based sensitivity for multiple target variables
    target_vars = [
        "Heating:EnergyTransfer [J](Hourly)",
        "Electricity:Facility [J](Hourly)",
        "MYDHW_0_WATERHEATER:Water Heater Heating Energy [J](Daily)"
    ]
    final_report = []
    for var in target_vars:
        corr_df = compute_sensitivity(merged_sens_df, target_variable=var)
        corr_df["TargetVariable"] = var
        final_report.append(corr_df)

    if final_report:
        final_report_df = pd.concat(final_report, ignore_index=True)
    else:
        final_report_df = pd.DataFrame()

    # 6) Save sensitivity report
    out_csv = "sensitivity_report.csv"
    final_report_df.to_csv(out_csv, index=False)
    print(f"\n[INFO] Sensitivity report saved to: {out_csv}")

    # 7) Identify top 3 parameters by absolute correlation for each variable
    top_params = (
        final_report_df
        .sort_values("AbsCorrelation", ascending=False)
        .groupby("TargetVariable")
        .head(3)
    )
    print("\n=== Top 3 Parameters (by |Correlation|) for Each Variable ===")
    print(top_params)

    # 8) Additional steps like calibration/optimization could go here.


if __name__ == "__main__":
    main()
