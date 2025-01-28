# validation/compare_sims_with_measured.py
import pandas as pd

def load_csv_as_df(real_data_path, sim_data_path):
    """
    Loads real and simulated data from CSV into DataFrames.
    Just a simple utility function, used if needed.
    """
    print(f"[DEBUG] Loading real data from: {real_data_path}")
    print(f"[DEBUG] Loading sim data  from: {sim_data_path}")

    df_real = pd.read_csv(real_data_path)
    df_sim  = pd.read_csv(sim_data_path)

    print("[DEBUG] df_real shape:", df_real.shape)
    print("[DEBUG] df_sim  shape:", df_sim.shape)
    print("[DEBUG] df_real columns:", df_real.columns.to_list())
    print("[DEBUG] df_sim columns: ", df_sim.columns.to_list())
    return df_real, df_sim


def align_data_for_variable(df_real, df_sim, real_building_id, sim_building_id, variable_name):
    """
    Returns aligned arrays of sim vs. obs for a given (real_building_id, sim_building_id, variable).
    - df_real and df_sim should be *already filtered* to the appropriate building + var
      (i.e., df_real_sub, df_sim_sub).
    - This function melts them from wide to long format and merges on 'Date'.

    Returns: (sim_values_array, obs_values_array, merged_dataframe)
    """

    # 1) Filter again for safety, though presumably df_real and df_sim are already subset
    real_sel = df_real[
        (df_real['BuildingID'] == real_building_id) &
        (df_real['VariableName'] == variable_name)
    ]
    sim_sel  = df_sim[
        (df_sim['BuildingID'] == sim_building_id) &
        (df_sim['VariableName'] == variable_name)
    ]

    # Debug prints
    print(f"   > Aligning real Bldg={real_building_id} vs sim Bldg={sim_building_id}, Var={variable_name}")
    print(f"   > real_sel shape={real_sel.shape}, sim_sel shape={sim_sel.shape}")

    # If empty, return empty arrays
    if real_sel.empty or sim_sel.empty:
        return [], [], pd.DataFrame()

    # 2) Melt from wide to long
    real_long = real_sel.melt(
        id_vars=['BuildingID','VariableName'],
        var_name='Date',
        value_name='Value'
    ).dropna(subset=['Value'])

    sim_long = sim_sel.melt(
        id_vars=['BuildingID','VariableName'],
        var_name='Date',
        value_name='Value'
    ).dropna(subset=['Value'])

    # 3) Merge on 'Date'
    merged = pd.merge(
        real_long[['Date','Value']],
        sim_long[['Date','Value']],
        on='Date', how='inner', suffixes=('_obs','_sim')
    )

    # 4) Return arrays plus the merged DataFrame
    return merged['Value_sim'].values, merged['Value_obs'].values, merged
