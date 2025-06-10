"""
zone_sizing_functions.py

Functions for creating and applying Zone Sizing parameter scenarios.
"""
import pandas as pd
import random
import json
from modification.common_utils import generate_multiple_param_sets, save_param_scenarios_to_csv

# Dictionary to map CSV param_name to EnergyPlus Sizing:Zone field name
PARAM_TO_EP_FIELD_MAP = {
    "cooling_supply_air_temp": "Cooling_Design_Supply_Air_Temperature",
    "heating_supply_air_temp": "Heating_Design_Supply_Air_Temperature",
    "cooling_supply_air_hr": "Cooling_Design_Supply_Air_Humidity_Ratio",
    "heating_supply_air_hr": "Heating_Design_Supply_Air_Humidity_Ratio",
    "cooling_design_air_flow_method": "Cooling_Design_Air_Flow_Method",
    "heating_design_air_flow_method": "Heating_Design_Air_Flow_Method",
}

def create_zone_sizing_scenarios(df_sizing_input, building_id, num_scenarios, picking_method, random_seed, scenario_csv_out):
    """Generates scenarios for zone sizing parameters."""
    if random_seed:
        random.seed(random_seed)
        
    # Generate scenarios for numeric parameters first
    df_numeric = df_sizing_input.dropna(subset=['min_val', 'max_val'])
    numeric_scenarios = generate_multiple_param_sets(
        df_main_sub=df_numeric,
        num_sets=num_scenarios,
        picking_method=picking_method
    )
    
    # Handle non-numeric (choice-based) parameters
    df_choices = df_sizing_input.dropna(subset=['choices'])
    for scenario_dict in numeric_scenarios:
        for _, row in df_choices.iterrows():
            param_name = row['param_name']
            choices_str = row['choices']
            choices_list = json.loads(choices_str)
            scenario_dict[param_name] = random.choice(choices_list)

    save_param_scenarios_to_csv(numeric_scenarios, building_id, scenario_csv_out)
    print(f"[INFO] Wrote scenario zone sizing params to {scenario_csv_out}")
    df_scen = pd.read_csv(scenario_csv_out)
    return df_scen

def apply_zone_sizing_params_to_idf(idf, df_sizing_scen):
    """
    Applies zone sizing parameters to all Sizing:Zone objects in the IDF.
    """
    if df_sizing_scen.empty:
        return

    print(f"[INFO] Applying {len(df_sizing_scen)} zone sizing parameter modifications...")
    
    params = {row.param_name: row.assigned_value for row in df_sizing_scen.itertuples()}
    
    sizing_zone_objects = idf.idfobjects["SIZING:ZONE"]
    if not sizing_zone_objects:
        print("[WARN] No SIZING:ZONE objects found in IDF.")
        return

    # Apply the same parameters to ALL Sizing:Zone objects
    for sz_obj in sizing_zone_objects:
        print(f"  - Modifying SIZING:ZONE for '{sz_obj.Zone_or_ZoneList_Name}'")
        for param_name, param_value in params.items():
            if param_name in PARAM_TO_EP_FIELD_MAP:
                ep_field = PARAM_TO_EP_FIELD_MAP[param_name]
                try:
                    setattr(sz_obj, ep_field, param_value)
                    # print(f"    - Set {ep_field} = {param_value}") # Uncomment for verbose logging
                except Exception as e:
                    print(f"[ERROR] Could not set {ep_field} on {sz_obj.Name}: {e}")