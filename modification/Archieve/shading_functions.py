"""
shading_functions.py

Functions for creating and applying shading parameter scenarios.
"""
import pandas as pd
from modification.common_utils import generate_multiple_param_sets, save_param_scenarios_to_csv

# This dictionary maps the CSV param_name to the actual EnergyPlus field name.
PARAM_TO_EP_FIELD_MAP = {
    # Material:WindowBlind fields
    "slat_orientation": "Slat_Orientation",
    "slat_width": "Slat_Width",
    "slat_separation": "Slat_Separation",
    "slat_thickness": "Slat_Thickness",
    "slat_angle_deg": "Slat_Angle",
    "slat_conductivity": "Slat_Conductivity",
    "slat_beam_solar_transmittance": "Slat_Beam_Solar_Transmittance",
    "slat_beam_solar_reflectance": "Slat_Beam_Solar_Reflectance",
    "slat_diffuse_solar_transmittance": "Slat_Diffuse_Solar_Transmittance",
    "slat_diffuse_solar_reflectance": "Slat_Diffuse_Solar_Reflectance",
    "slat_beam_visible_transmittance": "Slat_Beam_Visible_Transmittance",
    "slat_beam_visible_reflectance": "Front_Side_Slat_Beam_Visible_Reflectance", # Note: E+ has front/back
    "slat_diffuse_visible_transmittance": "Slat_Diffuse_Visible_Transmittance",
    "slat_diffuse_visible_reflectance": "Front_Side_Slat_Diffuse_Visible_Reflectance", # Note: E+ has front/back
    "slat_ir_transmittance": "Slat_Infrared_Transmittance",
    "slat_ir_emissivity": "Front_Side_Slat_Infrared_Emissivity", # Note: E+ has front/back
    "blind_to_glass_distance": "Blind_to_Glass_Distance",
    "slat_opening_multiplier": "Slat_Opening_Multiplier",
    # ShadingControl fields could be added here if needed
}

def create_shading_scenarios(df_shading_input, building_id, num_scenarios, picking_method, random_seed, scenario_csv_out):
    """Generates scenarios for shading parameters from a structured CSV."""
    shading_scenarios = generate_multiple_param_sets(
        df_main_sub=df_shading_input,
        num_sets=num_scenarios,
        picking_method=picking_method
    )
    # The common util `save_param_scenarios_to_csv` doesn't preserve all columns,
    # so we build the dataframe manually here.
    rows = []
    for i, scenario_dict in enumerate(shading_scenarios):
        # We need to map the scenario values back to the original rows
        for _, row in df_shading_input.iterrows():
            param_name = row['param_name']
            if param_name in scenario_dict:
                new_row = row.to_dict()
                new_row['scenario_index'] = i
                new_row['ogc_fid'] = building_id
                new_row['assigned_value'] = scenario_dict[param_name]
                rows.append(new_row)

    df_out = pd.DataFrame(rows)

    # Ensure these two columns exist and are written first so the output matches
    # other scenario CSVs used in the modification workflow.
    if 'scenario_index' not in df_out.columns:
        df_out['scenario_index'] = pd.NA
    if 'ogc_fid' not in df_out.columns:
        df_out['ogc_fid'] = building_id
    ordered_cols = ['scenario_index', 'ogc_fid'] + [c for c in df_out.columns
                                                    if c not in ['scenario_index', 'ogc_fid']]
    df_out = df_out[ordered_cols]

    df_out.to_csv(scenario_csv_out, index=False)
    print(f"[INFO] Wrote scenario shading params to {scenario_csv_out}")
    return df_out


def apply_shading_params_to_idf(idf, df_shading_scen):
    """Applies shading parameters to the IDF by modifying Material:WindowBlind objects."""
    if df_shading_scen.empty:
        return

    print(f"[INFO] Applying {len(df_shading_scen)} shading parameter modifications...")
    
    # Group by the blind material name to modify each object once
    grouped = df_shading_scen.groupby('blind_material_name')

    for blind_name, group_df in grouped:
        try:
            # Find the blind material object
            blind_obj = idf.getobject("MATERIAL:WINDOWBLIND", blind_name)
            if not blind_obj:
                print(f"[WARN] Could not find MATERIAL:WINDOWBLIND named '{blind_name}'. Skipping.")
                continue

            print(f"  - Modifying MATERIAL:WINDOWBLIND '{blind_name}':")
            for row in group_df.itertuples():
                param_name = row.param_name
                param_value = row.assigned_value
                
                if param_name in PARAM_TO_EP_FIELD_MAP:
                    ep_field = PARAM_TO_EP_FIELD_MAP[param_name]
                    # Set the attribute on the eppy/geomeppy object
                    setattr(blind_obj, ep_field, param_value)
                    print(f"    - Set {ep_field} = {param_value}")

        except Exception as e:
            print(f"[ERROR] Failed to modify blind material '{blind_name}': {e}")