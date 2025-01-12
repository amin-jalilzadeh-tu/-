# fenez/dict_override_excel.py

import pandas as pd
import copy
import math

def override_dictionaries_from_excel(
    excel_path,
    default_res_data,
    default_nonres_data,
    default_roughness="MediumRough",
    fallback_wwr_range=(0.2, 0.3)
):
    """
    Reads an Excel file containing envelope data (including min_wwr, max_wwr,
    R_value_min, R_value_max, etc.) and uses it to override or extend
    the default dictionaries for residential and non_residential materials.

    The Excel must contain columns like:
      - building_function : 'residential' or 'non_residential'
      - building_type
      - year_range
      - scenario
      - calibration_stage
      - element : e.g. 'exterior_wall', 'windows', 'doors', etc.
      - area_m2
      - R_value_min, R_value_max
      - U_value_min, U_value_max
      - roughness
      - material_opaque_lookup
      - material_window_lookup
      - min_wwr, max_wwr

    For each row, we locate or create the dictionary entry in either:
      default_res_data[(btype, yrange, scen, stage)] or
      default_nonres_data[(btype, yrange, scen, stage)]

    Then we override sub-keys like:
      data_entry["wwr_range"] = (min_wwr, max_wwr)
      data_entry[element]["R_value_range"] = (R_value_min, R_value_max)
      data_entry[element]["U_value_range"] = (U_value_min, U_value_max)

    Returns
    -------
    new_res_data : dict
    new_nonres_data : dict

    Example usage:
      new_res, new_nonres = override_dictionaries_from_excel(
          "envelop.xlsx", residential_materials_data, non_residential_materials_data
      )
    """
    # Make deep copies so we don't mutate originals
    new_res_data = copy.deepcopy(default_res_data)
    new_nonres_data = copy.deepcopy(default_nonres_data)

    # Load Excel
    df = pd.read_excel(excel_path)

    required_cols = [
        "building_function",
        "building_type",
        "year_range",
        "scenario",
        "calibration_stage",
        "element",
        "area_m2",
        "R_value_min",
        "R_value_max",
        "U_value_min",
        "U_value_max",
        "roughness",
        "material_opaque_lookup",
        "material_window_lookup",
        "min_wwr",
        "max_wwr"
    ]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Excel file is missing required columns: {missing_cols}")

    for _, row in df.iterrows():
        bfunc = str(row["building_function"]).strip().lower()  # 'residential' or 'non_residential'
        btype = str(row["building_type"]).strip()
        yrange = str(row["year_range"]).strip()
        scen   = str(row["scenario"]).strip()
        stage  = str(row["calibration_stage"]).strip()
        elem_name = str(row["element"]).strip()

        # Decide which dictionary to modify
        if bfunc == "residential":
            current_dict = new_res_data
        else:
            current_dict = new_nonres_data

        dict_key = (btype, yrange, scen, stage)

        # Create or fetch the entry
        if dict_key not in current_dict:
            current_dict[dict_key] = {
                "roughness": default_roughness,
                "wwr_range": fallback_wwr_range
            }
        data_entry = current_dict[dict_key]

        # Possibly override top-level roughness
        rgh_val = str(row["roughness"]).strip()
        if rgh_val.lower() != "nan":
            data_entry["roughness"] = rgh_val

        # Possibly override top-level wwr_range
        min_wwr = row["min_wwr"]
        max_wwr = row["max_wwr"]
        if pd.notna(min_wwr) and pd.notna(max_wwr):
            data_entry["wwr_range"] = (float(min_wwr), float(max_wwr))

        # Now handle the sub-element (doors, windows, exterior_wall, etc.)
        if elem_name not in data_entry:
            data_entry[elem_name] = {}

        elem_dict = data_entry[elem_name]

        # area
        if pd.notna(row["area_m2"]):
            elem_dict["area_m2"] = float(row["area_m2"])

        # R_value_range
        r_min = row["R_value_min"]
        r_max = row["R_value_max"]
        if pd.notna(r_min) and pd.notna(r_max):
            elem_dict["R_value_range"] = (float(r_min), float(r_max))

        # U_value_range
        u_min = row["U_value_min"]
        u_max = row["U_value_max"]
        if pd.notna(u_min) and pd.notna(u_max):
            elem_dict["U_value_range"] = (float(u_min), float(u_max))

        # Overwrite or store roughness for that element if needed
        # (Often we keep the top-level roughness, but you could do:
        # elem_dict["roughness"] = data_entry["roughness"])

        # material_opaque_lookup
        opq_lookup = row["material_opaque_lookup"]
        if pd.notna(opq_lookup):
            elem_dict["material_opaque_lookup"] = str(opq_lookup).strip()

        # material_window_lookup
        win_lookup = row["material_window_lookup"]
        if pd.notna(win_lookup):
            elem_dict["material_window_lookup"] = str(win_lookup).strip()

    return new_res_data, new_nonres_data
