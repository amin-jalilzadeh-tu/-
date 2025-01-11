# validation/compare_sims_with_measured.py
import pandas as pd

def load_csv_as_df(real_data_path, sim_data_path):
    """
    Loads real and simulated data from CSV into DataFrames.
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

def align_data_for_variable(df_real, df_sim, building_id, variable_name):
    """
    Returns aligned arrays of sim vs. obs for a given building & variable.
    Expects wide-format columns like: '01-Jan', '02-Jan', ...
    """
    # 1) Subset real
    real_sel = df_real[
        (df_real['BuildingID'] == building_id) &
        (df_real['VariableName'] == variable_name)
    ]
    # 2) Subset sim
    sim_sel = df_sim[
        (df_sim['BuildingID'] == building_id) &
        (df_sim['VariableName'] == variable_name)
    ]

    print(f"   > Aligning for Bldg={building_id}, Var={variable_name}")
    print(f"   > real_sel shape={real_sel.shape}, sim_sel shape={sim_sel.shape}")

    if real_sel.empty or sim_sel.empty:
        # Return empty arrays if there's no data to compare
        return [], [], pd.DataFrame()

    # 3) Melt them from wide to long
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

    print("   > real_long shape=", real_long.shape)
    print("   > sim_long  shape=", sim_long.shape)

    # 4) Merge on 'Date'
    merged = pd.merge(
        real_long[['Date','Value']], 
        sim_long[['Date','Value']],
        on='Date', how='inner', suffixes=('_obs','_sim')
    )

    print("   > merged shape=", merged.shape)
    return merged['Value_sim'].values, merged['Value_obs'].values, merged
