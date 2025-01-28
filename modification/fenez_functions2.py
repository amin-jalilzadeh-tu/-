"""
fenez_functions2.py

This module provides functions for applying fenestration & envelope parameters 
to an EnergyPlus IDF, analogous to HVAC or Vent modules.

Contents:
  1) apply_building_level_fenez(...) => calls update_construction_materials, 
     assign_constructions_to_surfaces, add_fenestration, etc.
  2) apply_object_level_fenez(...)  => advanced approach that processes 
     'structured_fenez_params.csv' row by row, updating IDF objects directly.
  3) create_fenez_scenarios(...)    => (NEW) generates a scenario-level DataFrame
     with sub_key, param_min, param_max, etc., for each scenario, potentially 
     applying random picks or custom selection logic. This can be saved as
     'scenario_params_fenez.csv'.
"""

import random
import pandas as pd

# -----------------------------------------------------------------------
#  Imports from your local modules (assumed to exist)
# -----------------------------------------------------------------------
from idf_objects.fenez.materials import (
    update_construction_materials,
    assign_constructions_to_surfaces
)
from idf_objects.fenez.fenestration import add_fenestration


##############################################################################
# 1) BUILDING-LEVEL FENESTRATION
##############################################################################
def apply_building_level_fenez(
    idf,
    building_row,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config_fenez=None,
    assigned_fenez_log=None,
    add_windows=True,
    use_computed_wwr=False,
    include_doors_in_wwr=False
):
    """
    A high-level function to:
      1) Generate new Materials & Constructions from fenestration data 
         (using update_construction_materials).
      2) Assign those Constructions to surfaces (assign_constructions_to_surfaces).
      3) Optionally call add_fenestration(...) to set WWR or create new windows.

    building_row:
      - A dict (or Series) with "ogc_fid", "building_function", "age_range", etc.

    user_config_fenez:
      - A merged fenestration dictionary for this building (like res_data or nonres_data).

    assigned_fenez_log:
      - If provided, logs final picks (R-values, thickness, WWR, etc.).

    add_windows:
      - If True, calls add_fenestration(...) to create new windows or set WWR.

    use_computed_wwr, include_doors_in_wwr:
      - Passed to add_fenestration(...) for computing WWR from sub-element areas, etc.

    Returns:
      construction_map : dict, mapping sub-element => construction name
    """
    if random_seed is not None:
        random.seed(random_seed)

    ########################################################################
    # 1) Update constructions & materials
    ########################################################################
    construction_map = update_construction_materials(
        idf=idf,
        building_row=building_row,
        building_index=None,  # or your building index
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=user_config_fenez,  # <= the dictionary with final picks
        assigned_fenez_log=assigned_fenez_log
    )

    # 2) Assign them to surfaces
    assign_constructions_to_surfaces(idf, construction_map)

    ########################################################################
    # 3) Optionally add fenestration (windows, WWR, etc.)
    ########################################################################
    if add_windows:
        bldg_func = str(building_row.get("building_function", "residential")).lower()

        # We'll pass user_config_fenez to either res_data or nonres_data depending on building_function
        res_dict = None
        nonres_dict = None

        if bldg_func == "residential":
            res_dict = user_config_fenez
        else:
            nonres_dict = user_config_fenez

        add_fenestration(
            idf=idf,
            building_row=building_row,
            scenario=scenario,
            calibration_stage=calibration_stage,
            strategy=strategy,
            random_seed=random_seed,
            res_data=res_dict,
            nonres_data=nonres_dict,
            assigned_fenez_log=assigned_fenez_log,
            use_computed_wwr=use_computed_wwr,
            include_doors_in_wwr=include_doors_in_wwr
        )

    return construction_map


##############################################################################
# 2) OBJECT-LEVEL FENESTRATION
##############################################################################
def apply_object_level_fenez(idf, df_fenez):
    """
    Reads 'structured_fenez_params.csv' row by row. 
    Each row might specify:
       - ogc_fid
       - sub_key (like "top_opq", "exterior_wall_opq", etc.)
       - eplus_object_type (MATERIAL, MATERIAL:NOMASS, WINDOWMATERIAL:GLAZING, ...)
       - eplus_object_name (the intended name to create or update)
       - param_name (Thickness, Conductivity, R_value, U_value, roughness, etc.)
       - param_value
       - param_min, param_max

    Then we can group by (eplus_object_type, eplus_object_name) 
    to create or update that object in the IDF, assigning fields accordingly.
    
    Example usage:
       df_struct = pd.read_csv("structured_fenez_params.csv")
       apply_object_level_fenez(my_idf, df_struct)
    """

    group_cols = ["eplus_object_type", "eplus_object_name"]
    grouped = df_fenez.groupby(group_cols)

    for (obj_type, obj_name), group_df in grouped:
        print(f"[FENEZ] Handling {obj_type} => '{obj_name}' with {len(group_df)} rows.")

        # 1) Attempt to find or create the object in IDF
        obj_type_upper = obj_type.upper() if isinstance(obj_type, str) else None
        if not obj_type_upper or obj_type_upper not in idf.idfobjects:
            print(f"[FENEZ WARNING] IDF has no object type '{obj_type_upper}', skipping.")
            continue

        # search by Name
        existing_obj = [
            o for o in idf.idfobjects[obj_type_upper]
            if hasattr(o, "Name") and str(o.Name).upper() == str(obj_name).upper()
        ]
        if existing_obj:
            eplus_obj = existing_obj[0]
        else:
            # create new
            eplus_obj = idf.newidfobject(obj_type_upper)
            if hasattr(eplus_obj, "Name"):
                eplus_obj.Name = obj_name
            else:
                print(f"[FENEZ WARNING] {obj_type_upper} has no 'Name' field? object creation is partial.")
                # might continue or skip

        # 2) row by row => param_name => param_value
        for row in group_df.itertuples():
            p_name = row.param_name
            val    = row.param_value

            # Attempt float conversion if numeric
            try:
                val_float = float(val)
            except (ValueError, TypeError):
                val_float = None  # probably string

            # A few example mappings or direct sets:
            if p_name and isinstance(p_name, str):
                p_lower = p_name.lower()

                # handle certain known string fields
                if p_lower in ["roughness", "optical_data_type", "solar_diffusing"]:
                    if hasattr(eplus_obj, p_name):
                        setattr(eplus_obj, p_name, str(val))
                    else:
                        field_name = _match_field_name(eplus_obj, p_name)
                        if field_name:
                            setattr(eplus_obj, field_name, str(val))
                        else:
                            print(f"[FENEZ WARNING] No direct field match for param_name='{p_name}'. Skipping.")

                # handle certain known numeric fields
                elif p_lower in [
                    "thickness", "conductivity", "density", "specific_heat",
                    "thermal_resistance", "solar_transmittance", 
                    "front_solar_reflectance", "back_solar_reflectance",
                    "visible_transmittance", "front_visible_reflectance",
                    "back_visible_reflectance", "front_ir_emissivity",
                    "back_ir_emissivity", "dirt_correction_factor"
                ]:
                    field_name = _match_field_name(eplus_obj, p_name)
                    if field_name and val_float is not None:
                        setattr(eplus_obj, field_name, val_float)
                elif p_lower in ["r_value", "u_value"]:
                    # these are computed or not direct fields
                    # you'd have to recalc thickness or conduction
                    # skipping direct assignment
                    pass
                else:
                    # fallback attempt
                    field_name = _match_field_name(eplus_obj, p_name)
                    if field_name:
                        setattr(eplus_obj, field_name, val_float if val_float is not None else val)
                    else:
                        print(f"[FENEZ WARNING] No direct field match for param_name='{p_name}'. Skipping.")

        print(f"[FENEZ] Updated {obj_type} => '{obj_name}' with new fields.")


def _match_field_name(eplus_obj, param_name):
    """
    A small helper to guess the correct IDF field name from param_name 
    if there's a mismatch. If param_name exactly matches the IDF field, 
    you can skip this step. Otherwise, we do a dict-based approach 
    for typical window materials, etc.
    """

    map_dict = {
        "front_solar_reflectance": "Front_Side_Solar_Reflectance_at_Normal_Incidence",
        "back_solar_reflectance":  "Back_Side_Solar_Reflectance_at_Normal_Incidence",
        "front_visible_reflectance": "Front_Side_Visible_Reflectance_at_Normal_Incidence",
        "back_visible_reflectance":  "Back_Side_Visible_Reflectance_at_Normal_Incidence",
        "front_ir_emissivity": "Front_Side_Infrared_Hemispherical_Emissivity",
        "back_ir_emissivity":  "Back_Side_Infrared_Hemispherical_Emissivity",
        "solar_transmittance": "Solar_Transmittance_at_Normal_Incidence",
        "visible_transmittance": "Visible_Transmittance_at_Normal_Incidence",
        "dirt_correction_factor": "Dirt_Correction_Factor_for_Solar_and_Visible_Transmittance"
    }

    p_lower = param_name.lower()
    if p_lower in map_dict:
        candidate_field = map_dict[p_lower]
        if hasattr(eplus_obj, candidate_field):
            return candidate_field
        else:
            return None

    # direct match
    if hasattr(eplus_obj, param_name):
        return param_name

    return None


##############################################################################
# 3) CREATE FENESTRATION SCENARIOS (NEW)
##############################################################################
def create_fenez_scenarios(
    df_struct_fenez,
    building_id,
    num_scenarios=5,
    picking_method="random_uniform",
    scenario_start_index=0,
    random_seed=42,
    scenario_csv_out=None
):
    """
    Generates a scenario-level DataFrame from a "structured" fenestration DataFrame.

    Arguments:
      df_struct_fenez: pd.DataFrame
        Expected to contain columns like:
          ['ogc_fid','sub_key','eplus_object_type','eplus_object_name',
           'param_name','param_value','param_min','param_max']
        Typically read from "structured_fenez_params.csv".

      building_id: int (or str)
        Which building's data to filter from df_struct_fenez (ogc_fid).

      num_scenarios: int
        How many scenario sets to generate.

      picking_method: str
        E.g. "random_uniform", "fixed", "some_other_method" ...
        Used to decide how param_value is recalculated.

      scenario_start_index: int
        If you already have scenario indexes used up, you can start from another offset.

      random_seed: int
        Seed for reproducible random picks.

      scenario_csv_out: str or None
        If not None, write the final DataFrame to this path as CSV.

    Returns:
      df_scenarios: pd.DataFrame
        Columns:
          scenario_index, ogc_fid, sub_key, eplus_object_type, eplus_object_name,
          param_name, param_value, param_min, param_max, picking_method

        This can be saved as "scenario_params_fenez.csv" or merged with other scenario param files.

    Example usage:
      df_struct = pd.read_csv("output/assigned/structured_fenez_params.csv")
      df_scen = create_fenez_scenarios(
          df_struct_fenez=df_struct,
          building_id=4136730,
          num_scenarios=3,
          picking_method="random_uniform",
          scenario_csv_out="output/scenarios/scenario_params_fenez.csv"
      )
      # => returns a DF and writes it to scenario_params_fenez.csv
    """
    if random_seed is not None:
        random.seed(random_seed)

    # 1) Filter the structured data for this building
    df_bldg = df_struct_fenez.loc[df_struct_fenez["ogc_fid"] == building_id].copy()
    if df_bldg.empty:
        print(f"[create_fenez_scenarios] No fenestration data found for ogc_fid={building_id}.")
        return pd.DataFrame()

    scenario_rows = []

    # 2) Loop over the number of scenarios
    for i in range(num_scenarios):
        scenario_i = scenario_start_index + i

        # 3) For each param in df_bldg, pick a new param_value
        for row in df_bldg.itertuples():
            sub_key = row.sub_key
            eplus_type = row.eplus_object_type
            eplus_name = row.eplus_object_name
            param_name = row.param_name

            # base value, min, max
            base_val = row.param_value
            p_min = row.param_min
            p_max = row.param_max

            # compute new value
            new_val = base_val  # default fallback

            if picking_method == "random_uniform":
                if p_min is not None and p_max is not None:
                    try:
                        # Attempt float cast
                        fmin = float(p_min)
                        fmax = float(p_max)
                        # pick random
                        # if min == max, it stays the same
                        if fmax >= fmin:
                            new_val = random.uniform(fmin, fmax)
                        else:
                            # fallback if min>max
                            new_val = base_val
                    except:
                        pass
                else:
                    # no range => keep base_val
                    pass

            elif picking_method == "fixed":
                # keep base_val as is, or override with your own logic
                new_val = base_val

            else:
                # if you have some other picking method
                new_val = base_val

            row_dict = {
                "scenario_index": scenario_i,
                "ogc_fid": building_id,
                "sub_key": sub_key,
                "eplus_object_type": eplus_type,
                "eplus_object_name": eplus_name,
                "param_name": param_name,
                "param_value": new_val,
                "param_min": p_min,
                "param_max": p_max,
                "picking_method": picking_method
            }
            scenario_rows.append(row_dict)

    # 4) Convert to DataFrame
    df_scenarios = pd.DataFrame(scenario_rows)

    # 5) Optionally write CSV
    if scenario_csv_out:
        df_scenarios.to_csv(scenario_csv_out, index=False)
        print(f"[create_fenez_scenarios] Wrote scenario params to {scenario_csv_out}")

    return df_scenarios
