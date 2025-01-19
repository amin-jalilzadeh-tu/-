# common_utils.py

import os
import random
import pandas as pd

# If using Eppy:
from eppy.modeleditor import IDF
# If using Geomeppy, comment out the above and uncomment below:
# from geomeppy import IDF as GeomIDF
# GeomIDF.setiddname("path/to/Energy+.idd")


###############################################################################
# 1) Reading "assigned" CSVs
###############################################################################

def load_assigned_csv(csv_path):
    """
    Loads a generic CSV file containing assigned parameters for a building or zone.
    For example:
      D:/Documents/E_Plus_2030_py/output/assigned/assigned_dhw_params.csv
      D:/Documents/E_Plus_2030_py/output/assigned/assigned_hvac_building.csv
      etc.

    Returns:
      A Pandas DataFrame with the file contents.
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Cannot find CSV at: {csv_path}")
    df = pd.read_csv(csv_path)
    return df


def filter_for_building(df_main, df_zone=None, building_id=None):
    """
    If 'df_zone' is provided, filters both dataframes by ogc_fid == building_id.
    If building_id is None, returns df_main (and df_zone) unfiltered.

    This is useful if you have a building-level CSV and a zone-level CSV
    and want to isolate data for a particular ogc_fid.
    """
    if building_id is not None:
        df_main_sub = df_main[df_main["ogc_fid"] == building_id].copy()
        if df_zone is not None:
            df_zone_sub = df_zone[df_zone["ogc_fid"] == building_id].copy()
        else:
            df_zone_sub = None
    else:
        df_main_sub = df_main.copy()
        df_zone_sub = df_zone.copy() if df_zone is not None else None

    return df_main_sub, df_zone_sub


###############################################################################
# 2) Helpers for Generating Scenario Parameter Sets
###############################################################################

def to_float_or_none(x):
    """
    Attempts to convert x to float. If it fails (or is NaN), returns None.
    """
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def pick_value_in_range(base_val, param_min, param_max,
                        method="random_uniform", scale_factor=0.5):
    """
    Picks a new value given:
      - base_val: original numeric value (fallback if range is invalid)
      - param_min, param_max: numeric range
      - method: 
         "random_uniform" => uniform in [param_min, param_max]
         "scale_around_base" => base_val * random(1 - scale_factor, 1 + scale_factor)
         "offset_half" => base_val +/- up to 50% of half the total range
      - scale_factor: used if method="scale_around_base"
    Returns a float. If range invalid, returns base_val.
    """
    base_val_f = to_float_or_none(base_val)
    if base_val_f is None:
        base_val_f = 0.0

    min_f = to_float_or_none(param_min)
    max_f = to_float_or_none(param_max)

    if method == "random_uniform":
        if min_f is not None and max_f is not None and min_f < max_f:
            return random.uniform(min_f, max_f)
        else:
            return base_val_f

    elif method == "scale_around_base":
        low_factor = 1.0 - scale_factor
        high_factor = 1.0 + scale_factor
        factor = random.uniform(low_factor, high_factor)
        return base_val_f * factor

    elif method == "offset_half":
        if min_f is not None and max_f is not None:
            half_span = (max_f - min_f) / 2.0 * 0.5
            offset = random.uniform(-half_span, half_span)
            return base_val_f + offset
        else:
            return base_val_f

    # Default => return base_val
    return base_val_f


def define_building_param_strategy(df_main_sub, picking_method="random_uniform",
                                   scale_factor=0.5):
    """
    Loops over rows in df_main_sub to build {param_name -> new_value}.
    For each row, we call pick_value_in_range(...) to generate a new numeric value.

    - Skips rows with param_name="schedule_details" or other obviously non-numeric fields.
    - You can adapt if you want to skip more.

    Returns: { param_name -> numeric_value }
    """
    final_param_dict = {}

    for idx, row in df_main_sub.iterrows():
        param_name = row.get("param_name", None)
        if not param_name:
            continue

        # Skip known non-numeric param names if needed
        if param_name.lower() == "schedule_details":
            continue

        base_val = row.get("param_value", None)
        p_min = row.get("param_min", None)
        p_max = row.get("param_max", None)

        new_val = pick_value_in_range(
            base_val=base_val,
            param_min=p_min,
            param_max=p_max,
            method=picking_method,
            scale_factor=scale_factor
        )
        final_param_dict[param_name] = new_val

    return final_param_dict


def generate_multiple_param_sets(df_main_sub, num_sets=5,
                                 picking_method="random_uniform",
                                 scale_factor=0.5):
    """
    Calls define_building_param_strategy(...) multiple times to create 
    'num_sets' scenario dicts, e.g. for random draws in [param_min, param_max].

    Returns: list of dicts => each dict is {param_name -> new_value}
    """
    all_scenarios = []
    for _ in range(num_sets):
        scenario = define_building_param_strategy(
            df_main_sub=df_main_sub,
            picking_method=picking_method,
            scale_factor=scale_factor
        )
        all_scenarios.append(scenario)
    return all_scenarios


def save_param_scenarios_to_csv(all_scenarios, building_id,
                                out_csv="scenario_params.csv"):
    """
    Writes each scenario's picks to CSV with columns:
      [scenario_index, ogc_fid, param_name, assigned_value]

    This is how we form the "scenario_index" concept so we can groupby in the future.
    """
    rows = []
    for i, scenario_dict in enumerate(all_scenarios):
        for p_name, val in scenario_dict.items():
            rows.append({
                "scenario_index": i,
                "ogc_fid": building_id,
                "param_name": p_name,
                "assigned_value": val
            })

    df_out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df_out.to_csv(out_csv, index=False)
    print(f"[INFO] Saved scenario picks => {out_csv}")


###############################################################################
# 3) IDF Load/Save
###############################################################################

def load_idf(base_idf_path, idd_path):
    """
    Loads an existing IDF file from disk. Adjust if using Geomeppy instead of Eppy.
    """
    if not os.path.isfile(idd_path):
        raise FileNotFoundError(f"IDD file not found at: {idd_path}")
    if not os.path.isfile(base_idf_path):
        raise FileNotFoundError(f"IDF file not found at: {base_idf_path}")

    # Eppy usage
    IDF.iddname = idd_path
    idf = IDF(base_idf_path)
    return idf


def save_idf(idf, out_path):
    """
    Saves the modified IDF to out_path, creating directories as needed.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    idf.saveas(out_path)
    print(f"[INFO] Saved modified IDF => {out_path}")


###############################################################################
# 4) Optional: Loading a "Scenario" CSV (already defined picks)
###############################################################################

def load_scenario_csv(scenario_csv):
    """
    Reads a CSV that presumably has columns:
      - scenario_index
      - ogc_fid
      - param_name
      - assigned_value
    or something similar.

    The caller can do: df.groupby("scenario_index") to iterate over scenarios.
    """
    if not os.path.isfile(scenario_csv):
        raise FileNotFoundError(f"Cannot find scenario CSV at: {scenario_csv}")
    df = pd.read_csv(scenario_csv)
    return df
