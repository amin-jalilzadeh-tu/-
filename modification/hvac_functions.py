"""
hvac_functions.py

Provides functions for:
  1) create_hvac_scenarios(...)
     - Generates scenario data (potentially random) for building-level and zone-level HVAC,
       merging assigned_hvac_building.csv and assigned_hvac_zones.csv.
  2) apply_building_level_hvac(...)
     - Updates building-wide HVAC schedules (heating/cooling setpoints) and
       Ideal Loads supply air temps.
  3) apply_zone_level_hvac(...)
     - For each zone, applies or creates zone-level HVAC objects (like IdealLoads),
       sets setpoint schedules or thermostats, etc.

In this revised version, `_modify_schedule_compact()` is updated to parse 
existing "Until: HH:MM, value" lines and only update the numeric portion, 
preserving the schedule's time blocks. 
"""

import os
import random
import pandas as pd

from eppy.modeleditor import IDF  # or adapt as needed


##############################################################################
# 1) CREATE HVAC SCENARIOS
##############################################################################
def create_hvac_scenarios(
    df_building,
    df_zones,
    building_id,
    num_scenarios=5,
    picking_method="random_uniform",
    random_seed=42,
    scenario_csv_out=None
):
    """
    Generates a scenario-level DataFrame for HVAC from two CSVs:
      - df_building => assigned_hvac_building.csv
      - df_zones    => assigned_hvac_zones.csv

    Each of these has columns like:
      df_building: [ogc_fid, param_name, param_value] plus any param_name_range rows
      df_zones:    [ogc_fid, zone_name, param_name, param_value]

    We parse param_min / param_max from "xxx_range" lines for building-level, then
    produce a "long" DataFrame with columns:
      [scenario_index, ogc_fid, zone_name, param_name, param_value, param_min, param_max, picking_method]

    Example:
      heating_day_setpoint = 10.64 (with range (10.0, 11.0))
      => param_value might be a random pick in [10.0, 11.0] if picking_method=="random_uniform".

    Finally, we optionally save to scenario_csv_out (e.g. "scenario_params_hvac.csv").

    Return:
      df_scen (pd.DataFrame)
    """
    if random_seed is not None:
        random.seed(random_seed)

    # 1) Filter for this building
    df_bldg = df_building[df_building["ogc_fid"] == building_id].copy()
    df_zone = df_zones[df_zones["ogc_fid"] == building_id].copy()

    if df_bldg.empty and df_zone.empty:
        print(f"[create_hvac_scenarios] No HVAC data found for ogc_fid={building_id}.")
        return pd.DataFrame()

    # 2) Parse building-level HVAC params (with param_min/param_max)
    bldg_params = parse_building_hvac_params(df_bldg)

    # 3) Parse zone-level HVAC params (generally no param_min/param_max)
    zone_params = parse_zone_hvac_params(df_zone)

    scenario_rows = []

    # 4) For each scenario, pick new param_value for each building-level param
    for scenario_i in range(num_scenarios):
        # (A) Building-level
        for p in bldg_params:
            p_name = p["param_name"]
            base_val = p["param_value"]
            p_min = p["param_min"]
            p_max = p["param_max"]

            new_val = pick_value(base_val, p_min, p_max, picking_method)

            scenario_rows.append({
                "scenario_index": scenario_i,
                "ogc_fid": building_id,
                "zone_name": None,  # building-level
                "param_name": p_name,
                "param_value": new_val,
                "param_min": p_min,
                "param_max": p_max,
                "picking_method": picking_method
            })

        # (B) zone-level
        for z in zone_params:
            z_name  = z["zone_name"]
            p_name  = z["param_name"]
            base_val = z["param_value"]
            new_val = pick_value(base_val, None, None, picking_method)

            scenario_rows.append({
                "scenario_index": scenario_i,
                "ogc_fid": building_id,
                "zone_name": z_name,
                "param_name": p_name,
                "param_value": new_val,
                "param_min": None,
                "param_max": None,
                "picking_method": picking_method
            })

    # 5) Convert to DataFrame
    df_scen = pd.DataFrame(scenario_rows)

    # 6) Optionally write to CSV
    if scenario_csv_out:
        os.makedirs(os.path.dirname(scenario_csv_out), exist_ok=True)
        df_scen.to_csv(scenario_csv_out, index=False)
        print(f"[create_hvac_scenarios] Wrote scenario HVAC params => {scenario_csv_out}")

    return df_scen


def parse_building_hvac_params(df_bldg):
    """
    Helper to parse building-level HVAC parameters from assigned_hvac_building.csv
    into a list of dict with:
      [
        {
          "param_name": "heating_day_setpoint",
          "param_value": 10.64,
          "param_min": 10.0,
          "param_max": 11.0
        }, ...
      ]
    If we see "heating_day_setpoint_range" => store param_min/param_max in the dict
    for "heating_day_setpoint", etc.
    """
    param_map = {}  # "heating_day_setpoint" => {value: X, min: Y, max: Z}

    for row in df_bldg.itertuples():
        name = row.param_name
        val  = row.param_value

        if name.endswith("_range"):
            base_name = name.replace("_range", "")
            if base_name not in param_map:
                param_map[base_name] = {"param_value": None, "param_min": None, "param_max": None}

            t = parse_tuple(val)
            if t and len(t) == 2:
                param_map[base_name]["param_min"] = t[0]
                param_map[base_name]["param_max"] = t[1]
        else:
            if name not in param_map:
                param_map[name] = {"param_value": None, "param_min": None, "param_max": None}
            param_map[name]["param_value"] = val

    # Convert to list
    result = []
    for p_name, dct in param_map.items():
        result.append({
            "param_name":  p_name,
            "param_value": dct["param_value"],
            "param_min":   dct["param_min"],
            "param_max":   dct["param_max"]
        })
    return result


def parse_zone_hvac_params(df_zone):
    """
    Helper for zone-level HVAC: typically no range columns, so param_min/param_max = None.
    Returns a list of dicts => 
      [
        {"zone_name": "Zone1", "param_name": "hvac_object_name", "param_value": "Zone1 Ideal Loads"},
        ...
      ]
    """
    results = []
    for row in df_zone.itertuples():
        zname = row.zone_name
        pname = row.param_name
        val   = row.param_value

        results.append({
            "zone_name": zname,
            "param_name": pname,
            "param_value": val
        })
    return results


def parse_tuple(val):
    """
    If val is like "(10.0, 11.0)", parse to (10.0, 11.0). Otherwise None.
    """
    if not isinstance(val, str):
        return None
    val_str = val.strip()
    if not (val_str.startswith("(") and val_str.endswith(")")):
        return None
    try:
        inner = val_str[1:-1]
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
    If picking_method=="random_uniform" and p_min/p_max are numeric,
    pick randomly in [p_min, p_max]. Otherwise keep base_val as is.
    """
    # Attempt float
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
        return base_val

    return base_val


##############################################################################
# 2) APPLY BUILDING-LEVEL HVAC
##############################################################################

def apply_building_level_hvac(idf, param_dict):
    """
    param_dict is a dictionary of building-level HVAC parameters, e.g.:
      {
        "heating_day_setpoint": 10.64,
        "heating_night_setpoint": 15.02,
        "cooling_day_setpoint": 25.6,
        "cooling_night_setpoint": 26.44,
        "max_heating_supply_air_temp": 52.36,
        "min_cooling_supply_air_temp": 13.35,
        ...
      }

    This function:
      1) Updates "ZONE HEATING SETPOINTS" schedule (if day/night keys exist).
      2) Updates "ZONE COOLING SETPOINTS" schedule (if day/night keys exist).
      3) For each ZONEHVAC:IDEALLOADSAIRSYSTEM, sets supply air temps if present.
    """

    # (1) Heating Setpoint Schedules
    if "heating_day_setpoint" in param_dict or "heating_night_setpoint" in param_dict:
        h_day = param_dict.get("heating_day_setpoint", 20.0)
        h_night = param_dict.get("heating_night_setpoint", 15.0)
        _modify_schedule_compact(
            idf,
            schedule_name="ZONE HEATING SETPOINTS",
            day_value=h_day,
            night_value=h_night,
            day_start="07:00",
            day_end="19:00"
        )

    # (2) Cooling Setpoint Schedules
    if "cooling_day_setpoint" in param_dict or "cooling_night_setpoint" in param_dict:
        c_day = param_dict.get("cooling_day_setpoint", 24.0)
        c_night = param_dict.get("cooling_night_setpoint", 27.0)
        _modify_schedule_compact(
            idf,
            schedule_name="ZONE COOLING SETPOINTS",
            day_value=c_day,
            night_value=c_night,
            day_start="07:00",
            day_end="19:00"
        )

    # (3) Ideal Loads Supply Temps
    max_heat = param_dict.get("max_heating_supply_air_temp", None)
    min_cool = param_dict.get("min_cooling_supply_air_temp", None)
    if (max_heat is not None) or (min_cool is not None):
        _set_ideal_loads_supply_temps_all_zones(
            idf,
            max_heating_temp=max_heat,
            min_cooling_temp=min_cool
        )


def _set_ideal_loads_supply_temps_all_zones(idf, max_heating_temp=None, min_cooling_temp=None):
    """
    Loops over all ZONEHVAC:IDEALLOADSAIRSYSTEM objects, sets:
      Maximum_Heating_Supply_Air_Temperature = max_heating_temp
      Minimum_Cooling_Supply_Air_Temperature = min_cooling_temp
    if provided.
    """
    if "ZONEHVAC:IDEALLOADSAIRSYSTEM" not in idf.idfobjects:
        return

    ideal_objs = idf.idfobjects["ZONEHVAC:IDEALLOADSAIRSYSTEM"]
    for ideal in ideal_objs:
        if max_heating_temp is not None:
            ideal.Maximum_Heating_Supply_Air_Temperature = max_heating_temp
        if min_cooling_temp is not None:
            ideal.Minimum_Cooling_Supply_Air_Temperature = min_cooling_temp

        print(f"[HVAC] Updated '{ideal.Name}' => MaxHeat={max_heating_temp}, MinCool={min_cooling_temp}")


##############################################################################
# PARTIAL SCHEDULE EDITING: UPDATED _modify_schedule_compact
##############################################################################

def parse_schedule_until_line(line_str: str):
    """
    Parses a single line like "Until: 07:00, 15.0".
    Returns (time_str, float_value).
    If parsing fails, returns (None, None).
    """
    if not isinstance(line_str, str):
        return (None, None)
    line_str = line_str.strip()
    if not line_str.lower().startswith("until:"):
        return (None, None)

    # Remove "Until:"
    try:
        remainder = line_str.split("Until:", 1)[1].strip()  # e.g. "07:00, 15.0"
        # Split on comma
        time_part, val_str = remainder.split(",", 1)
        time_str = time_part.strip()
        val_float = float(val_str.strip())
        return (time_str, val_float)
    except:
        return (None, None)


def _modify_schedule_compact(
    idf,
    schedule_name,
    day_value,
    night_value,
    day_start="07:00",
    day_end="19:00"
):
    """
    Partially modifies an existing SCHEDULE:COMPACT by parsing each 'Until:' field,
    preserving its time range, but swapping out the numeric value for day_value or
    night_value based on whether time < day_start, time < day_end, or beyond day_end.

    If the schedule does not exist, we log a warning and skip.

    NOTE: This is a simplistic approach to day vs. night assignment:
      - If the field's 'Until' time is < day_start => night_value
      - Else if < day_end => day_value
      - Else => night_value again

    That way we preserve however many time blocks the schedule had—only numeric values
    get replaced. If you want a different approach, adapt the logic below.
    """
    sched_obj = idf.getobject("SCHEDULE:COMPACT", schedule_name.upper())
    if not sched_obj:
        print(f"[WARN] schedule '{schedule_name}' not found; skipping.")
        return

    # We'll parse day_start/day_end into HH:MM integer comparisons for convenience
    def time_to_minutes(tstr):
        # "07:00" => 7*60 + 0 = 420
        parts = tstr.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m

    day_start_mins = time_to_minutes(day_start)
    day_end_mins   = time_to_minutes(day_end)

    # FieldValues is the raw list of all fields after the object name & type
    # Typically, Field_1 might be "Through: 12/31", Field_2 = "For: AllDays",
    # then subsequent fields are "Until: HH:MM, Value".
    for i in range(len(sched_obj.fieldvalues)):
        field_str = sched_obj.fieldvalues[i]

        # parse "Until:" lines
        time_str, old_val = parse_schedule_until_line(field_str)
        if time_str is None:
            # Not an "Until:" line or parse failed, skip
            continue

        # Convert time_str -> minutes
        mins = 9999
        try:
            mins = time_to_minutes(time_str)
        except:
            pass

        # Now pick day or night
        if mins < day_start_mins:
            new_val = night_value
        elif mins < day_end_mins:
            new_val = day_value
        else:
            new_val = night_value

        # Overwrite the field with the same time, new numeric
        sched_obj.fieldvalues[i] = f"Until: {time_str},{new_val:.2f}"

    print(f"[HVAC] Updated schedule '{schedule_name}' with day={day_value}, night={night_value}")


##############################################################################
# 3) APPLY ZONE-LEVEL HVAC
##############################################################################
def apply_zone_level_hvac(idf, df_zone_scen):
    """
    Accepts a DataFrame with columns [zone_name, param_name, param_value] 
    for each zone. E.g.:
      zone_name=Zone1_FrontPerimeter, param_name=hvac_object_name, 
        param_value=Zone1_FrontPerimeter Ideal Loads
      zone_name=Zone1_FrontPerimeter, param_name=heating_setpoint_schedule, 
        param_value=ZONE HEATING SETPOINTS
      ...

    Then you can create or update the zone's HVAC objects accordingly.
    """

    grouped = df_zone_scen.groupby("zone_name")

    for z_name, z_df in grouped:
        print(f"[HVAC] => Zone={z_name}, {len(z_df)} param rows")

        zone_params = {}
        for row in z_df.itertuples():
            pname = row.param_name
            pval  = row.param_value
            zone_params[pname] = pval

        hvac_obj_name  = zone_params.get("hvac_object_name")
        hvac_obj_type  = zone_params.get("hvac_object_type", "ZONEHVAC:IDEALLOADSAIRSYSTEM")

        # Example for schedules:
        heating_sched  = zone_params.get("heating_setpoint_schedule")
        cooling_sched  = zone_params.get("cooling_setpoint_schedule")

        # Create or find the zone hvac system
        if hvac_obj_name:
            hvac_obj = find_or_create_object(idf, hvac_obj_type, hvac_obj_name)
            if hasattr(hvac_obj, "Zone_Name"):
                hvac_obj.Zone_Name = z_name
            print(f"[HVAC] Created or found {hvac_obj_type} => '{hvac_obj_name}' for zone {z_name}")

        # If you want to manipulate thermostats or schedules:
        if heating_sched or cooling_sched:
            print(f"[HVAC] For zone={z_name}, link heating_sched={heating_sched}, cooling_sched={cooling_sched}")
            # Implement or skip

##############################################################################
# Utility: find/create an object
##############################################################################
def find_or_create_object(idf, obj_type_upper, obj_name):
    """
    Utility to find an existing object in IDF by type & name, or create a new one.
    E.g.: find_or_create_object(idf, "ZONEHVAC:IDEALLOADSAIRSYSTEM", "Zone1_Core Ideal Loads")
    """
    obj_type_upper = obj_type_upper.upper()
    if obj_type_upper not in idf.idfobjects:
        # If IDF doesn't have that object class, attempt creation
        new_obj = idf.newidfobject(obj_type_upper)
        new_obj.Name = obj_name
        return new_obj

    existing = [
        o for o in idf.idfobjects[obj_type_upper]
        if hasattr(o, "Name") and str(o.Name) == str(obj_name)
    ]
    if existing:
        return existing[0]
    else:
        new_obj = idf.newidfobject(obj_type_upper)
        new_obj.Name = obj_name
        return new_obj
