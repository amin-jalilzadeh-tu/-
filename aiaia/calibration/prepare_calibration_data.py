# Calibration\\prepare_calibration_data.py

import os
import pandas as pd
import numpy as np


def load_data(
    real_data_csv: str,
    sim_data_csv: str,
    validation_report_csv: str,
    master_params_csv: str
):
    """
    Loads the four main CSV files into DataFrames.

    :param real_data_csv: Path to the real measured data CSV.
    :param sim_data_csv: Path to the simulated data CSV.
    :param validation_report_csv: Path to the validation report CSV.
    :param master_params_csv: Path to the master parameters CSV.
    :return: A tuple of DataFrames: (df_real, df_sim, df_val, df_params)
    """
    df_real = pd.read_csv(real_data_csv)
    df_sim = pd.read_csv(sim_data_csv)
    df_val = pd.read_csv(validation_report_csv)
    df_params = pd.read_csv(master_params_csv)
    return df_real, df_sim, df_val, df_params


def filter_numeric_parameters(df_params: pd.DataFrame) -> pd.DataFrame:
    """
    Filters out any parameters that are purely text-based.
    For instance, if you only want to calibrate numeric parameters
    that have valid min/max ranges.

    - We'll define 'numeric parameter' as one that has a not-null
      min_value and max_value, or at least is recognized as float.

    :param df_params: The master parameters DataFrame with columns like
                      ['BuildingID', 'param_name', 'assigned_value', 'min_value', 'max_value'].
    :return: Filtered DataFrame containing only numeric-eligible parameters.
    """
    # Example rule: keep rows where min_value and max_value are not null AND are numeric
    # (If you have a different criterion, adjust accordingly.)
    mask_numeric = (
        df_params["min_value"].notna() &
        df_params["max_value"].notna()
    )
    df_numeric = df_params[mask_numeric].copy()

    # Alternatively, you could check for actual float values
    # for assigned_value, but only if min/max are also valid:
    # df_numeric = df_numeric[pd.to_numeric(df_numeric['assigned_value'], errors='coerce').notna()]

    return df_numeric


def create_param_set_id_column(df_params: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures there's a unique 'param_set_id' for each row in df_params.
    If your data already has a unique ID that groups multiple param_names
    into a single 'parameter set', you'll want to adapt this function.

    For demonstration, we combine BuildingID and param_name, or we
    could combine all param_name + assigned_value in a group, etc.

    :param df_params: The DataFrame of parameters.
    :return: The same DataFrame but with a new column 'param_set_id'.
    """
    # Simple approach: each row is unique anyway, so param_set_id = index
    df_params["param_set_id"] = df_params.index.astype(str)

    # If you have multiple parameters that belong to the *same* set,
    # you might group them by BuildingID or some other grouping logic.
    # For example:
    #   df_params['param_set_id'] = (
    #       df_params['BuildingID'].astype(str) + "_" +
    #       df_params.groupby('BuildingID').cumcount().astype(str)
    #   )
    #
    # But in real practice, you might have a more sophisticated approach.

    return df_params


def merge_params_with_validation(
    df_val: pd.DataFrame,
    df_params: pd.DataFrame,
    how: str = "inner"
) -> pd.DataFrame:
    """
    Example function to merge validation report with parameter info
    on a common key 'param_set_id'.
    """
    # 1) Rename 'SimBldg' => 'param_set_id'
    df_val = df_val.rename(columns={'SimBldg': 'param_set_id'})
    
    # 2) Convert both sides to the same type
    df_val['param_set_id'] = df_val['param_set_id'].astype(str)
    df_params['param_set_id'] = df_params['param_set_id'].astype(str)

    # 3) Merge on 'param_set_id'
    df_merged = pd.merge(df_val, df_params, on="param_set_id", how=how)
    return df_merged



def prepare_calibration_data(
    real_data_csv: str,
    sim_data_csv: str,
    validation_report_csv: str,
    master_params_csv: str
):
    """
    1. Loads all CSVs into DataFrames.
    2. Filters numeric parameters if desired.
    3. Creates or ensures we have a 'param_set_id' in df_params.
    4. Optionally merges validation info and parameters together.

    :return: A dictionary of DataFrames for convenience.
    """
    # 1) Load data
    df_real, df_sim, df_val, df_params = load_data(
        real_data_csv,
        sim_data_csv,
        validation_report_csv,
        master_params_csv
    )

    # 2) Filter numeric parameters only (optional)
    df_numeric_params = filter_numeric_parameters(df_params)

    # 3) Create param_set_id in the parameter DataFrame
    df_numeric_params = create_param_set_id_column(df_numeric_params)

    # 4) Merge with validation data if you want a single DataFrame
    #    that has param_set_id, CVRMSE, min_value, max_value, etc.
    #    (This is optional, depending on your calibration approach.)
    df_merged = merge_params_with_validation(df_val, df_numeric_params)

    # Return them for further use
    return {
        "df_real": df_real,
        "df_sim": df_sim,
        "df_val": df_val,
        "df_params_raw": df_params,           # original
        "df_params_numeric": df_numeric_params,  # numeric only
        "df_merged": df_merged
    }


# -----------------------------------------------------------------------------
# Example usage (test this in a if __name__=="__main__": block or from another script)
if __name__ == "__main__":
    real_data_csv = r"D:\Documents\E_Plus_2030_py\output\results\mock_merged_daily_mean.csv"
    sim_data_csv = r"D:\Documents\E_Plus_2030_py\output\results\merged_daily_mean_mocked.csv"
    validation_report_csv = r"D:\Documents\E_Plus_2030_py\validation_report.csv"
    master_params_csv = r"D:\Documents\E_Plus_2030_py\output\assigned\master_parameters_mock.csv"

    data_dict = prepare_calibration_data(
        real_data_csv,
        sim_data_csv,
        validation_report_csv,
        master_params_csv
    )

    print("[INFO] DF_REAL shape:", data_dict["df_real"].shape)
    print("[INFO] DF_SIM shape:", data_dict["df_sim"].shape)
    print("[INFO] DF_VAL shape:", data_dict["df_val"].shape)
    print("[INFO] DF_PARAMS_RAW shape:", data_dict["df_params_raw"].shape)
    print("[INFO] DF_PARAMS_NUMERIC shape:", data_dict["df_params_numeric"].shape)
    print("[INFO] DF_MERGED shape:", data_dict["df_merged"].shape)
    # ... further analysis ...
