"""
dict_override_excel.py

Used by fenez_config_manager.py (and others) to apply Excel-based overrides
to your base fenestration/material dictionaries.

The Excel file is expected to have columns like:

  building_function:        e.g. "residential" or "non_residential"
  building_type:            e.g. "Two-and-a-half-story House"
  year_range:               e.g. "1992 - 2005"
  scenario:                 e.g. "scenario1"
  calibration_stage:        e.g. "pre_calibration"
  element:                  e.g. "exterior_wall", "windows", "doors", "flat_roof"
  area_m2:                  numeric
  R_value_min, R_value_max: numeric
  U_value_min, U_value_max: numeric
  roughness:                string or blank
  material_opaque_lookup:   optional, e.g. "Concrete_200mm"
  material_window_lookup:   optional, e.g. "Glazing_Clear_3mm"
  min_wwr, max_wwr:         numeric (for top-level wwr_range override)

This file merges those Excel-based settings into your in-memory dictionaries
for residential and non_residential. The order of overrides is:

1) Start with your base dictionaries (res_data, nonres_data).
2) For each row in the Excel, find or create the (btype, year_range, scenario, stage) key.
3) Override or fill in fields like "wwr_range", R_value_range, U_value_range, etc.

Returns new copies (deep copies) of the dictionaries with overrides applied.
"""

import pandas as pd
import copy

def override_dictionaries_from_excel(
    excel_path: str,
    default_res_data: dict,
    default_nonres_data: dict,
    default_roughness="MediumRough",
    fallback_wwr_range=(0.2, 0.3)
):
    """
    Reads an Excel file containing envelope/fenestration data and uses it to override
    the default dictionaries for residential and non_residential materials.

    The Excel must contain columns:

      building_function, building_type, year_range, scenario, calibration_stage,
      element, area_m2, R_value_min, R_value_max, U_value_min, U_value_max,
      roughness, material_opaque_lookup, material_window_lookup,
      min_wwr, max_wwr

    Parameters
    ----------
    excel_path : str
        Path to the .xlsx file with columns described above.
    default_res_data : dict
        The default residential fenestration/material dictionary.
    default_nonres_data : dict
        The default non-residential fenestration/material dictionary.
    default_roughness : str
        A fallback roughness if none is provided or if the Excel cell is blank.
    fallback_wwr_range : tuple
        A default (min_wwr, max_wwr) if none is found.

    Returns
    -------
    new_res_data : dict
    new_nonres_data : dict
        Updated copies of the input dictionaries with Excel overrides applied.
    """
    # Make deep copies so we don't mutate the originals
    new_res_data = copy.deepcopy(default_res_data)
    new_nonres_data = copy.deepcopy(default_nonres_data)

    # Read the Excel data into a DataFrame
    df = pd.read_excel(excel_path)

    # Check for required columns
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

    # Iterate over each row and override accordingly
    for _, row in df.iterrows():
        bfunc = str(row["building_function"]).strip().lower()   # "residential" or "non_residential"
        btype = str(row["building_type"]).strip()
        yrange= str(row["year_range"]).strip()
        scen  = str(row["scenario"]).strip()
        stage = str(row["calibration_stage"]).strip()
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
                "wwr_range": fallback_wwr_range,
            }
        data_entry = current_dict[dict_key]

        # Possibly override top-level roughness
        rgh_val = str(row["roughness"]).strip()
        if rgh_val.lower() not in ["nan", ""]:
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

        # area_m2
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

        # material_opaque_lookup
        opq_lookup = row["material_opaque_lookup"]
        if pd.notna(opq_lookup):
            elem_dict["material_opaque_lookup"] = str(opq_lookup).strip()

        # material_window_lookup
        win_lookup = row["material_window_lookup"]
        if pd.notna(win_lookup):
            elem_dict["material_window_lookup"] = str(win_lookup).strip()

    return new_res_data, new_nonres_data
