# fenez_config_manager.py

import copy
import pandas as pd

# We assume you have the Excel override function in dict_override_excel:
# from .dict_override_excel import override_dictionaries_from_excel
# Adjust the import path as needed:
from idf_objects.fenez.dict_override_excel import override_dictionaries_from_excel


def build_fenez_config(
    base_res_data: dict,
    base_nonres_data: dict,
    excel_path: str = None,
    do_excel_override: bool = False,
    user_fenez_overrides = None
):
    """
    Builds the final fenestration configuration (for residential & non-res)
    by merging:

      1) base_res_data, base_nonres_data (the "default" dictionaries).
      2) Excel overrides (if do_excel_override=True and excel_path provided).
      3) User overrides from fenestration.json (a list of rules).

    Returns (final_res_data, final_nonres_data).
    
    Parameters
    ----------
    base_res_data : dict
        Your default dictionary for residential fenestration/materials.
    base_nonres_data : dict
        Your default dictionary for non-res fenestration/materials.
    excel_path : str
        Path to the Excel file with fenestration overrides (if any).
    do_excel_override : bool
        If True, apply the Excel overrides first.
    user_fenez_overrides : list or None
        A list of overrides from fenestration.json, e.g.:
        [
          {
            "building_id": 4136730,
            "building_function": "residential",
            "age_range": "1992 - 2005",
            "scenario": "scenario1",
            "param_name": "wwr",
            "min_val": 0.25,
            "max_val": 0.30
          },
          ...
        ]

    """
    # 1) Copy the base dictionaries so we don't mutate originals
    final_res_data = copy.deepcopy(base_res_data)
    final_nonres_data = copy.deepcopy(base_nonres_data)

    # 2) If requested, apply Excel overrides
    if do_excel_override and excel_path and len(excel_path.strip()) > 0:
        final_res_data, final_nonres_data = override_dictionaries_from_excel(
            excel_path=excel_path,
            default_res_data=final_res_data,
            default_nonres_data=final_nonres_data,
            default_roughness="MediumRough",
            fallback_wwr_range=(0.2, 0.3)
        )

    # 3) Then apply user JSON overrides (if any)
    if user_fenez_overrides:
        final_res_data, final_nonres_data = apply_user_fenez_overrides(
            final_res_data,
            final_nonres_data,
            user_fenez_overrides
        )

    return final_res_data, final_nonres_data


def apply_user_fenez_overrides(final_res_data, final_nonres_data, user_fenez_list):
    """
    Applies user-defined overrides from fenestration.json to the in-memory dictionaries.
    Each item in `user_fenez_list` might look like:

      {
        "building_id": 4136730,
        "building_function": "residential",
        "age_range": "1992 - 2005",
        "scenario": "scenario1",
        "calibration_stage": "pre_calibration",  # optional
        "param_name": "wwr",
        "fixed_value": 0.28
      }

    or:

      {
        "building_function": "non_residential",
        "age_range": "2015 and later",
        "scenario": "scenario1",
        "param_name": "roof_R_value",
        "min_val": 3.0,
        "max_val": 3.5
      }

    This function interprets these overrides and modifies 
    final_res_data or final_nonres_data accordingly.
    """
    for rule in user_fenez_list:
        bfunc   = str(rule.get("building_function", "")).lower()
        btype   = str(rule.get("building_type", ""))  # might come from "residential_type" if known
        age_rng = str(rule.get("age_range", "2015 and later"))
        scen    = str(rule.get("scenario", "scenario1"))
        stage   = str(rule.get("calibration_stage", "pre_calibration"))
        p_name  = rule.get("param_name", "").lower()

        # Decide which dict to modify
        if bfunc == "residential":
            data_dict = final_res_data
        else:
            data_dict = final_nonres_data

        dict_key = (btype, age_rng, scen, stage)
        if dict_key not in data_dict:
            # If the combination doesn't exist, create an entry 
            data_dict[dict_key] = {
                "roughness": "MediumRough",
                "wwr_range": (0.2, 0.3)
                # You can add more defaults or handle them carefully
            }

        # Extract overrides
        fixed_val = rule.get("fixed_value")
        min_val   = rule.get("min_val")
        max_val   = rule.get("max_val")

        # Now interpret param_name
        if p_name == "wwr":
            # If there's a fixed_value, store range=(fixed_val,fixed_val).
            if fixed_val is not None:
                data_dict[dict_key]["wwr_range"] = (fixed_val, fixed_val)
            elif min_val is not None and max_val is not None:
                data_dict[dict_key]["wwr_range"] = (min_val, max_val)

        elif p_name == "roof_r_value":
            # For example, override "flat_roof" => "R_value_range"
            # If 'flat_roof' doesn't exist, create it:
            if "flat_roof" not in data_dict[dict_key]:
                data_dict[dict_key]["flat_roof"] = {}
            if fixed_val is not None:
                data_dict[dict_key]["flat_roof"]["R_value_range"] = (fixed_val, fixed_val)
            elif min_val is not None and max_val is not None:
                data_dict[dict_key]["flat_roof"]["R_value_range"] = (min_val, max_val)

        # Possibly handle other param_name items similarly, e.g. "wall_u_value", "door_u_value", etc.
        # Example:
        # elif p_name == "wall_u_value":
        #     if "exterior_wall" not in data_dict[dict_key]:
        #         data_dict[dict_key]["exterior_wall"] = {}
        #     if fixed_val is not None:
        #         data_dict[dict_key]["exterior_wall"]["U_value_range"] = (fixed_val, fixed_val)
        #     elif min_val is not None and max_val is not None:
        #         data_dict[dict_key]["exterior_wall"]["U_value_range"] = (min_val, max_val)

        # If your override logic is more detailed (like referencing building_id),
        # you might store building_id-specific details. But typically, 
        # building_id is only relevant if you do building-level picks.

    return final_res_data, final_nonres_data
