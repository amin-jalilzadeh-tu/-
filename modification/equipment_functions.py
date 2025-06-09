"""
equipment_functions.py

Functions for creating and applying Electric Equipment scenarios.
"""
import pandas as pd
from modification.common_utils import generate_multiple_param_sets, save_param_scenarios_to_csv
from modification.hvac_functions import _modify_schedule_compact # Re-use the schedule modifier

def create_equipment_scenarios(df_equipment_input, building_id, num_scenarios, picking_method, random_seed, scenario_csv_out):
    """Generates scenarios for equipment parameters from a structured CSV."""
    # Filter for parameters that have a min/max range to vary them
    df_to_vary = df_equipment_input.dropna(subset=['min_val', 'max_val'])
    
    equipment_scenarios = generate_multiple_param_sets(
        df_main_sub=df_to_vary,
        num_sets=num_scenarios,
        picking_method=picking_method
    )
    save_param_scenarios_to_csv(equipment_scenarios, building_id, scenario_csv_out)
    print(f"[INFO] Wrote scenario equipment params to {scenario_csv_out}")
    df_scen = pd.read_csv(scenario_csv_out)
    return df_scen

def apply_equipment_params_to_idf(idf, df_equip_scen):
    """
    Applies equipment parameters to the IDF.
    This modifies the 'ElectricEquipment' object and its schedule.
    """
    if df_equip_scen.empty:
        return

    print(f"[INFO] Applying {len(df_equip_scen)} equipment parameter modifications...")
    
    params = {row.param_name: row.assigned_value for row in df_equip_scen.itertuples()}

    # --- 1. Modify the ElectricEquipment Object ---
    # The object is likely named for the zonelist, e.g., "ALL_ZONES_ElecEquip"
    equip_objects = idf.idfobjects["ELECTRICEQUIPMENT"]
    if not equip_objects:
        print("[WARN] No ELECTRICEQUIPMENT objects found in IDF.")
        return
        
    # Assume we modify all equipment objects found
    for equip_obj in equip_objects:
        if 'equip_wm2' in params:
            equip_obj.Watts_per_Zone_Floor_Area = params['equip_wm2']
            print(f"  - Modified {equip_obj.Name}: Watts_per_Zone_Floor_Area = {params['equip_wm2']:.2f}")
        if 'equip_fraction_latent' in params:
            equip_obj.Fraction_Latent = params['equip_fraction_latent']
        if 'equip_fraction_radiant' in params:
            equip_obj.Fraction_Radiant = params['equip_fraction_radiant']
        if 'equip_fraction_lost' in params:
            equip_obj.Fraction_Lost = params['equip_fraction_lost']

    # --- 2. Modify the Equipment Schedule ---
    day_val = params.get('tD')
    night_val = params.get('tN')
    
    if day_val is not None or night_val is not None:
        # We need to find the schedule name. It's often linked in the ElectricEquipment object.
        schedule_name = equip_objects[0].Schedule_Name # Assume all use the same schedule
        print(f"  - Modifying Schedule:Compact '{schedule_name}'")
        
        _modify_schedule_compact(
            idf=idf,
            schedule_name=schedule_name,
            day_value=params.get('tD', 500), # Provide a default if missing
            night_value=params.get('tN', 200),
            day_start="08:00", # Define your day/night hours
            day_end="20:00"
        )