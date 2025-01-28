"""
vent_functions.py

Provides:
  1) create_vent_scenarios(...) 
     - Generates scenario-level data for both building-level and zone-level vent parameters,
       possibly incorporating min/max ranges for infiltration_base, infiltration_flow_m3_s, etc.
     - Writes or returns a single scenario DataFrame (or multiple, if you prefer them separate).

  2) apply_building_level_vent(idf, vent_params)
     - Applies building-level infiltration/vent parameters to the IDF.

  3) apply_zone_level_vent(idf, df_zone_scen)
     - Applies zone-level infiltration/vent parameters to the IDF by creating or updating
       ZoneInfiltration:DesignFlowRate and ZoneVentilation:DesignFlowRate objects.
"""

import os
import random
import pandas as pd


# ---------------------------------------------------------------------------
# 1) CREATE VENTILATION SCENARIOS
# ---------------------------------------------------------------------------
def create_vent_scenarios(
    df_building,
    df_zones,
    building_id,
    num_scenarios=5,
    picking_method="random_uniform",
    random_seed=42,
    scenario_csv_out=None
):
    """
    Generate a scenario-level DataFrame that combines building-level vent parameters
    (from df_building) and zone-level vent parameters (from df_zones), including
    param_min/param_max if present. Then optionally randomizes or adjusts them
    for each scenario.

    Args:
      df_building (pd.DataFrame): building-level vent data, typically from
        "assigned_vent_building.csv" with columns like:
         - ogc_fid, param_name, param_value
         - param_name might also have a "_range" companion row with min/max in parentheses
      df_zones (pd.DataFrame): zone-level vent data from
        "assigned_vent_zones.csv" with columns like:
         - ogc_fid, zone_name, param_name, param_value
      building_id: int or str, the building ID to filter on
      num_scenarios: int, how many scenario sets to create
      picking_method: str, e.g. "random_uniform", "fixed", etc.
      random_seed: int, for reproducible random picks
      scenario_csv_out: str or None, if not None we write final DataFrame to CSV

    Returns:
      df_scen (pd.DataFrame): A "long" DataFrame with columns like:
        [scenario_index, ogc_fid, zone_name, param_name, param_value,
         param_min, param_max, picking_method, ...]
      - zone_name may be empty/None for building-level params
      - param_min/param_max extracted from e.g. infiltration_base_range
      - param_value potentially randomized if picking_method == "random_uniform"
    """
    if random_seed is not None:
        random.seed(random_seed)

    # 1) Filter for this building
    df_bldg = df_building[df_building["ogc_fid"] == building_id].copy()
    df_zone = df_zones[df_zones["ogc_fid"] == building_id].copy()

    if df_bldg.empty and df_zone.empty:
        print(f"[create_vent_scenarios] No ventilation data found for ogc_fid={building_id}.")
        return pd.DataFrame()

    # 2) Build building param list, with param_min/param_max if they appear in "xxx_range" rows
    bldg_params = parse_building_vent_params(df_bldg)

    # 3) Build zone param list
    zone_params = parse_zone_vent_params(df_zone)

    scenario_rows = []

    # 4) For each scenario, we pick new param_value for each building-level param
    for scenario_i in range(num_scenarios):
        # A) Building-level
        for p in bldg_params:
            p_name = p["param_name"]
            p_val  = p["param_value"]  # base
            p_min  = p["param_min"]
            p_max  = p["param_max"]

            new_val = pick_value(p_val, p_min, p_max, picking_method)
            scenario_rows.append({
                "scenario_index": scenario_i,
                "ogc_fid": building_id,
                "zone_name": None,  # building-level param
                "param_name": p_name,
                "param_value": new_val,
                "param_min": p_min,
                "param_max": p_max,
                "picking_method": picking_method
            })

        # B) Zone-level
        for z in zone_params:
            z_name  = z["zone_name"]
            p_name  = z["param_name"]
            p_val   = z["param_value"]
            p_min   = z["param_min"]
            p_max   = z["param_max"]

            new_val = pick_value(p_val, p_min, p_max, picking_method)
            scenario_rows.append({
                "scenario_index": scenario_i,
                "ogc_fid": building_id,
                "zone_name": z_name,
                "param_name": p_name,
                "param_value": new_val,
                "param_min": p_min,
                "param_max": p_max,
                "picking_method": picking_method
            })

    # 5) Convert to DataFrame
    df_scen = pd.DataFrame(scenario_rows)

    # 6) Optionally write to CSV
    if scenario_csv_out:
        os.makedirs(os.path.dirname(scenario_csv_out), exist_ok=True)
        df_scen.to_csv(scenario_csv_out, index=False)
        print(f"[create_vent_scenarios] Wrote scenario vent params => {scenario_csv_out}")

    return df_scen


def parse_building_vent_params(df_bldg):
    """
    Helper to parse building-level vent parameters from
    assigned_vent_building.csv into a list of dicts with
      [param_name, param_value, param_min, param_max]

    - If param_name == "infiltration_base_range" => store param_min/param_max from the tuple
      matched with param_name="infiltration_base".
    - Similarly for "year_factor_range", "fan_pressure_range", etc.
    """
    # We read rows like:
    #   infiltration_base, 100.3639
    #   infiltration_base_range, (100.3, 100.4)
    # We'll store them in a dictionary keyed by the "base param"
    param_map = {}  # e.g. "infiltration_base" => {value:..., min:..., max:...}

    for row in df_bldg.itertuples():
        name = row.param_name
        val  = row.param_value

        # e.g. name="infiltration_base_range"
        if name.endswith("_range"):
            base_name = name.replace("_range", "")
            if base_name not in param_map:
                param_map[base_name] = {"param_value": None, "param_min": None, "param_max": None}

            # parse (min,max)
            t = parse_tuple(val)
            if t and len(t) == 2:
                param_map[base_name]["param_min"] = t[0]
                param_map[base_name]["param_max"] = t[1]
        else:
            # normal param
            if name not in param_map:
                param_map[name] = {"param_value": None, "param_min": None, "param_max": None}
            param_map[name]["param_value"] = val

    # Now produce a list of dict
    result = []
    for p_name, dct in param_map.items():
        result.append({
            "param_name":  p_name,
            "param_value": dct["param_value"],
            "param_min":   dct["param_min"],
            "param_max":   dct["param_max"]
        })
    return result


def parse_zone_vent_params(df_zone):
    """
    Helper to parse zone-level vent params from assigned_vent_zones.csv
    into a list of dicts with zone_name, param_name, param_value, param_min, param_max.

    Typically, assigned_vent_zones doesn't store param_min/param_max,
    so we might keep them as None. But if your code logs them, parse them similarly.
    """
    results = []
    # e.g. row: zone_name="Zone1_FrontPerimeter", param_name="infiltration_flow_m3_s", param_value=0.255
    for row in df_zone.itertuples():
        zname = row.zone_name
        pname = row.param_name
        val   = row.param_value

        # If you store param ranges in zone CSV, parse them similarly to parse_tuple
        # For now, we assume no range => None
        results.append({
            "zone_name": zname,
            "param_name": pname,
            "param_value": val,
            "param_min": None,
            "param_max": None
        })
    return results


def parse_tuple(val):
    """
    If val is like "(100.3, 100.4)", parse to (100.3, 100.4). Otherwise None.
    """
    if not isinstance(val, str):
        return None
    val_str = val.strip()
    if not (val_str.startswith("(") and val_str.endswith(")")):
        return None
    try:
        # e.g. ast.literal_eval could do this too, but let's do a simple approach:
        inner = val_str[1:-1]  # remove parens
        parts = inner.split(",")
        if len(parts) != 2:
            return None
        p1 = float(parts[0])
        p2 = float(parts[1])
        return (p1, p2)
    except:
        return None


def pick_value(base_val, p_min, p_max, picking_method):
    """
    Given a base_val (float or str), optional p_min/p_max, and a method,
    return a new value. Example:
      - If picking_method == "random_uniform" and p_min/p_max are not None,
        pick random in [p_min, p_max].
      - Else keep base_val as is.

    Adjust as needed for more complex logic (like scale factors).
    """
    # Attempt float conversion
    try:
        base_f = float(base_val)
    except:
        base_f = None

    if picking_method == "random_uniform" and p_min is not None and p_max is not None:
        try:
            fmin = float(p_min)
            fmax = float(p_max)
            if fmax >= fmin:
                return random.uniform(fmin, fmax)
        except:
            pass
        # fallback => base_val
        return base_val

    # if picking_method == "fixed", or no range, just return base_val
    return base_val


# ---------------------------------------------------------------------------
# 2) APPLY BUILDING-LEVEL VENT
# ---------------------------------------------------------------------------
def apply_building_level_vent(idf, vent_params):
    """
    Applies building-level infiltration/vent parameters (like infiltration_base,
    infiltration_total_m3_s, schedules, etc.) to the IDF in a "coarse" manner.

    Example usage:
        vent_params = {
          "infiltration_base": 0.5,
          "ventilation_total_m3_s": 0.01,
          "infiltration_schedule_name": "AlwaysOnSched",
          ...
        }
        apply_building_level_vent(my_idf, vent_params)
    """
    # This is a placeholder approach, as building-level infiltration often
    # needs to be distributed to zones. But let's assume you have a
    # "global infiltration" or "HVAC system infiltration" object in IDF
    # that you can set.

    infiltration_base = vent_params.get("infiltration_base")
    infiltration_sched = vent_params.get("infiltration_schedule_name")
    # etc.

    print(f"[VENT] Applying building-level infiltration_base={infiltration_base}, schedule={infiltration_sched}")

    # If you have a top-level infiltration object or design object, you can find it:
    # e.g. "ZoneInfiltration:DesignFlowRate" object named "GlobalInfil" or similar
    # This is just a pseudo-illustration:
    # infiltration_obj = find_or_create_infiltration_object(idf, name="GlobalInfil")
    # infiltration_obj.Design_Flow_Rate = infiltration_base
    # infiltration_obj.Schedule_Name = infiltration_sched

    # If you want to store infiltration_total_m3_s, etc. do similarly
    # ...
    pass


# ---------------------------------------------------------------------------
# 3) APPLY ZONE-LEVEL VENT
# ---------------------------------------------------------------------------
def apply_zone_level_vent(idf, df_zone_scen):
    """
    Applies zone-level infiltration/vent parameters to each zone. The DataFrame
    is expected to have columns:
       [zone_name, param_name, param_value, ...]
    derived from scenario-based picks or from assigned_vent_zones.csv.

    Each zone might have infiltration_object_name, infiltration_flow_m3_s,
    infiltration_schedule_name, ventilation_object_name, ventilation_flow_m3_s,
    ventilation_schedule_name, etc.

    We'll group by zone_name, create or update the infiltration/vent objects
    in IDF.
    """
    # group by zone_name
    grouped = df_zone_scen.groupby("zone_name")

    for z_name, z_df in grouped:
        print(f"[VENT] => Zone={z_name}, {len(z_df)} param rows")

        # We can parse infiltrationX / ventilationX from param_name => param_value
        # A simple approach is to build a dict
        z_params = {}
        for row in z_df.itertuples():
            pname = row.param_name
            pval  = row.param_value
            z_params[pname] = pval

        # infiltration
        infil_obj_name  = z_params.get("infiltration_object_name")
        infil_obj_type  = z_params.get("infiltration_object_type", "ZONEINFILTRATION:DESIGNFLOWRATE")
        infil_flow      = z_params.get("infiltration_flow_m3_s", 0.0)
        infil_schedule  = z_params.get("infiltration_schedule_name", "AlwaysOnSched")

        # find or create infiltration object
        if infil_obj_name:
            infil_obj = find_or_create_object(idf, infil_obj_type, infil_obj_name)
            # set infiltration fields (some fields vary by object type)
            if hasattr(infil_obj, "Name"):
                infil_obj.Name = infil_obj_name
            if hasattr(infil_obj, "Zone_or_ZoneList_Name"):
                infil_obj.Zone_or_ZoneList_Name = z_name
            if hasattr(infil_obj, "Design_Flow_Rate"):
                try:
                    infil_obj.Design_Flow_Rate = float(infil_flow)
                except:
                    pass
            if hasattr(infil_obj, "Schedule_Name"):
                infil_obj.Schedule_Name = infil_schedule

        # ventilation
        vent_obj_name   = z_params.get("ventilation_object_name")
        vent_obj_type   = z_params.get("ventilation_object_type", "ZONEVENTILATION:DESIGNFLOWRATE")
        vent_flow       = z_params.get("ventilation_flow_m3_s", 0.0)
        vent_schedule   = z_params.get("ventilation_schedule_name", "AlwaysOnSched")

        if vent_obj_name:
            vent_obj = find_or_create_object(idf, vent_obj_type, vent_obj_name)
            if hasattr(vent_obj, "Name"):
                vent_obj.Name = vent_obj_name
            if hasattr(vent_obj, "Zone_or_ZoneList_Name"):
                vent_obj.Zone_or_ZoneList_Name = z_name
            if hasattr(vent_obj, "Design_Flow_Rate"):
                try:
                    vent_obj.Design_Flow_Rate = float(vent_flow)
                except:
                    pass
            if hasattr(vent_obj, "Schedule_Name"):
                vent_obj.Schedule_Name = vent_schedule


def find_or_create_object(idf, obj_type_upper, obj_name):
    """
    Utility to find an existing object in IDF by type & name, or create a new one.
    e.g. find_or_create_object(idf, "ZONEINFILTRATION:DESIGNFLOWRATE", "Infil_Zone1")
    """
    if not obj_type_upper:
        return None
    if obj_type_upper not in idf.idfobjects:
        # If IDF doesn't have that object class, attempt creation
        new_obj = idf.newidfobject(obj_type_upper)
        return new_obj

    # try to find by name
    existing = [
        o for o in idf.idfobjects[obj_type_upper]
        if hasattr(o, "Name") and str(o.Name) == str(obj_name)
    ]
    if existing:
        return existing[0]
    else:
        # create new
        new_obj = idf.newidfobject(obj_type_upper)
        return new_obj
